"""CurriculumSets router — thin layer over curriculum_set_service.

Provides:
- ``GET    /api/v1/curriculum-sets?organization_id=…``  — list
- ``POST   /api/v1/curriculum-sets``                    — create
- ``PATCH  /api/v1/curriculum-sets/{id}``               — update
- ``DELETE /api/v1/curriculum-sets/{id}``                — delete
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db
from app.schemas.curriculum_sets import (
    CurriculumSetCreateRequest,
    CurriculumSetOut,
    CurriculumSetUpdateRequest,
)
from app.services.curriculum_set_service import (
    CurriculumSetNotFoundError,
    create_curriculum_set,
    delete_curriculum_set,
    list_curriculum_sets,
    update_curriculum_set,
)

router = APIRouter(prefix="/api/v1", tags=["CurriculumSets"])


# ── List ─────────────────────────────────────────────────────────────


@router.get(
    "/curriculum-sets",
    response_model=list[CurriculumSetOut],
    status_code=status.HTTP_200_OK,
    summary="List curriculum sets for an organization",
)
def list_cs(
    organization_id: uuid.UUID = Query(..., description="Organization to list sets for"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[CurriculumSetOut]:
    try:
        return list_curriculum_sets(
            db=db,
            current_user=current_user,
            organization_id=organization_id,
        )
    except CurriculumSetNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))


# ── Create ───────────────────────────────────────────────────────────


@router.post(
    "/curriculum-sets",
    response_model=CurriculumSetOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a curriculum set",
)
def create_cs(
    body: CurriculumSetCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CurriculumSetOut:
    try:
        return create_curriculum_set(
            db=db,
            current_user=current_user,
            body=body,
        )
    except CurriculumSetNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))


# ── Update (PATCH) ───────────────────────────────────────────────────


@router.patch(
    "/curriculum-sets/{curriculum_set_id}",
    response_model=CurriculumSetOut,
    status_code=status.HTTP_200_OK,
    summary="Update a curriculum set",
)
def update_cs(
    curriculum_set_id: uuid.UUID,
    body: CurriculumSetUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CurriculumSetOut:
    try:
        return update_curriculum_set(
            db=db,
            current_user=current_user,
            curriculum_set_id=curriculum_set_id,
            body=body,
        )
    except CurriculumSetNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))


# ── Delete ───────────────────────────────────────────────────────────


@router.delete(
    "/curriculum-sets/{curriculum_set_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a curriculum set",
)
def delete_cs(
    curriculum_set_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Response:
    try:
        delete_curriculum_set(
            db=db,
            current_user=current_user,
            curriculum_set_id=curriculum_set_id,
        )
    except CurriculumSetNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
