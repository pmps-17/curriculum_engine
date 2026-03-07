"""Results router — ``GET /api/v1/results/{analysis_run_id}``.

Returns the full stored result for a previously-completed analysis run,
including pillar scores, skill scores, evidence, findings, compliance
results, and review history.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.results import ResultResponse
from app.services.results_service import RunNotFoundError, get_result

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Results"])


@router.get(
    "/results/{analysis_run_id}",
    response_model=ResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a stored analysis result",
    description=(
        "Returns the full analysis output for a given run ID, including "
        "pillar/skill scores, evidence snippets, findings, intake "
        "compliance results, and review history."
    ),
    responses={
        200: {"description": "Result retrieved successfully."},
        404: {"description": "Analysis run not found."},
    },
)
def get_analysis_result(
    analysis_run_id: UUID,
    db: Session = Depends(get_db),
) -> ResultResponse:
    """Fetch and return a stored analysis result by run ID."""
    try:
        return get_result(db=db, analysis_run_id=analysis_run_id)

    except RunNotFoundError as exc:
        logger.info("Run not found: %s", analysis_run_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
