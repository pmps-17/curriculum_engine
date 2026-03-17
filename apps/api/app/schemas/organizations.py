"""Request and response schemas for organization tenancy.

Covers organization creation, joining via invite code, and listing.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import CamelModel


# ── Requests ─────────────────────────────────────────────────────────


class OrganizationCreateRequest(CamelModel):
    """Body for ``POST /api/v1/organizations``."""

    name: str = Field(
        min_length=1, max_length=255,
        description="Human-readable organization name.",
    )


class OrganizationJoinRequest(CamelModel):
    """Body for ``POST /api/v1/organizations/join``."""

    invite_code: str = Field(
        min_length=1, max_length=12,
        description="Invite code shared by the organization owner.",
    )


# ── Responses ────────────────────────────────────────────────────────


class OrganizationOut(CamelModel):
    """Organization payload returned to the client."""

    organization_id: UUID = Field(description="Organization identifier.")
    name: str = Field(description="Organization display name.")
    invite_code: str | None = Field(
        default=None,
        description="Invite code (included only when the user is the owner).",
    )
    created_at: datetime = Field(description="When the organization was created.")


class OrganizationJoinOut(CamelModel):
    """Response after joining an organization."""

    organization_id: UUID = Field(description="Organization identifier.")
    name: str = Field(description="Organization display name.")
