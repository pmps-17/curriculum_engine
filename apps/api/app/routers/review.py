"""Review router — create and list human reviews on analysis runs.

Endpoints:

- ``POST /api/v1/reviews``                          — create a review
- ``GET  /api/v1/reviews/{analysis_run_id}``         — list reviews for a run
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db
from app.repositories.organization_repo import OrganizationRepo
from app.schemas.review import ReviewRequest, ReviewResponse
from app.services.review_service import (
    AnalysisRunNotCompletedError,
    AnalysisRunNotFoundError,
    InvalidEditTargetError,
    ReviewError,
    create_review,
    get_reviews_for_run,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Reviews"])


@router.post(
    "/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a human review",
    description=(
        "Create a review (approve, reject, comment, or override scores) "
        "on a completed analysis run.  Human reviews are authoritative."
    ),
    responses={
        201: {"description": "Review created successfully."},
        404: {"description": "Analysis run not found."},
        409: {"description": "Analysis run is not in a reviewable state."},
        422: {"description": "Invalid edit target or validation error."},
    },
)
def submit_review(
    request: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ReviewResponse:
    """Create a new review on an analysis run."""
    try:
        return create_review(db=db, request=request)

    except AnalysisRunNotFoundError as exc:
        logger.info("Review target not found: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except AnalysisRunNotCompletedError as exc:
        logger.info("Run not reviewable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except InvalidEditTargetError as exc:
        logger.warning("Invalid edit target: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except ReviewError as exc:
        logger.error("Review failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Review error: {exc}",
        ) from exc


@router.get(
    "/reviews/{analysis_run_id}",
    response_model=list[ReviewResponse],
    status_code=status.HTTP_200_OK,
    summary="List reviews for an analysis run",
    description="Returns all human reviews attached to a given analysis run.",
    responses={
        200: {"description": "Reviews returned."},
        404: {"description": "Analysis run not found."},
    },
)
def list_reviews(
    analysis_run_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[ReviewResponse]:
    """Return all reviews for a specific analysis run."""
    try:
        return get_reviews_for_run(db=db, analysis_run_id=analysis_run_id)

    except AnalysisRunNotFoundError as exc:
        logger.info("Run not found: %s", analysis_run_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
