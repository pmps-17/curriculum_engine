"""Documents router — access-controlled document metadata, preview & download.

Endpoints
---------
- ``GET  /api/v1/documents/{document_id}``          — metadata (no text)
- ``GET  /api/v1/documents/{document_id}/preview``   — truncated text preview
- ``GET  /api/v1/documents/{document_id}/download``  — stream original file
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db
from app.repositories.document_repo import DEFAULT_PREVIEW_LIMIT, DocumentRepo
from app.repositories.workspace_repo import WorkspaceRepo
from app.schemas.documents import DocumentMeta, DocumentPreview

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

# ── helpers ──────────────────────────────────────────────────────────


def _require_document(doc_repo: DocumentRepo, document_id: UUID):
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
    workspace_id: UUID | None,
    user_id: UUID,
) -> None:
    """Raise 403 when the document belongs to a workspace the user is not a member of."""
    if workspace_id is None:
        return  # no workspace — no restriction
    ws_repo = WorkspaceRepo(db)
    if not ws_repo.is_member(workspace_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace.",
        )


def _extraction_status_label(doc) -> str:
    """Derive the extraction-status string from the Document model."""
    if doc.raw_text:
        return "EXTRACTED"
    if doc.parse_error:
        return "REJECTED"
    return "STORED_ONLY"


# ── GET /api/v1/documents/{document_id} ─────────────────────────────


@router.get(
    "/{document_id}",
    response_model=DocumentMeta,
    status_code=status.HTTP_200_OK,
    summary="Document metadata",
    responses={
        401: {"description": "Not authenticated."},
        403: {"description": "Not a member of the workspace."},
        404: {"description": "Document not found."},
    },
)
def get_document_meta(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentMeta:
    """Return document metadata without any extracted text."""
    doc_repo = DocumentRepo(db)
    doc = _require_document(doc_repo, document_id)
    _enforce_membership(db, doc.workspace_id, current_user.user_id)

    return DocumentMeta(
        document_id=doc.id,
        filename=doc.filename,
        content_type=doc.mime_type,
        size_bytes=doc.file_size_bytes,
        document_type=doc.document_type if isinstance(doc.document_type, str) else doc.document_type.value,
        extraction_status=_extraction_status_label(doc),
        warnings=doc.parse_error,
        workspace_id=doc.workspace_id,
        created_at=doc.created_at,
    )


# ── GET /api/v1/documents/{document_id}/preview ─────────────────────


@router.get(
    "/{document_id}/preview",
    response_model=DocumentPreview,
    status_code=status.HTTP_200_OK,
    summary="Truncated text preview",
    responses={
        401: {"description": "Not authenticated."},
        403: {"description": "Not a member of the workspace."},
        404: {"description": "Document not found."},
        409: {"description": "Text not extracted for this document."},
    },
)
def get_document_preview(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentPreview:
    """Return the first *N* characters of extracted text."""
    doc_repo = DocumentRepo(db)
    doc = _require_document(doc_repo, document_id)
    _enforce_membership(db, doc.workspace_id, current_user.user_id)

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
        403: {"description": "Not a member of the workspace."},
        404: {"description": "Document or file not found."},
    },
)
def download_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    """Stream the original uploaded file as an attachment."""
    doc_repo = DocumentRepo(db)
    doc = _require_document(doc_repo, document_id)
    _enforce_membership(db, doc.workspace_id, current_user.user_id)

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
