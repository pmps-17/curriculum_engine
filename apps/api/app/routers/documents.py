"""Documents router — access-controlled document metadata, preview, download,
and Curriculum Library list / patch / delete.

Endpoints
---------
- ``GET    /api/v1/documents``                        — library list (org-scoped)
- ``PATCH  /api/v1/documents/{document_id}``          — update metadata
- ``PATCH  /api/v1/documents/{document_id}/content``  — replace text/file
- ``DELETE /api/v1/documents/{document_id}``           — soft-delete
- ``GET    /api/v1/documents/{document_id}``           — single-doc detail
- ``GET    /api/v1/documents/{document_id}/preview``   — truncated text preview
- ``GET    /api/v1/documents/{document_id}/download``  — stream original file
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db
from app.repositories.document_repo import DEFAULT_PREVIEW_LIMIT, DocumentRepo
from app.repositories.organization_repo import OrganizationRepo
from app.schemas.documents import (
    DocumentContentResponse,
    DocumentDetail,
    DocumentLibraryItem,
    DocumentMeta,
    DocumentPreview,
    DocumentUpdateRequest,
)
from app.services.document_service import (
    DocumentAccessError,
    DocumentNotFoundError,
    delete_document,
    get_document_detail,
    list_documents,
    update_document,
    update_document_content,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

# ── helpers ──────────────────────────────────────────────────────────


def _require_document(doc_repo: DocumentRepo, document_id: uuid.UUID):
    """Fetch or 404."""
    doc = doc_repo.get_document(document_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return doc


def _enforce_membership(
    db: Session,
    organization_id: uuid.UUID | None,
    user_id: uuid.UUID,
) -> None:
    """Raise 403 when the document belongs to an organization the user is not a member of."""
    if organization_id is None:
        return  # no organization — no restriction
    org_repo = OrganizationRepo(db)
    if not org_repo.is_member(organization_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization.",
        )


def _extraction_status_label(doc) -> str:
    """Derive the extraction-status string from the Document model."""
    if doc.raw_text:
        return "EXTRACTED"
    if doc.parse_error:
        return "REJECTED"
    return "STORED_ONLY"


# ── GET /api/v1/documents  (Library list) ────────────────────────────


@router.get(
    "",
    response_model=list[DocumentLibraryItem],
    status_code=status.HTTP_200_OK,
    summary="List documents for an organization (Library grid)",
    responses={
        403: {"description": "Not a member of the organization."},
    },
)
def list_library_documents(
    organization_id: uuid.UUID = Query(..., description="Organization to list documents for"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[DocumentLibraryItem]:
    """Return document summaries for the Curriculum Library grid."""
    try:
        return list_documents(
            db=db,
            current_user=current_user,
            organization_id=organization_id,
            limit=limit,
            offset=offset,
        )
    except DocumentAccessError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc))


# ── PATCH /api/v1/documents/{document_id} ────────────────────────────


@router.patch(
    "/{document_id}",
    response_model=DocumentLibraryItem,
    status_code=status.HTTP_200_OK,
    summary="Update document metadata",
    responses={
        403: {"description": "Not a member of the organization."},
        404: {"description": "Document not found."},
    },
)
def patch_document(
    document_id: uuid.UUID,
    body: DocumentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentLibraryItem:
    """Patch user-facing metadata (title, subject, grade_band)."""
    try:
        return update_document(
            db=db,
            current_user=current_user,
            document_id=document_id,
            body=body,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
    except DocumentAccessError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc))


# ── DELETE /api/v1/documents/{document_id} ───────────────────────────


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a document",
    responses={
        403: {"description": "Not a member of the organization."},
        404: {"description": "Document not found."},
    },
)
def remove_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Response:
    """Soft-delete a document (sets deleted_at, excluded from future queries)."""
    try:
        delete_document(
            db=db,
            current_user=current_user,
            document_id=document_id,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
    except DocumentAccessError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── GET /api/v1/documents/{document_id} ─────────────────────────────


@router.get(
    "/{document_id}",
    response_model=DocumentDetail,
    status_code=status.HTTP_200_OK,
    summary="Document detail (metadata + extracted text)",
    responses={
        401: {"description": "Not authenticated."},
        403: {"description": "Not a member of the organization."},
        404: {"description": "Document not found."},
    },
)
def get_document_detail_endpoint(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentDetail:
    """Return full document detail including extracted text."""
    try:
        return get_document_detail(
            db=db,
            current_user=current_user,
            document_id=document_id,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
    except DocumentAccessError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc))


# ── PATCH /api/v1/documents/{document_id}/content ───────────────────


@router.patch(
    "/{document_id}/content",
    response_model=DocumentContentResponse,
    status_code=status.HTTP_200_OK,
    summary="Replace document content (text or file)",
    responses={
        400: {"description": "No content provided."},
        403: {"description": "Not a member of the organization."},
        404: {"description": "Document not found."},
    },
)
async def patch_document_content(
    document_id: uuid.UUID,
    curriculum_text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentContentResponse:
    """Replace curriculum content — either pasted text or a new file."""
    if curriculum_text is None and file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either curriculum_text or file.",
        )

    file_bytes: bytes | None = None
    filename: str | None = None
    mime_type: str | None = None

    if file is not None:
        file_bytes = await file.read()
        filename = file.filename
        mime_type = file.content_type

    try:
        return update_document_content(
            db=db,
            current_user=current_user,
            document_id=document_id,
            curriculum_text=curriculum_text if file is None else None,
            file_bytes=file_bytes,
            filename=filename,
            mime_type=mime_type,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
    except DocumentAccessError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc))


# ── GET /api/v1/documents/{document_id}/preview ─────────────────────


@router.get(
    "/{document_id}/preview",
    response_model=DocumentPreview,
    status_code=status.HTTP_200_OK,
    summary="Truncated text preview",
    responses={
        401: {"description": "Not authenticated."},
        403: {"description": "Not a member of the organization."},
        404: {"description": "Document not found."},
        409: {"description": "Text not extracted for this document."},
    },
)
def get_document_preview(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentPreview:
    """Return the first *N* characters of extracted text."""
    doc_repo = DocumentRepo(db)
    doc = _require_document(doc_repo, document_id)
    _enforce_membership(db, doc.organization_id, current_user.user_id)

    result = doc_repo.get_document_preview(document_id, limit=DEFAULT_PREVIEW_LIMIT)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Text has not been extracted for this document.",
        )

    preview_text, truncated = result
    return DocumentPreview(
        document_id=doc.id,
        preview_text=preview_text,
        preview_truncated=truncated,
        char_count=len(preview_text),
    )


# ── GET /api/v1/documents/{document_id}/download ────────────────────


@router.get(
    "/{document_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download original file",
    responses={
        401: {"description": "Not authenticated."},
        403: {"description": "Not a member of the organization."},
        404: {"description": "Document or file not found."},
    },
)
def download_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    """Stream the original uploaded file as an attachment."""
    doc_repo = DocumentRepo(db)
    doc = _require_document(doc_repo, document_id)
    _enforce_membership(db, doc.organization_id, current_user.user_id)

    file_path = doc_repo.get_file_path(document_id)
    if file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original file not found on disk.",
        )

    media_type = doc.mime_type or "application/octet-stream"

    def _iter_file():
        with open(file_path, "rb") as fh:
            while chunk := fh.read(64 * 1024):  # 64 KB chunks
                yield chunk

    return StreamingResponse(
        _iter_file(),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.filename}"',
            "Content-Length": str(file_path.stat().st_size),
        },
    )
