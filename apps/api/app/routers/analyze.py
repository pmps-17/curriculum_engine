"""Analyze router — ``POST /api/v1/analyze``.

This router is intentionally **thin**.  All orchestration logic lives
in ``analyze_service.run_analysis()``.  The router's only jobs are:

1. Accept and validate the request body (Pydantic does this).
2. Inject the DB session.
3. Validate organization membership via ``get_current_user``.
4. Delegate to the service.
5. Map service exceptions to HTTP status codes.
6. Return the response.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db
from app.repositories.organization_repo import OrganizationRepo
from app.schemas.analysis import AnalyzeRequest, AnalyzeResponse
from app.services.analyze_service import (
    AnalysisError,
    DocumentNotFoundError,
    DocumentValidationError,
    IntakeRejectedError,
    OntologyNotFoundError,
    OrganizationAccessError,
    run_analysis,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Analysis"])


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Run curriculum pillar-mapping analysis",
    description=(
        "Accepts raw curriculum/lesson text, normalises it, runs intake "
        "compliance checks, performs keyword-based pillar mapping for "
        "P1/P2/P3, and returns scored, explainable results."
    ),
    responses={
        200: {"description": "Analysis completed successfully."},
        401: {"description": "Not authenticated."},
        403: {"description": "Not a member of the organization."},
        404: {"description": "Ontology version not found."},
        422: {"description": "Request validation failed or intake rejected."},
        500: {"description": "Internal analysis pipeline error."},
    },
)
def analyze(
    request: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> AnalyzeResponse:
    """Run the full analysis pipeline for a single curriculum item."""
    request_id = uuid.uuid4()

    # ── Organization membership check (if organization_id provided) ────
    if request.organization_id:
        org_repo = OrganizationRepo(db)
        org = org_repo.get_by_id(request.organization_id)
        if org is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )
        if not org_repo.is_member(request.organization_id, current_user.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization.",
            )

    # Structured log — never log raw curriculum/rubric text
    logger.info(
        "Analysis request received.",
        extra={
            "request_id": str(request_id),
            "title": request.title,
            "subject": request.subject,
            "grade_band": request.grade_band,
            "item_type": request.item_type.value,
            "text_length": len(request.curriculum_text) if request.curriculum_text else 0,
            "document_id": request.document_id,
            "has_rubric": request.rubric_text is not None,
            "triggered_by": request.triggered_by,
        },
    )

    try:
        response = run_analysis(db=db, request=request)

        logger.info(
            "Analysis completed.",
            extra={
                "request_id": str(request_id),
                "analysis_run_id": str(response.analysis_run_id),
                "status": response.status.value,
                "pillar_count": len(response.pillar_scores),
                "match_method": response.match_method.value,
                "overall_score": response.overall_score,
            },
        )
        return response

    except OntologyNotFoundError as exc:
        logger.warning("Ontology not found.", extra={"request_id": str(request_id), "error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DocumentNotFoundError as exc:
        logger.info("Document not found.", extra={"request_id": str(request_id), "error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DocumentValidationError as exc:
        logger.info("Document validation failed.", extra={"request_id": str(request_id), "error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except OrganizationAccessError as exc:
        logger.warning("Organization access denied.", extra={"request_id": str(request_id), "error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except IntakeRejectedError as exc:
        logger.info("Intake rejected.", extra={"request_id": str(request_id), "error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": str(exc),
                "compliance_results": exc.compliance_results,
            },
        ) from exc

    except AnalysisError as exc:
        logger.error("Analysis failed.", extra={"request_id": str(request_id), "error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis pipeline error: {exc}",
        ) from exc
