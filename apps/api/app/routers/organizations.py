"""Organizations router — organization CRUD and invite-code join.

Provides:
- ``POST /api/v1/organizations``      — create a new organization
- ``POST /api/v1/organizations/join`` — join via invite code
- ``GET  /api/v1/organizations``      — list user's organizations

User identity is resolved via ``get_current_user`` (Google JWT or
dev-header fallback).
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db
from app.repositories.organization_repo import OrganizationRepo
from app.schemas.organizations import (
    OrganizationCreateRequest,
    OrganizationJoinOut,
    OrganizationJoinRequest,
    OrganizationOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Organizations"])


# ── Endpoints ────────────────────────────────────────────────────────


@router.post(
    "/organizations",
    response_model=OrganizationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an organization",
)
def create_organization(
    body: OrganizationCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> OrganizationOut:
    """Create a new organization and add the caller as owner + member."""
    repo = OrganizationRepo(db)
    user = repo.upsert_user(current_user.email)
    org = repo.create_organization(name=body.name, owner=user)
    db.commit()

    logger.info("Organization created: %s by %s", org.id, current_user.email)
    return OrganizationOut(
        organization_id=org.id,
        name=org.name,
        invite_code=org.invite_code,
        created_at=org.created_at,
    )


@router.post(
    "/organizations/join",
    response_model=OrganizationJoinOut,
    status_code=status.HTTP_200_OK,
    summary="Join an organization via invite code",
)
def join_organization(
    body: OrganizationJoinRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> OrganizationJoinOut:
    """Join an existing organization using its invite code."""
    repo = OrganizationRepo(db)
    user = repo.upsert_user(current_user.email)

    org = repo.get_by_invite_code(body.invite_code.strip().upper())
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite code.",
        )

    repo.add_member(organization_id=org.id, user_id=user.id)
    db.commit()

    logger.info("User %s joined organization %s", current_user.email, org.id)
    return OrganizationJoinOut(organization_id=org.id, name=org.name)


@router.get(
    "/organizations",
    response_model=list[OrganizationOut],
    status_code=status.HTTP_200_OK,
    summary="List organizations for the current user",
)
def list_organizations(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[OrganizationOut]:
    """Return all organizations the caller belongs to."""
    repo = OrganizationRepo(db)
    user = repo.upsert_user(current_user.email)
    organizations = repo.list_for_user(user.id)

    return [
        OrganizationOut(
            organization_id=org.id,
            name=org.name,
            invite_code=org.invite_code if org.owner_user_id == user.id else None,
            created_at=org.created_at,
        )
        for org in organizations
    ]
