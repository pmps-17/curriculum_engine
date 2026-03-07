"""Review and audit-trail models.

Human review is authoritative in the curriculum engine.  These tables
record review decisions, individual edits/overrides, and a general
audit log for traceability.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import AuditAction, ReviewEditType, ReviewStatus
from app.models.mixins import TimestampMixin


# ── Review ───────────────────────────────────────────────────────────

class Review(TimestampMixin, Base):
    """A human review session attached to an analysis run.

    A reviewer may approve, reject, or request changes.  Individual
    score overrides are captured in ``ReviewEdit`` rows.
    """

    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False
    )
    reviewer: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ReviewStatus] = mapped_column(
        String(30), default=ReviewStatus.PENDING, nullable=False
    )
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    edits: Mapped[list["ReviewEdit"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )


# ── Review Edit ──────────────────────────────────────────────────────

class ReviewEdit(TimestampMixin, Base):
    """A single change made by a reviewer (score override, match add/remove, comment)."""

    __tablename__ = "review_edits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False
    )
    edit_type: Mapped[ReviewEditType] = mapped_column(
        String(30), nullable=False
    )
    target_entity: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        doc="Table name of the entity being edited (e.g. 'skill_scores')."
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
        doc="PK of the row being edited."
    )
    old_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    review: Mapped["Review"] = relationship(back_populates="edits")


# ── Audit Log ────────────────────────────────────────────────────────

class AuditLog(Base):
    """Append-only audit trail for key system events.

    Uses ``created_at`` only (no ``updated_at``), because audit rows are
    immutable by design.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    action: Mapped[AuditAction] = mapped_column(String(30), nullable=False)
    entity_type: Mapped[str] = mapped_column(
        String(100), nullable=False,
        doc="Table / model name of the affected entity."
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
