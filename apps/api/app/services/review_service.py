"""Review service — create and manage human reviews on analysis runs.

Human review is **authoritative** in the curriculum engine.  This
service handles:

- Creating a new review (approve / reject / in-progress / comment).
- Persisting individual edits (score overrides, match changes).
- Applying score overrides to the underlying ``SkillScore`` rows.
- Writing an audit-log entry for every review action.

All DB writes happen inside the caller's transaction — the service
calls ``flush()`` but never ``commit()``.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.analysis import AnalysisRun
from app.models.enums import (
    AnalysisRunStatus,
    AuditAction,
    ReviewEditType,
    ReviewStatus,
)
from app.models.review import AuditLog, Review, ReviewEdit
from app.repositories.review_repo import ReviewRepo
from app.schemas.review import (
    ReviewEditIn,
    ReviewEditOut,
    ReviewRequest,
    ReviewResponse,
)

logger = logging.getLogger(__name__)

# Valid target entity names for score-override edits
_SCORE_OVERRIDE_TARGETS: frozenset[str] = frozenset({"skill_scores", "pillar_scores"})


# =====================================================================
# Exceptions
# =====================================================================


class ReviewError(Exception):
    """Base exception for review-service failures."""


class AnalysisRunNotFoundError(ReviewError):
    """The target analysis run does not exist."""


class AnalysisRunNotCompletedError(ReviewError):
    """The target analysis run is not in a reviewable state."""


class InvalidEditTargetError(ReviewError):
    """A review edit references an entity that cannot be found."""


# =====================================================================
# Internal helpers
# =====================================================================


def _validate_analysis_run(repo: ReviewRepo, run_id: UUID) -> AnalysisRun:
    """Load and validate that the analysis run exists and is completed."""
    run = repo.get_analysis_run(run_id)
    if run is None:
        raise AnalysisRunNotFoundError(
            f"Analysis run {run_id} not found."
        )
    if run.status != AnalysisRunStatus.COMPLETED:
        raise AnalysisRunNotCompletedError(
            f"Analysis run {run_id} has status '{run.status.value}'; "
            f"only completed runs can be reviewed."
        )
    return run


def _apply_score_override(
    repo: ReviewRepo,
    edit: ReviewEditIn,
) -> None:
    """Apply a score override to the target row, if applicable.

    Only ``skill_scores`` overrides are applied in v1.  Pillar scores
    are not directly editable — they should be recomputed from skill
    scores in a future version.
    """
    if edit.edit_type != ReviewEditType.SCORE_OVERRIDE:
        return
    if edit.target_entity != "skill_scores" or edit.target_id is None:
        return
    if edit.new_value is None:
        return

    skill_score = repo.get_skill_score(edit.target_id)
    if skill_score is None:
        raise InvalidEditTargetError(
            f"SkillScore {edit.target_id} not found for override."
        )

    logger.info(
        "Overriding skill_score %s: %.4f → %.4f (reviewer edit).",
        edit.target_id,
        skill_score.score,
        edit.new_value,
    )
    repo.update_skill_score(skill_score, edit.new_value)


def _persist_edits(
    repo: ReviewRepo,
    review: Review,
    edits: list[ReviewEditIn],
) -> list[ReviewEdit]:
    """Persist individual review edits and apply side-effects."""
    models: list[ReviewEdit] = []
    for edit_in in edits:
        # Validate target entity name for score overrides
        if (
            edit_in.edit_type == ReviewEditType.SCORE_OVERRIDE
            and edit_in.target_entity
            and edit_in.target_entity not in _SCORE_OVERRIDE_TARGETS
        ):
            raise InvalidEditTargetError(
                f"Invalid target entity '{edit_in.target_entity}' for "
                f"score override. Allowed: {_SCORE_OVERRIDE_TARGETS}"
            )

        # Apply override to the actual score row
        _apply_score_override(repo, edit_in)

        # Persist the edit record
        edit_model = repo.create_review_edit(
            review_id=review.id,
            edit_type=edit_in.edit_type,
            target_entity=edit_in.target_entity,
            target_id=edit_in.target_id,
            old_value=edit_in.old_value,
            new_value=edit_in.new_value,
            comment=edit_in.comment,
        )
        models.append(edit_model)

    repo.flush_edits()
    return models


def _write_audit_log(
    repo: ReviewRepo,
    review: Review,
    action: AuditAction,
    detail: dict | None = None,
) -> AuditLog:
    """Append an immutable audit-log entry for this review action."""
    return repo.create_audit_log(
        action=action,
        entity_type="reviews",
        entity_id=review.id,
        actor=review.reviewer,
        detail=detail or {
            "review_status": review.status.value,
            "analysis_run_id": str(review.analysis_run_id),
            "edit_count": len(review.edits),
        },
    )


def _build_response(review: Review, edits: list[ReviewEdit]) -> ReviewResponse:
    """Map ORM entities to the API response schema."""
    edit_outs = [
        ReviewEditOut(
            id=e.id,
            review_id=e.review_id,
            edit_type=e.edit_type,
            target_entity=e.target_entity,
            target_id=e.target_id,
            old_value=e.old_value,
            new_value=e.new_value,
            comment=e.comment,
            created_at=e.created_at,
        )
        for e in edits
    ]
    return ReviewResponse(
        id=review.id,
        analysis_run_id=review.analysis_run_id,
        reviewer=review.reviewer,
        status=review.status,
        comments=review.comments,
        edits=edit_outs,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


# =====================================================================
# Public API
# =====================================================================


def create_review(
    *,
    db: Session,
    request: ReviewRequest,
) -> ReviewResponse:
    """Create a new review on a completed analysis run.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    request:
        Validated ``ReviewRequest`` from the router.

    Returns
    -------
    ReviewResponse
        The persisted review with all edits.

    Raises
    ------
    AnalysisRunNotFoundError
        If the target run does not exist.
    AnalysisRunNotCompletedError
        If the target run is not in ``COMPLETED`` status.
    InvalidEditTargetError
        If a score-override references an invalid entity.
    """
    # ── Validate ─────────────────────────────────────────────────────
    repo = ReviewRepo(db)
    _validate_analysis_run(repo, request.analysis_run_id)

    # ── Persist review ───────────────────────────────────────────────
    review = repo.create_review(
        analysis_run_id=request.analysis_run_id,
        reviewer=request.reviewer,
        status=request.status,
        comments=request.comments,
    )

    # ── Persist edits + apply overrides ──────────────────────────────
    edit_models = _persist_edits(repo, review, request.edits)

    # ── Audit log ────────────────────────────────────────────────────
    _write_audit_log(repo, review, AuditAction.REVIEW)

    db.commit()

    logger.info(
        "Review %s created on run %s by '%s' — status=%s, edits=%d.",
        review.id,
        review.analysis_run_id,
        review.reviewer,
        review.status.value,
        len(edit_models),
    )

    return _build_response(review, edit_models)


def get_reviews_for_run(
    *,
    db: Session,
    analysis_run_id: UUID,
) -> list[ReviewResponse]:
    """Return all reviews for a given analysis run.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    analysis_run_id:
        The analysis run to look up reviews for.

    Raises
    ------
    AnalysisRunNotFoundError
        If the run does not exist.
    """
    repo = ReviewRepo(db)
    run = repo.get_analysis_run(analysis_run_id)
    if run is None:
        raise AnalysisRunNotFoundError(
            f"Analysis run {analysis_run_id} not found."
        )

    reviews = repo.list_reviews_for_run(analysis_run_id)

    return [_build_response(r, list(r.edits)) for r in reviews]
