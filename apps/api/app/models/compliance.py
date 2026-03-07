"""Compliance, coverage, and risk models.

These tables capture the *aggregate* governance layer that sits above
individual analysis runs:

- **Intake compliance** – checks run on a document at upload time.
- **Coverage controls / assessments** – aggregate pillar coverage
  evaluated across a scope (unit, subject, package).
- **Risk scores** – derived risk tier for a given scope + pillar.
- **Improvement actions** – recommended steps to close coverage gaps.
"""

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import (
    ActionPriority,
    ActionStatus,
    ComplianceCheckType,
    ComplianceStatus,
    CoverageScope,
    RiskLevel,
)
from app.models.mixins import TimestampMixin


# ── Intake Compliance Result ─────────────────────────────────────────

class IntakeComplianceResult(TimestampMixin, Base):
    """Result of a single compliance check executed during document intake."""

    __tablename__ = "intake_compliance_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    check_type: Mapped[ComplianceCheckType] = mapped_column(
        String(30), nullable=False
    )
    status: Mapped[ComplianceStatus] = mapped_column(
        String(30), nullable=False
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Coverage Control ─────────────────────────────────────────────────

class CoverageControl(TimestampMixin, Base):
    """Defines expected coverage targets for a scope + pillar.

    E.g. "Grade 5 Science (package) should achieve ≥ 70 % coverage on
    P2."  Controls are set by curriculum leads and used to evaluate
    aggregate coverage assessments.
    """

    __tablename__ = "coverage_controls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scope: Mapped[CoverageScope] = mapped_column(String(30), nullable=False)
    scope_ref_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
        doc="FK to the scoped entity (subject, package, etc.). "
            "Not a DB-level FK because it can point to different tables."
    )
    pillar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pillars.id"), nullable=False
    )
    target_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Coverage Assessment ──────────────────────────────────────────────

class CoverageAssessment(TimestampMixin, Base):
    """Aggregate coverage result for a scope + pillar.

    Computed by rolling up lesson-level pillar scores across the scope.
    """

    __tablename__ = "coverage_assessments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    coverage_control_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coverage_controls.id"), nullable=False
    )
    actual_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gap: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        doc="target_score − actual_score (positive means under-covered)."
    )
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    coverage_control: Mapped["CoverageControl"] = relationship()


# ── Risk Score ───────────────────────────────────────────────────────

class RiskScore(TimestampMixin, Base):
    """Derived risk tier for a scope + pillar based on coverage gaps."""

    __tablename__ = "risk_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    coverage_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coverage_assessments.id"), nullable=False
    )
    risk_level: Mapped[RiskLevel] = mapped_column(String(30), nullable=False)
    risk_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    coverage_assessment: Mapped["CoverageAssessment"] = relationship()


# ── Improvement Action ───────────────────────────────────────────────

class ImprovementAction(TimestampMixin, Base):
    """A concrete recommendation to close a coverage gap or reduce risk."""

    __tablename__ = "improvement_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    risk_score_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risk_scores.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[ActionPriority] = mapped_column(
        String(30), default=ActionPriority.MEDIUM, nullable=False
    )
    status: Mapped[ActionStatus] = mapped_column(
        String(30), default=ActionStatus.OPEN, nullable=False
    )
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # relationships
    risk_score: Mapped["RiskScore"] = relationship()
