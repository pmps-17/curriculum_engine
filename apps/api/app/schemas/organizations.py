"""Request and response schemas for organization tenancy.

Covers organization creation, joining via invite code, and listing.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.base import CamelModel


# ── Shared optional profile fields ───────────────────────────────────


class _OrganizationProfileMixin(CamelModel):
    """Optional contact + location fields shared across create/update."""

    contact_name: str | None = Field(
        default=None, max_length=255,
        description="Primary contact person.",
    )
    contact_email: EmailStr | None = Field(
        default=None,
        description="Contact email (validated format).",
    )
    country_name: str | None = Field(
        default=None, max_length=100,
        description="Full country name (e.g. 'United States').",
    )
    country_code: str | None = Field(
        default=None, max_length=10,
        description="ISO-2 country code (e.g. 'US').",
    )
    state_name: str | None = Field(
        default=None, max_length=100,
        description="Full state / province name (e.g. 'California').",
    )
    state_code: str | None = Field(
        default=None, max_length=10,
        description="State / region code (e.g. 'CA').",
    )
    city: str | None = Field(
        default=None, max_length=100,
        description="City name.",
    )


# ── Requests ─────────────────────────────────────────────────────────


class OrganizationCreateRequest(_OrganizationProfileMixin):
    """Body for ``POST /api/v1/organizations``."""

    name: str = Field(
        min_length=1, max_length=255,
        description="Human-readable organization name.",
    )
    description: str | None = Field(
        default=None, max_length=1000,
        description="Optional short description of the organization.",
    )


class OrganizationUpdateRequest(_OrganizationProfileMixin):
    """Body for ``PATCH /api/v1/organizations/{id}``."""

    name: str | None = Field(
        default=None, min_length=1, max_length=255,
        description="Updated organization name.",
    )
    description: str | None = Field(
        default=None, max_length=1000,
        description="Updated description (send null to clear).",
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
    description: str | None = Field(
        default=None,
        description="Optional short description.",
    )
    invite_code: str | None = Field(
        default=None,
        description="Invite code (included only when the user is the owner).",
    )
    created_at: datetime = Field(description="When the organization was created.")

    # ── Permissions ──────────────────────────────────────────────────
    is_admin: bool = Field(
        default=False,
        description="True when the current user is the org creator/owner.",
    )
    member_count: int = Field(
        default=0,
        description="Total number of members in this organization.",
    )

    # ── Contact ──────────────────────────────────────────────────────
    contact_name: str | None = Field(default=None, description="Primary contact person.")
    contact_email: str | None = Field(default=None, description="Contact email.")

    # ── Location ─────────────────────────────────────────────────────
    country_name: str | None = Field(default=None, description="Full country name.")
    country_code: str | None = Field(default=None, description="ISO-2 country code.")
    state_name: str | None = Field(default=None, description="Full state / province name.")
    state_code: str | None = Field(default=None, description="State / region code.")
    city: str | None = Field(default=None, description="City name.")


class OrganizationJoinOut(CamelModel):
    """Response after joining an organization."""

    organization_id: UUID = Field(description="Organization identifier.")
    name: str = Field(description="Organization display name.")


# ── Member response ──────────────────────────────────────────────────


class MemberOut(CamelModel):
    """A single organization member."""

    user_id: UUID = Field(description="User identifier.")
    email: str = Field(description="User email address.")
    name: str | None = Field(default=None, description="User display name.")
    role: str = Field(description="'admin' for the org owner, 'member' otherwise.")
    joined_at: datetime = Field(description="When the user joined the organization.")
