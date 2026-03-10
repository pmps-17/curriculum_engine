"""Request and response schemas for the analysis pipeline.

Covers:
- ``AnalyzeRequest``  — what the client sends to trigger an analysis.
- ``AnalyzeResponse`` — the full result returned after analysis completes.
- Nested output schemas for pillar scores, skill scores, evidence
  snippets, findings, and intake compliance results.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.models.enums import (
    AnalysisRunStatus,
    ComplianceCheckType,
    ComplianceStatus,
    CurriculumItemType,
    FindingCategory,
    FindingSeverity,
    MatchMethod,
    PillarCode,
)
from app.schemas.base import CamelModel


# =====================================================================
# Nested output schemas (smallest → largest)
# =====================================================================


class EvidenceSnippetOut(CamelModel):
    """A verbatim text excerpt that supports a score."""

    id: UUID = Field(description="Evidence snippet identifier.")
    chunk_id: UUID = Field(description="Source chunk that contains the excerpt.")
    skill_id: UUID = Field(description="Skill this evidence supports.")
    snippet_text: str = Field(description="Verbatim text from the curriculum.")
    relevance_score: float = Field(
        ge=0.0, le=1.0,
        description="0-1 relevance of this snippet to the matched skill.",
    )


class SkillScoreOut(CamelModel):
    """Deterministic score for a single skill."""

    id: UUID = Field(description="Skill score identifier.")
    skill_id: UUID = Field(description="Skill that was scored.")
    skill_code: str | None = Field(
        default=None, description="Human-readable skill code (e.g. 'P1-S1')."
    )
    skill_name: str | None = Field(
        default=None, description="Display name of the skill."
    )
    score: float = Field(
        ge=0.0, le=1.0, description="Normalised score (0 = no evidence, 1 = strong)."
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence in the score."
    )
    indicator_hits: int = Field(
        ge=0, description="Number of skill indicators matched."
    )
    explanation: str | None = Field(
        default=None,
        description="Human-readable explanation of how the score was derived.",
    )


class PillarScoreOut(CamelModel):
    """Aggregate score for one pillar, with nested skill-level detail."""

    id: UUID = Field(description="Pillar score identifier.")
    pillar_id: UUID = Field(description="Pillar that was scored.")
    pillar_code: PillarCode | None = Field(
        default=None, description="Pillar code (P1, P2, P3)."
    )
    pillar_name: str | None = Field(
        default=None, description="Display name of the pillar."
    )
    score: float = Field(
        ge=0.0, le=1.0,
        description="Aggregate normalised score across skills in this pillar.",
    )
    skill_count: int = Field(
        ge=0, description="Number of skills evaluated under this pillar."
    )
    explanation: str | None = Field(
        default=None,
        description="Summary explanation of pillar-level scoring.",
    )
    skill_scores: list[SkillScoreOut] = Field(
        default_factory=list,
        description="Breakdown by individual skill.",
    )


class FindingOut(CamelModel):
    """A flag or observation raised during analysis."""

    id: UUID = Field(description="Finding identifier.")
    severity: FindingSeverity = Field(description="info / warning / error.")
    category: FindingCategory = Field(description="Category of the finding.")
    title: str = Field(description="Short description of the finding.")
    detail: str | None = Field(
        default=None, description="Extended explanation."
    )
    pillar_id: UUID | None = Field(
        default=None, description="Related pillar, if applicable."
    )
    skill_id: UUID | None = Field(
        default=None, description="Related skill, if applicable."
    )


class IntakeComplianceResultOut(CamelModel):
    """Result of a single intake compliance check."""

    id: UUID = Field(description="Compliance result identifier.")
    check_type: ComplianceCheckType = Field(
        description="What kind of check was run."
    )
    status: ComplianceStatus = Field(
        description="pass / fail / warning / skipped."
    )
    message: str | None = Field(
        default=None, description="Short human-readable outcome."
    )
    detail: str | None = Field(
        default=None, description="Extended detail or remediation hint."
    )


# =====================================================================
# Request
# =====================================================================


class AnalyzeRequest(CamelModel):
    """Payload sent by the client to trigger a curriculum analysis run.

    At minimum the client must provide ``curriculum_text``.  All other
    fields add context that improves accuracy or enables richer
    downstream reporting.
    """

    # ── Required ─────────────────────────────────────────────────────
    curriculum_text: str = Field(
        min_length=1,
        max_length=100_000,
        description="Raw lesson / activity text to analyse (max 100 000 chars).",
    )

    # ── Optional context ─────────────────────────────────────────────
    title: str | None = Field(
        default=None,
        max_length=500,
        description="Title of the lesson or activity.",
    )
    item_type: CurriculumItemType = Field(
        default=CurriculumItemType.LESSON,
        description="Granularity of the curriculum item.",
    )
    subject: str | None = Field(
        default=None,
        max_length=255,
        description="Subject area (e.g. 'Mathematics').",
    )
    grade_band: str | None = Field(
        default=None,
        max_length=50,
        description="Grade band or level (e.g. 'K-2', 'Grade 5').",
    )
    rubric_text: str | None = Field(
        default=None,
        max_length=100_000,
        description="Optional rubric text for richer assessment mapping (max 100 000 chars).",
    )
    unit_name: str | None = Field(
        default=None,
        max_length=255,
        description="Name of the unit this item belongs to.",
    )

    # ── Linking / governance ─────────────────────────────────────────
    school_id: UUID | None = Field(
        default=None, description="School to associate the analysis with."
    )
    curriculum_package_id: UUID | None = Field(
        default=None, description="Curriculum package for aggregate reporting."
    )
    subject_id: UUID | None = Field(
        default=None, description="Subject FK for aggregate reporting."
    )
    ontology_version_id: UUID | None = Field(
        default=None,
        description="Specific ontology version to use.  If omitted the "
                    "active version is used.",
    )
    triggered_by: str | None = Field(
        default=None,
        max_length=255,
        description="User or system that triggered the analysis.",
    )

    @field_validator("curriculum_text")
    @classmethod
    def curriculum_text_not_blank(cls, v: str) -> str:
        """Reject whitespace-only submissions."""
        if not v.strip():
            raise ValueError("curriculum_text must contain non-whitespace content.")
        return v


# =====================================================================
# Response
# =====================================================================


class AnalyzeResponse(CamelModel):
    """Full result of a completed analysis run.

    Designed to be self-contained: a frontend or researcher can render
    the entire analysis from this single payload without extra lookups.
    """

    # ── Run metadata ─────────────────────────────────────────────────
    analysis_run_id: UUID = Field(description="Unique run identifier.")
    curriculum_item_id: UUID = Field(description="Curriculum item that was analysed.")
    ontology_version_id: UUID = Field(description="Ontology version used.")
    status: AnalysisRunStatus = Field(description="Final status of the run.")
    triggered_by: str | None = Field(
        default=None, description="Who / what triggered the run."
    )
    created_at: datetime = Field(description="When the run started.")

    # ── Intake compliance ────────────────────────────────────────────
    intake_compliance: list[IntakeComplianceResultOut] = Field(
        default_factory=list,
        description="Intake checks executed before scoring.",
    )

    # ── Scores ───────────────────────────────────────────────────────
    pillar_scores: list[PillarScoreOut] = Field(
        default_factory=list,
        description="Pillar-level scores with nested skill detail.",
    )

    # ── Evidence ─────────────────────────────────────────────────────
    evidence_snippets: list[EvidenceSnippetOut] = Field(
        default_factory=list,
        description="Text excerpts supporting the scores.",
    )

    # ── Findings ─────────────────────────────────────────────────────
    findings: list[FindingOut] = Field(
        default_factory=list,
        description="Flags, warnings, and observations.",
    )

    # ── Summary helpers (flat, for quick UI rendering) ───────────────
    overall_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Weighted average across all pillars (convenience field).",
    )
    match_method: MatchMethod = Field(
        default=MatchMethod.KEYWORD,
        description="Primary match method used in this run.",
    )
    error_message: str | None = Field(
        default=None,
        description="Error detail if status is 'failed'.",
    )
