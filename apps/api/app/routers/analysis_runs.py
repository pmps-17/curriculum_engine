"""Analysis-runs router — ``GET /api/v1/analysis-runs``.

Lists analysis runs for an organization.  The endpoint is thin: it
validates membership, delegates to the repository, and maps the
rows into Pydantic response models.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db
from app.repositories.analysis_run_repo import AnalysisRunRepo
from app.repositories.organization_repo import OrganizationRepo
from app.schemas.analysis_runs import AnalysisRunSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Analysis Runs"])


@router.get(
    "/analysis-runs",
    response_model=list[AnalysisRunSummary],
    status_code=status.HTTP_200_OK,
    summary="List analysis runs for an organization",
    description=(
        "Returns a paginated list of analysis runs scoped to an organization, "
        "sorted by creation time (newest first)."
    ),
    responses={
        200: {"description": "List of analysis run summaries."},
        401: {"description": "Not authenticated."},
        403: {"description": "Not a member of the organization."},
        404: {"description": "Organization not found."},
    },
)
def list_analysis_runs(
    organization_id: UUID = Query(..., description="Organization to list runs for."),
    limit: int = Query(50, ge=1, le=200, description="Max rows to return."),
    offset: int = Query(0, ge=0, description="Pagination offset."),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[AnalysisRunSummary]:
    """List analysis runs for an organization with membership enforcement."""

    org_repo = OrganizationRepo(db)

    org = org_repo.get_by_id(organization_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )
    if not org_repo.is_member(organization_id, current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization.",
        )

    # ── Query ────────────────────────────────────────────────────────
    run_repo = AnalysisRunRepo(db)
    rows = run_repo.list_for_organization(organization_id, limit=limit, offset=offset)

    return [
        AnalysisRunSummary(
            analysis_run_id=r["analysis_run_id"],
            title=r.get("title"),
            subject=r.get("subject"),
            grade_band=None,  # not persisted on run; future enhancement
            status=r["status"],
            created_at=r["created_at"],
            document_id=r.get("document_id"),
        )
        for r in rows
    ]
