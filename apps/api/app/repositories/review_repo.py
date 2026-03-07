"""Repository for review, review-edit, and audit-log persistence.

All DB reads and writes for the human-review domain live here.
Methods flush but never commit — the service owns the transaction.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisRun, SkillScore
from app.models.enums import AuditAction
from app.models.review import AuditLog, Review, ReviewEdit


class ReviewRepo:
    """Thin data-access layer for review-domain tables."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Analysis run lookups ─────────────────────────────────────────

    def get_analysis_run(self, run_id: uuid.UUID) -> AnalysisRun | None:
        """Return an analysis run by primary key, or ``None``."""
        return self._db.get(AnalysisRun, run_id)

    # ── Skill score lookups ──────────────────────────────────────────

    def get_skill_score(self, score_id: uuid.UUID) -> SkillScore | None:
        """Return a skill score by primary key, or ``None``."""
        return self._db.get(SkillScore, score_id)

    def update_skill_score(self, score: SkillScore, new_value: float) -> None:
        """Overwrite a skill score value and flush."""
        score.score = new_value
        self._db.flush()

    # ── Review CRUD ──────────────────────────────────────────────────

    def create_review(
        self,
        *,
        analysis_run_id: uuid.UUID,
        reviewer: str,
        status: str,
        comments: str | None,
    ) -> Review:
        """Insert a new review and flush (ID assigned)."""
        review = Review(
            analysis_run_id=analysis_run_id,
            reviewer=reviewer,
            status=status,
            comments=comments,
        )
        self._db.add(review)
        self._db.flush()
        return review

    def list_reviews_for_run(
        self,
        analysis_run_id: uuid.UUID,
    ) -> list[Review]:
        """Return all reviews for a given analysis run, ordered by date."""
        stmt = (
            select(Review)
            .where(Review.analysis_run_id == analysis_run_id)
            .order_by(Review.created_at)
        )
        return list(self._db.scalars(stmt).all())

    # ── Review edits ─────────────────────────────────────────────────

    def create_review_edit(
        self,
        *,
        review_id: uuid.UUID,
        edit_type: str,
        target_entity: str | None,
        target_id: uuid.UUID | None,
        old_value: float | None,
        new_value: float | None,
        comment: str | None,
    ) -> ReviewEdit:
        """Insert a single review edit row."""
        edit = ReviewEdit(
            review_id=review_id,
            edit_type=edit_type,
            target_entity=target_entity,
            target_id=target_id,
            old_value=old_value,
            new_value=new_value,
            comment=comment,
        )
        self._db.add(edit)
        return edit

    def flush_edits(self) -> None:
        """Flush all pending edit inserts."""
        self._db.flush()

    # ── Audit log ────────────────────────────────────────────────────

    def create_audit_log(
        self,
        *,
        action: AuditAction,
        entity_type: str,
        entity_id: uuid.UUID | None,
        actor: str | None,
        detail: dict | None,
    ) -> AuditLog:
        """Insert an immutable audit-log entry and flush."""
        log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            detail=detail,
        )
        self._db.add(log)
        self._db.flush()
        return log
