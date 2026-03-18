"""Request and response schemas for curriculum sets.

Covers CRUD operations on the CurriculumSet entity — the Library-level
grouping under an organization.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import CamelModel


# ── Requests ─────────────────────────────────────────────────────────


class CurriculumSetCreateRequest(CamelModel):
    """Body for ``POST /api/v1/curriculum-sets``."""

    organization_id: UUID = Field(
        description="Organization this set belongs to.",
    )
    title: str = Field(
        min_length=1, max_length=500,
        description="Display title of the curriculum set.",
    )
    subject: str | None = Field(
        default=None, max_length=255,
        description="Subject area (e.g. Science, Math).",
    )
    grade_band: str | None = Field(
        default=None, max_length=100,
        description="Grade band (e.g. 3-5, 9-12).",
    )
    description: str | None = Field(
        default=None, max_length=2000,
        description="Optional description of the curriculum set.",
    )


class CurriculumSetUpdateRequest(CamelModel):
    """Body for ``PATCH /api/v1/curriculum-sets/{id}``."""

    title: str | None = Field(
        default=None, min_length=1, max_length=500,
        description="Updated title.",
    )
    subject: str | None = Field(
        default=None, max_length=255,
        description="Updated subject (send null to clear).",
    )
    grade_band: str | None = Field(
        default=None, max_length=100,
        description="Updated grade band (send null to clear).",
    )
    description: str | None = Field(
        default=None, max_length=2000,
        description="Updated description (send null to clear).",
    )


# ── Responses ────────────────────────────────────────────────────────


class CurriculumSetOut(CamelModel):
    """Curriculum set payload returned to the client."""

    id: UUID = Field(description="Curriculum set identifier.")
    organization_id: UUID = Field(description="Owning organization.")
    title: str = Field(description="Display title.")
    subject: str | None = Field(default=None, description="Subject area.")
    grade_band: str | None = Field(default=None, description="Grade band.")
    description: str | None = Field(default=None, description="Description.")
    created_by_user_id: UUID | None = Field(
        default=None, description="User who created this set.",
    )
    created_at: datetime = Field(description="Creation timestamp.")
    updated_at: datetime = Field(description="Last update timestamp.")
