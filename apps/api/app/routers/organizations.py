"""Organizations router — thin layer over organization_service.

Provides:
- ``GET    /api/v1/organizations``              — list caller's orgs
- ``POST   /api/v1/organizations``              — create a new org
- ``POST   /api/v1/organizations/join``         — join via invite code
- ``PATCH  /api/v1/organizations/{id}``         — edit org details
- ``POST   /api/v1/organizations/{id}/leave``   — leave the org
- ``GET    /api/v1/organizations/{id}/members`` — list members
- ``DELETE /api/v1/organizations/{id}``         — delete the org (admin only)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db
from app.schemas.organizations import (
    MemberOut,
    OrganizationCreateRequest,
    OrganizationJoinRequest,
    OrganizationOut,
    OrganizationUpdateRequest,
)
from app.services.organization_service import (
    OrganizationConflictError,
    OrganizationForbiddenError,
    OrganizationNotFoundError,
    create_organization,
    delete_organization,
    join_organization,
    leave_organization,
    list_members,
    list_organizations,
    update_organization,
)

router = APIRouter(prefix="/api/v1", tags=["Organizations"])


# ── List ─────────────────────────────────────────────────────────────


@router.get(
    "/organizations",
    response_model=list[OrganizationOut],
    status_code=status.HTTP_200_OK,
    summary="List organizations for the current user",
)
def list_orgs(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[OrganizationOut]:
    return list_organizations(db=db, current_user=current_user)


# ── Create ───────────────────────────────────────────────────────────


@router.post(
    "/organizations",
    response_model=OrganizationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an organization",
)
def create_org(
    body: OrganizationCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> OrganizationOut:
    return create_organization(db=db, current_user=current_user, body=body)


# ── Join ─────────────────────────────────────────────────────────────


@router.post(
    "/organizations/join",
    response_model=OrganizationOut,
    status_code=status.HTTP_200_OK,
    summary="Join an organization via invite code",
)
def join_org(
    body: OrganizationJoinRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> OrganizationOut:
    try:
        return join_organization(
            db=db, current_user=current_user, invite_code=body.invite_code,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))


# ── Update (PATCH) ───────────────────────────────────────────────────


@router.patch(
    "/organizations/{organization_id}",
    response_model=OrganizationOut,
    status_code=status.HTTP_200_OK,
    summary="Edit organization details",
)
def update_org(
    organization_id: uuid.UUID,
    body: OrganizationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> OrganizationOut:
    try:
        return update_organization(
            db=db,
            current_user=current_user,
            organization_id=organization_id,
            body=body,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))


# ── Leave ────────────────────────────────────────────────────────────


@router.post(
    "/organizations/{organization_id}/leave",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Leave an organization",
)
def leave_org(
    organization_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Response:
    try:
        leave_organization(
            db=db,
            current_user=current_user,
            organization_id=organization_id,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
    except OrganizationConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Members ──────────────────────────────────────────────────────────


@router.get(
    "/organizations/{organization_id}/members",
    response_model=list[MemberOut],
    status_code=status.HTTP_200_OK,
    summary="List members of an organization",
)
def get_members(
    organization_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[MemberOut]:
    try:
        return list_members(
            db=db,
            current_user=current_user,
            organization_id=organization_id,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))


# ── Delete ───────────────────────────────────────────────────────────


@router.delete(
    "/organizations/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an organization (admin only)",
)
def delete_org(
    organization_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Response:
    try:
        delete_organization(
            db=db,
            current_user=current_user,
            organization_id=organization_id,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
    except OrganizationForbiddenError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
