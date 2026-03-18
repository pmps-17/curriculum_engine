"""Organization service — business logic for organization management.

Enforces membership, ownership, and orphan-prevention rules.
Repositories handle all SQLAlchemy access; this layer never
touches ``db`` directly beyond ``commit()``.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.repositories.organization_repo import OrganizationRepo
from app.schemas.organizations import (
    OrganizationCreateRequest,
    OrganizationOut,
    OrganizationUpdateRequest,
)

logger = logging.getLogger(__name__)


# ── Exceptions (mapped to HTTP codes in the router) ──────────────────


class OrganizationNotFoundError(Exception):
    """Raised when the org does not exist or user is not a member."""


class OrganizationConflictError(Exception):
    """Raised when leaving would orphan the organization (last member)."""


# ── Helpers ──────────────────────────────────────────────────────────


def _org_to_out(
    org,
    *,
    show_invite_code: bool = False,
) -> OrganizationOut:
    """Map an ORM Organization to the response schema."""
    return OrganizationOut(
        organization_id=org.id,
        name=org.name,
        description=org.description,
        invite_code=org.invite_code if show_invite_code else None,
        created_at=org.created_at,
        contact_name=org.contact_name,
        contact_email=org.contact_email,
        country_name=org.country_name,
        country_code=org.country_code,
        state_name=org.state_name,
        state_code=org.state_code,
        city=org.city,
    )


# ── Public API ───────────────────────────────────────────────────────


def list_organizations(
    *,
    db: Session,
    current_user: CurrentUser,
) -> list[OrganizationOut]:
    """Return all organizations the caller belongs to."""
    repo = OrganizationRepo(db)
    user = repo.upsert_user(current_user.email)
    orgs = repo.list_for_user(user.id)
    return [
        _org_to_out(org, show_invite_code=(org.owner_user_id == user.id))
        for org in orgs
    ]


def create_organization(
    *,
    db: Session,
    current_user: CurrentUser,
    body: OrganizationCreateRequest,
) -> OrganizationOut:
    """Create a new organization and add the caller as owner + member."""
    repo = OrganizationRepo(db)
    user = repo.upsert_user(current_user.email)
    org = repo.create_organization(name=body.name, owner=user)

    # Apply optional profile fields supplied at creation time
    profile_kwargs: dict = {}
    if body.description is not None:
        profile_kwargs["description"] = body.description
    for field_name in (
        "contact_name", "contact_email",
        "country_name", "country_code",
        "state_name", "state_code",
        "city",
    ):
        val = getattr(body, field_name, None)
        if val is not None:
            profile_kwargs[field_name] = val

    if profile_kwargs:
        repo.update(org, **profile_kwargs)

    db.commit()
    logger.info("Organization created: %s by %s", org.id, current_user.email)
    return _org_to_out(org, show_invite_code=True)


def join_organization(
    *,
    db: Session,
    current_user: CurrentUser,
    invite_code: str,
) -> OrganizationOut:
    """Join an existing organization via invite code."""
    repo = OrganizationRepo(db)
    user = repo.upsert_user(current_user.email)

    org = repo.get_by_invite_code(invite_code.strip().upper())
    if org is None:
        raise OrganizationNotFoundError("Invalid invite code.")

    repo.add_member(organization_id=org.id, user_id=user.id)
    db.commit()
    logger.info("User %s joined organization %s", current_user.email, org.id)
    return _org_to_out(org, show_invite_code=(org.owner_user_id == user.id))


def update_organization(
    *,
    db: Session,
    current_user: CurrentUser,
    organization_id: uuid.UUID,
    body: OrganizationUpdateRequest,
) -> OrganizationOut:
    """Update mutable org details. Caller must be a member."""
    repo = OrganizationRepo(db)
    user = repo.upsert_user(current_user.email)

    org = repo.get_by_id(organization_id)
    if org is None or not repo.is_member(organization_id, user.id):
        raise OrganizationNotFoundError("Organization not found.")

    # Build kwargs — only include fields the client sent
    kwargs: dict = {}
    if body.name is not None:
        kwargs["name"] = body.name
    # description can be explicitly set to None (clear) or a string
    if "description" in body.model_fields_set:
        kwargs["description"] = body.description

    # Profile fields — all nullable, clearable via explicit null
    for field_name in (
        "contact_name", "contact_email",
        "country_name", "country_code",
        "state_name", "state_code",
        "city",
    ):
        if field_name in body.model_fields_set:
            kwargs[field_name] = getattr(body, field_name)

    if kwargs:
        repo.update(org, **kwargs)

    db.commit()
    logger.info(
        "Organization %s updated by %s (fields: %s)",
        organization_id,
        current_user.email,
        list(kwargs.keys()),
    )
    return _org_to_out(org, show_invite_code=(org.owner_user_id == user.id))


def leave_organization(
    *,
    db: Session,
    current_user: CurrentUser,
    organization_id: uuid.UUID,
) -> None:
    """Remove the caller from an organization.

    Raises:
        OrganizationNotFoundError: org missing or not a member.
        OrganizationConflictError: would leave org with zero members.
    """
    repo = OrganizationRepo(db)
    user = repo.upsert_user(current_user.email)

    org = repo.get_by_id(organization_id)
    if org is None or not repo.is_member(organization_id, user.id):
        raise OrganizationNotFoundError("Organization not found.")

    if repo.count_members(organization_id) <= 1:
        raise OrganizationConflictError(
            "Cannot leave: you are the last member. "
            "Delete the organization or add another member first."
        )

    repo.remove_member(organization_id=organization_id, user_id=user.id)
    db.commit()
    logger.info(
        "User %s left organization %s",
        current_user.email,
        organization_id,
    )
