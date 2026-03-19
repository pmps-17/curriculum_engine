"""Uploads router for handling file uploads.

- POST /api/v1/uploads
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db
from app.repositories.document_repo import DEFAULT_PREVIEW_LIMIT, DocumentRepo
from app.repositories.organization_repo import OrganizationRepo
from app.schemas.documents import UploadResponse
from app.services.upload_service import process_upload, UploadError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Uploads"])


@router.post(
    "/uploads",
    status_code=status.HTTP_200_OK,
    response_model=UploadResponse,
    summary="Upload curriculum file",
)
async def upload_document(
    file: UploadFile = File(..., description="Curriculum document file (PDF, DOCX, TXT, etc.)"),
    organization_id: str = Form(..., description="Organization UUID (required)"),
    title: Optional[str] = Form(None, description="Document title"),
    subject: Optional[str] = Form(None, description="Subject/topic"),
    grade_band: Optional[str] = Form(None, description="Grade level/band (e.g., 3-5)"),
    school_id: Optional[str] = Form(None, description="School UUID"),
    include_preview: bool = Query(False, description="Include a truncated text preview in the response."),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UploadResponse:
    """
    Upload a curriculum document file.

    **Supported file types:**
    - PDF, DOCX, DOC, TXT, MD, HTML, RTF
    - Or any other file (will be stored without text extraction)

    **File size limit:** 25MB

    **Returns:**
    - `document_id`: UUID of created document
    - `extraction_status`: Whether text was extracted ("EXTRACTED" | "STORED_ONLY" | "REJECTED")
    - `warnings`: Any extraction warnings (optional)
    - `preview_text`: First 2 000 chars of extracted text (only when `?include_preview=true`)

    **Example:**
    ```
    curl -X POST http://localhost:8000/api/v1/uploads \\
      -H "Authorization: Bearer <token>" \\
      -F "file=@curriculum.pdf" \\
      -F "organization_id=<UUID>" \\
      -F "title=Grade 5 Science" \\
      -F "subject=Science" \\
      -F "grade_band=3-5"
    ```
    """
    if not file:
        raise HTTPException(status_code=400, detail="File is required")

    # ── Organization membership check ─────────────────────────────────
    try:
        resolved_organization_id = uuid.UUID(organization_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid organization_id format.")

    org_repo = OrganizationRepo(db)
    org = org_repo.get_by_id(resolved_organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found.")
    if not org_repo.is_member(resolved_organization_id, current_user.user_id):
        raise HTTPException(status_code=403, detail="Not a member of this organization.")

    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"[uploads] Failed to read file: {e}")
        raise HTTPException(status_code=400, detail="Failed to read file")

    # Process upload (validate, store, extract)
    try:
        result = process_upload(
            file_bytes=content,
            filename=file.filename or "unknown",
            mime_type=file.content_type or "application/octet-stream",
        )
    except UploadError as e:
        logger.warning(f"[uploads] Upload validation error: {e}")
        # Determine HTTP status based on error type
        if "exceeds" in str(e).lower():
            raise HTTPException(status_code=413, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    # Create document record in database
    try:
        doc_repo = DocumentRepo(db)

        # Ensure school_id is a valid UUID; use a placeholder if not provided
        if school_id:
            try:
                school_uuid = uuid.UUID(school_id)
            except (ValueError, AttributeError):
                school_uuid = uuid.uuid4()
        else:
            school_uuid = uuid.uuid4()

        # Create batch and document (use service-generated ID so DB
        # id matches the on-disk filename for downloads)
        batch, doc = doc_repo.create_upload_batch_and_document(
            school_id=school_uuid,
            filename=result.filename,
            mime_type=result.mime_type,
            size_bytes=result.size_bytes,
            document_type=result.document_type,
            extracted_text=result.extracted_text,
            title=title,
            subject=subject,
            grade_band=grade_band,
            organization_id=resolved_organization_id,
            document_id=result.document_id,
            curriculum_set_id=None,
        )

        db.commit()

        logger.info(
            f"[uploads] Document created: {doc.id} (filename={result.filename}, "
            f"extraction={result.extraction_status})"
        )

        # Build response — never include full extracted text
        preview_text: str | None = None
        preview_truncated: bool | None = None
        if include_preview and result.extracted_text:
            full_len = len(result.extracted_text)
            preview_text = result.extracted_text[:DEFAULT_PREVIEW_LIMIT]
            preview_truncated = full_len > DEFAULT_PREVIEW_LIMIT

        return UploadResponse(
            document_id=str(doc.id),
            filename=result.filename,
            content_type=result.mime_type,
            size_bytes=result.size_bytes,
            extraction_status=result.extraction_status,
            warnings=result.warnings if result.warnings else None,
            preview_text=preview_text,
            preview_truncated=preview_truncated,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[uploads] Database error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create document record")
