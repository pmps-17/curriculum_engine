"""CurriculumSet service — business logic for curriculum-set management.

Enforces org-membership tenancy.  Repositories handle all SQLAlchemy
access; this layer never touches ``db`` directly beyond ``commit()``.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.repositories.curriculum_set_repo import CurriculumSetRepo
from app.repositories.organization_repo import OrganizationRepo
from app.schemas.curriculum_sets import (
    CurriculumSetCreateRequest,
    CurriculumSetOut,
    CurriculumSetUpdateRequest,
)

logger = logging.getLogger(__name__)


# ── Exceptions (mapped to HTTP codes in the router) ──────────────────


class CurriculumSetNotFoundError(Exception):
    """Raised when the curriculum set doesn't exist or user lacks access."""


# ── Helpers ──────────────────────────────────────────────────────────


def _cs_to_out(cs) -> CurriculumSetOut:
    """Map an ORM CurriculumSet to the response schema."""
    return CurriculumSetOut(
        id=cs.id,
        organization_id=cs.organization_id,
        title=cs.title,
        subject=cs.subject,
        grade_band=cs.grade_band,
        description=cs.description,
        created_by_user_id=cs.created_by_user_id,
        created_at=cs.created_at,
        updated_at=cs.updated_at,
    )


def _ensure_membership(
    org_repo: OrganizationRepo,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Raise ``CurriculumSetNotFoundError`` if the user is not a member."""
    org = org_repo.get_by_id(organization_id)
    if org is None or not org_repo.is_member(organization_id, user_id):
        raise CurriculumSetNotFoundError("Curriculum set not found.")


# ── Public API ───────────────────────────────────────────────────────


def list_curriculum_sets(
    *,
    db: Session,
    current_user: CurrentUser,
    organization_id: uuid.UUID,
) -> list[CurriculumSetOut]:
    """Return all curriculum sets for an organization the caller belongs to."""
    org_repo = OrganizationRepo(db)
    user = org_repo.upsert_user(current_user.email)
    _ensure_membership(org_repo, organization_id, user.id)

    cs_repo = CurriculumSetRepo(db)
    rows = cs_repo.list_for_organization(organization_id)
    return [_cs_to_out(cs) for cs in rows]


def create_curriculum_set(
    *,
    db: Session,
    current_user: CurrentUser,
    body: CurriculumSetCreateRequest,
) -> CurriculumSetOut:
    """Create a curriculum set inside the caller's organization."""
    org_repo = OrganizationRepo(db)
    user = org_repo.upsert_user(current_user.email)
    _ensure_membership(org_repo, body.organization_id, user.id)

    cs_repo = CurriculumSetRepo(db)
    cs = cs_repo.create(
        organization_id=body.organization_id,
        title=body.title,
        subject=body.subject,
        grade_band=body.grade_band,
        description=body.description,
        created_by_user_id=user.id,
    )
    db.commit()
    logger.info(
        "CurriculumSet %s created in org %s by %s",
        cs.id,
        body.organization_id,
        current_user.email,
    )
    return _cs_to_out(cs)


def update_curriculum_set(
    *,
    db: Session,
    current_user: CurrentUser,
    curriculum_set_id: uuid.UUID,
    body: CurriculumSetUpdateRequest,
) -> CurriculumSetOut:
    """Patch mutable fields on a curriculum set. Caller must be a member."""
    org_repo = OrganizationRepo(db)
    user = org_repo.upsert_user(current_user.email)

    cs_repo = CurriculumSetRepo(db)
    cs = cs_repo.get_by_id(curriculum_set_id)
    if cs is None:
        raise CurriculumSetNotFoundError("Curriculum set not found.")
    _ensure_membership(org_repo, cs.organization_id, user.id)

    # Build kwargs — only include fields the client actually sent
    kwargs: dict = {}
    if "title" in body.model_fields_set:
        kwargs["title"] = body.title
    if "subject" in body.model_fields_set:
        kwargs["subject"] = body.subject
    if "grade_band" in body.model_fields_set:
        kwargs["grade_band"] = body.grade_band
    if "description" in body.model_fields_set:
        kwargs["description"] = body.description

    if kwargs:
        cs_repo.update(cs, **kwargs)

    db.commit()
    logger.info(
        "CurriculumSet %s updated by %s (fields: %s)",
        curriculum_set_id,
        current_user.email,
        list(kwargs.keys()),
    )
    return _cs_to_out(cs)


def delete_curriculum_set(
    *,
    db: Session,
    current_user: CurrentUser,
    curriculum_set_id: uuid.UUID,
) -> None:
    """Hard-delete a curriculum set. Caller must be a member of the org."""
    org_repo = OrganizationRepo(db)
    user = org_repo.upsert_user(current_user.email)

    cs_repo = CurriculumSetRepo(db)
    cs = cs_repo.get_by_id(curriculum_set_id)
    if cs is None:
        raise CurriculumSetNotFoundError("Curriculum set not found.")
    _ensure_membership(org_repo, cs.organization_id, user.id)

    cs_repo.delete(cs)
    db.commit()
    logger.info(
        "CurriculumSet %s deleted by %s",
        curriculum_set_id,
        current_user.email,
    )
