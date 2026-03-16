"""Workspaces router — workspace CRUD and invite-code join.

Provides:
- ``POST /api/v1/workspaces``      — create a new workspace
- ``POST /api/v1/workspaces/join`` — join via invite code
- ``GET  /api/v1/workspaces``      — list user's workspaces

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
from app.repositories.workspace_repo import WorkspaceRepo
from app.schemas.workspaces import (
    WorkspaceCreateRequest,
    WorkspaceJoinOut,
    WorkspaceJoinRequest,
    WorkspaceOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Workspaces"])


# ── Endpoints ────────────────────────────────────────────────────────


@router.post(
    "/workspaces",
    response_model=WorkspaceOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workspace",
)
def create_workspace(
    body: WorkspaceCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> WorkspaceOut:
    """Create a new workspace and add the caller as owner + member."""
    repo = WorkspaceRepo(db)
    user = repo.upsert_user(current_user.email)
    ws = repo.create_workspace(name=body.name, owner=user)
    db.commit()

    logger.info("Workspace created: %s by %s", ws.id, current_user.email)
    return WorkspaceOut(
        workspace_id=ws.id,
        name=ws.name,
        invite_code=ws.invite_code,
        created_at=ws.created_at,
    )


@router.post(
    "/workspaces/join",
    response_model=WorkspaceJoinOut,
    status_code=status.HTTP_200_OK,
    summary="Join a workspace via invite code",
)
def join_workspace(
    body: WorkspaceJoinRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> WorkspaceJoinOut:
    """Join an existing workspace using its invite code."""
    repo = WorkspaceRepo(db)
    user = repo.upsert_user(current_user.email)

    ws = repo.get_by_invite_code(body.invite_code.strip().upper())
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite code.",
        )

    repo.add_member(workspace_id=ws.id, user_id=user.id)
    db.commit()

    logger.info("User %s joined workspace %s", current_user.email, ws.id)
    return WorkspaceJoinOut(workspace_id=ws.id, name=ws.name)


@router.get(
    "/workspaces",
    response_model=list[WorkspaceOut],
    status_code=status.HTTP_200_OK,
    summary="List workspaces for the current user",
)
def list_workspaces(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[WorkspaceOut]:
    """Return all workspaces the caller belongs to."""
    repo = WorkspaceRepo(db)
    user = repo.upsert_user(current_user.email)
    workspaces = repo.list_for_user(user.id)

    return [
        WorkspaceOut(
            workspace_id=ws.id,
            name=ws.name,
            invite_code=ws.invite_code if ws.owner_user_id == user.id else None,
            created_at=ws.created_at,
        )
        for ws in workspaces
    ]
