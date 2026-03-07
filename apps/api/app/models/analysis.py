"""Analysis-domain models.

Covers everything produced by a single analysis run: candidate skill
matches, deterministic scores (skill-level and pillar-level), evidence
snippets, and findings/flags.
"""

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import (
    AnalysisRunStatus,
    FindingCategory,
    FindingSeverity,
    MatchMethod,
)
from app.models.mixins import TimestampMixin


# ── Analysis Run ─────────────────────────────────────────────────────

class AnalysisRun(TimestampMixin, Base):
    """A single end-to-end analysis execution against a curriculum item.

    One curriculum item may be analysed many times (re-runs, different
    ontology versions, etc.).  Each run is immutable once completed.
    """

    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    curriculum_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("curriculum_items.id"), nullable=False
    )
    ontology_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ontology_versions.id"), nullable=False
    )
    status: Mapped[AnalysisRunStatus] = mapped_column(
        String(30), default=AnalysisRunStatus.PENDING, nullable=False
    )
    triggered_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    candidate_matches: Mapped[list["CandidateMatch"]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )
    skill_scores: Mapped[list["SkillScore"]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )
    pillar_scores: Mapped[list["PillarScore"]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )
    evidence_snippets: Mapped[list["EvidenceSnippet"]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )
    findings: Mapped[list["AnalysisFinding"]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )


# ── Candidate Match ──────────────────────────────────────────────────

class CandidateMatch(TimestampMixin, Base):
    """A potential match between a chunk and a skill indicator.

    Generated during the retrieval phase (keyword or embedding).  Not
    every candidate survives scoring.
    """

    __tablename__ = "candidate_matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunks.id"), nullable=False
    )
    skill_indicator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skill_indicators.id"), nullable=False
    )
    match_method: Mapped[MatchMethod] = mapped_column(
        String(30), default=MatchMethod.KEYWORD, nullable=False
    )
    raw_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    matched_keywords: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        doc="Comma-separated keywords that triggered the match."
    )

    # relationships
    analysis_run: Mapped["AnalysisRun"] = relationship(
        back_populates="candidate_matches"
    )


# ── Skill Score ──────────────────────────────────────────────────────

class SkillScore(TimestampMixin, Base):
    """Deterministic score for a single skill within an analysis run."""

    __tablename__ = "skill_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    indicator_hits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    analysis_run: Mapped["AnalysisRun"] = relationship(
        back_populates="skill_scores"
    )


# ── Pillar Score ─────────────────────────────────────────────────────

class PillarScore(TimestampMixin, Base):
    """Aggregate score for a pillar, derived from its skill scores."""

    __tablename__ = "pillar_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False
    )
    pillar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pillars.id"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    skill_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    analysis_run: Mapped["AnalysisRun"] = relationship(
        back_populates="pillar_scores"
    )


# ── Evidence Snippet ─────────────────────────────────────────────────

class EvidenceSnippet(TimestampMixin, Base):
    """A verbatim text excerpt that supports a particular score.

    Provides explainability — every score can point back to the original
    curriculum text that influenced it.
    """

    __tablename__ = "evidence_snippets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunks.id"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False
    )
    snippet_text: Mapped[str] = mapped_column(Text, nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # relationships
    analysis_run: Mapped["AnalysisRun"] = relationship(
        back_populates="evidence_snippets"
    )


# ── Analysis Finding ─────────────────────────────────────────────────

class AnalysisFinding(TimestampMixin, Base):
    """A flag or observation raised during analysis.

    Findings are descriptive, not punitive — they highlight gaps,
    low-confidence areas, or structural issues for human review.
    """

    __tablename__ = "analysis_findings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False
    )
    severity: Mapped[FindingSeverity] = mapped_column(
        String(30), default=FindingSeverity.INFO, nullable=False
    )
    category: Mapped[FindingCategory] = mapped_column(
        String(30), default=FindingCategory.OTHER, nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    pillar_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pillars.id"), nullable=True
    )
    skill_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id"), nullable=True
    )

    # relationships
    analysis_run: Mapped["AnalysisRun"] = relationship(
        back_populates="findings"
    )
