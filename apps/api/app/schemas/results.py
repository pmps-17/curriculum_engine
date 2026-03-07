"""Response schema for retrieving stored analysis results.

``ResultResponse`` is used when a client fetches a previously-completed
analysis run by ID — it returns the same rich payload as
``AnalyzeResponse`` plus additional metadata useful for dashboarding
and research validation.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import AnalysisRunStatus, MatchMethod, ReviewStatus
from app.schemas.analysis import (
    EvidenceSnippetOut,
    FindingOut,
    IntakeComplianceResultOut,
    PillarScoreOut,
)
from app.schemas.base import CamelModel


# =====================================================================
# Lightweight review summary (no full edit list)
# =====================================================================


class ReviewSummaryOut(CamelModel):
    """Compact review info embedded inside a result response."""

    id: UUID = Field(description="Review identifier.")
    reviewer: str = Field(description="Who reviewed.")
    status: ReviewStatus = Field(description="Review outcome.")
    comments: str | None = Field(default=None, description="Reviewer remarks.")
    created_at: datetime = Field(description="When the review was created.")


# =====================================================================
# Result response
# =====================================================================


class ResultResponse(CamelModel):
    """Full stored result for a single analysis run.

    Extends the analysis output with item-level context and review
    history so dashboards can render everything from one payload.
    """

    # ── Run identity ─────────────────────────────────────────────────
    analysis_run_id: UUID = Field(description="Unique run identifier.")
    status: AnalysisRunStatus = Field(description="Run status.")
    triggered_by: str | None = Field(
        default=None, description="Who / what triggered the run."
    )
    created_at: datetime = Field(description="When the run was created.")
    updated_at: datetime = Field(description="When the run was last modified.")

    # ── Curriculum item context ──────────────────────────────────────
    curriculum_item_id: UUID = Field(description="Analysed curriculum item.")
    title: str | None = Field(
        default=None, description="Title of the curriculum item."
    )
    item_type: str | None = Field(
        default=None, description="lesson / activity / module / unit."
    )
    subject_name: str | None = Field(
        default=None, description="Subject area, if known."
    )
    unit_name: str | None = Field(
        default=None, description="Unit name, if known."
    )
    grade_level: str | None = Field(
        default=None, description="Grade band, if known."
    )

    # ── Ontology ─────────────────────────────────────────────────────
    ontology_version_id: UUID = Field(description="Ontology version used.")
    ontology_version_label: str | None = Field(
        default=None, description="Human-readable ontology version label."
    )

    # ── Scores ───────────────────────────────────────────────────────
    pillar_scores: list[PillarScoreOut] = Field(
        default_factory=list,
        description="Pillar-level scores with nested skill detail.",
    )
    overall_score: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Weighted average across pillars.",
    )
    match_method: MatchMethod = Field(
        default=MatchMethod.KEYWORD,
        description="Primary match method used.",
    )

    # ── Evidence & findings ──────────────────────────────────────────
    evidence_snippets: list[EvidenceSnippetOut] = Field(
        default_factory=list,
        description="Supporting text excerpts.",
    )
    findings: list[FindingOut] = Field(
        default_factory=list,
        description="Flags and observations.",
    )

    # ── Intake compliance ────────────────────────────────────────────
    intake_compliance: list[IntakeComplianceResultOut] = Field(
        default_factory=list,
        description="Intake compliance check results.",
    )

    # ── Review history ───────────────────────────────────────────────
    reviews: list[ReviewSummaryOut] = Field(
        default_factory=list,
        description="Human reviews attached to this run.",
    )

    # ── Error ────────────────────────────────────────────────────────
    error_message: str | None = Field(
        default=None, description="Error detail if the run failed."
    )
