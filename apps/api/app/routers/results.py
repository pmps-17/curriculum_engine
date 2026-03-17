"""Results router — ``GET /api/v1/results/{analysis_run_id}``.

Returns the full stored result for a previously-completed analysis run,
including pillar scores, skill scores, evidence, findings, compliance
results, and review history.

If the analysis run has an ``organization_id``, the caller must be a member
of that organization (verified via ``get_current_user``).
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db
from app.repositories.organization_repo import OrganizationRepo
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
        401: {"description": "Not authenticated."},
        403: {"description": "Not a member of the organization."},
        404: {"description": "Analysis run not found."},
    },
)
def get_analysis_result(
    analysis_run_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ResultResponse:
    """Fetch and return a stored analysis result by run ID."""
    try:
        result = get_result(db=db, analysis_run_id=analysis_run_id)
    except RunNotFoundError as exc:
        logger.info("Run not found: %s", analysis_run_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    # ── Organization isolation check ───────────────────────────────────
    from app.models.analysis import AnalysisRun

    run = db.get(AnalysisRun, analysis_run_id)
    if run and run.organization_id:
        org_repo = OrganizationRepo(db)
        if not org_repo.is_member(run.organization_id, current_user.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization.",
            )

    return result
