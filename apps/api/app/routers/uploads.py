"""Uploads router for handling file uploads.

- POST /api/v1/uploads
"""

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, status, HTTPException
from pydantic import BaseModel

from app.core.db import SessionLocal
from app.repositories.document_repo import DocumentRepository
from app.services.upload_service import process_upload, UploadError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Uploads"])


class UploadResponse(BaseModel):
    """Response from file upload endpoint."""

    document_id: str
    filename: str
    content_type: str
    size_bytes: int
    extraction_status: str  # "EXTRACTED" | "STORED_ONLY" | "REJECTED"
    extracted_text: Optional[str] = None
    warnings: Optional[list[str]] = None

    class Config:
        from_attributes = True


@router.post(
    "/uploads",
    status_code=status.HTTP_200_OK,
    response_model=UploadResponse,
    summary="Upload curriculum file",
)
async def upload_document(
    file: UploadFile = File(..., description="Curriculum document file (PDF, DOCX, TXT, etc.)"),
    title: Optional[str] = Form(None, description="Document title"),
    subject: Optional[str] = Form(None, description="Subject/topic"),
    grade_band: Optional[str] = Form(None, description="Grade level/band (e.g., 3-5)"),
    school_id: Optional[str] = Form(None, description="School UUID"),
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
    - `extracted_text`: Text content if successfully extracted (optional)
    - `warnings`: Any extraction warnings (optional)

    **Example:**
    ```
    curl -X POST http://localhost:8000/api/v1/uploads \\
      -F "file=@curriculum.pdf" \\
      -F "title=Grade 5 Science" \\
      -F "subject=Science" \\
      -F "grade_band=3-5"
    ```
    """
    if not file:
        raise HTTPException(status_code=400, detail="File is required")

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
    db = SessionLocal()
    try:
        doc_repo = DocumentRepository(db)

        # Ensure school_id is a valid UUID; use a placeholder if not provided
        import uuid

        if school_id:
            try:
                school_uuid = uuid.UUID(school_id)
            except (ValueError, AttributeError):
                school_uuid = uuid.uuid4()
        else:
            # For POC: create a default school if needed
            # In production, require school_id
            school_uuid = uuid.uuid4()

        # Create batch and document
        batch, doc = doc_repo.create_upload_batch_and_document(
            school_id=school_uuid,
            filename=result.filename,
            mime_type=result.mime_type,
            size_bytes=result.size_bytes,
            document_type=result.document_type,
            extracted_text=result.extracted_text,
            subject=subject,
            grade_band=grade_band,
        )

        db.commit()

        logger.info(
            f"[uploads] Document created: {doc.id} (filename={result.filename}, "
            f"extraction={result.extraction_status})"
        )

        # Return response (do NOT include raw extracted_text in logs)
        return UploadResponse(
            document_id=str(doc.id),
            filename=result.filename,
            content_type=result.mime_type,
            size_bytes=result.size_bytes,
            extraction_status=result.extraction_status,
            extracted_text=result.extracted_text,
            warnings=result.warnings if result.warnings else None,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"[uploads] Database error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create document record")
    finally:
        db.close()
