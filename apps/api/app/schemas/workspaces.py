"""Request and response schemas for workspace tenancy.

Covers workspace creation, joining via invite code, and listing.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import CamelModel


# ── Requests ─────────────────────────────────────────────────────────


class WorkspaceCreateRequest(CamelModel):
    """Body for ``POST /api/v1/workspaces``."""

    name: str = Field(
        min_length=1, max_length=255,
        description="Human-readable workspace name.",
    )


class WorkspaceJoinRequest(CamelModel):
    """Body for ``POST /api/v1/workspaces/join``."""

    invite_code: str = Field(
        min_length=1, max_length=12,
        description="Invite code shared by the workspace owner.",
    )


# ── Responses ────────────────────────────────────────────────────────


class WorkspaceOut(CamelModel):
    """Workspace payload returned to the client."""

    workspace_id: UUID = Field(description="Workspace identifier.")
    name: str = Field(description="Workspace display name.")
    invite_code: str | None = Field(
        default=None,
        description="Invite code (included only when the user is the owner).",
    )
    created_at: datetime = Field(description="When the workspace was created.")


class WorkspaceJoinOut(CamelModel):
    """Response after joining a workspace."""

    workspace_id: UUID = Field(description="Workspace identifier.")
    name: str = Field(description="Workspace display name.")
