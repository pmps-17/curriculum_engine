"""Request and response schemas for human review workflows.

A review is always attached to a completed analysis run.  Reviewers can
override scores, add/remove matches, or leave comments — each edit is
captured individually for full audit-trail fidelity.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.models.enums import ReviewEditType, ReviewStatus
from app.schemas.base import CamelModel


# =====================================================================
# Nested types
# =====================================================================


class ReviewEditIn(CamelModel):
    """A single edit submitted as part of a review."""

    edit_type: ReviewEditType = Field(
        description="Kind of edit: score_override, match_added, match_removed, or comment.",
    )
    target_entity: str | None = Field(
        default=None,
        max_length=100,
        description="Table name of the entity being edited (e.g. 'skill_scores').",
    )
    target_id: UUID | None = Field(
        default=None,
        description="Primary key of the row being edited.",
    )
    old_value: float | None = Field(
        default=None,
        description="Previous numeric value (for score overrides).",
    )
    new_value: float | None = Field(
        default=None,
        description="New numeric value (for score overrides).",
    )
    comment: str | None = Field(
        default=None,
        description="Free-text justification or note.",
    )


class ReviewEditOut(ReviewEditIn):
    """Persisted review edit returned in responses."""

    id: UUID = Field(description="Review edit identifier.")
    review_id: UUID = Field(description="Parent review identifier.")
    created_at: datetime = Field(description="When the edit was recorded.")


# =====================================================================
# Request
# =====================================================================


class ReviewRequest(CamelModel):
    """Payload to create or update a review on an analysis run.

    At minimum the reviewer must identify themselves and the target run.
    Edits (score overrides, match changes, comments) are optional and
    can be supplied in bulk.
    """

    analysis_run_id: UUID = Field(
        description="The analysis run being reviewed.",
    )
    reviewer: str = Field(
        min_length=1,
        max_length=255,
        description="Name or identifier of the reviewer.",
    )
    status: ReviewStatus = Field(
        default=ReviewStatus.PENDING,
        description="Desired review status.",
    )
    comments: str | None = Field(
        default=None,
        description="Overall review comments.",
    )
    edits: list[ReviewEditIn] = Field(
        default_factory=list,
        description="Individual edits (overrides, additions, removals, comments).",
    )

    @field_validator("reviewer")
    @classmethod
    def reviewer_not_blank(cls, v: str) -> str:
        """Reject whitespace-only reviewer names."""
        if not v.strip():
            raise ValueError("reviewer must contain non-whitespace content.")
        return v


# =====================================================================
# Response
# =====================================================================


class ReviewResponse(CamelModel):
    """Full review record returned after creation or retrieval."""

    id: UUID = Field(description="Review identifier.")
    analysis_run_id: UUID = Field(description="Associated analysis run.")
    reviewer: str = Field(description="Who performed the review.")
    status: ReviewStatus = Field(description="Current review status.")
    comments: str | None = Field(
        default=None, description="Overall review comments."
    )
    edits: list[ReviewEditOut] = Field(
        default_factory=list,
        description="All edits recorded under this review.",
    )
    created_at: datetime = Field(description="When the review was created.")
    updated_at: datetime = Field(description="When the review was last modified.")
