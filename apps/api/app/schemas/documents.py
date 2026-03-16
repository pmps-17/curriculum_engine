"""Pydantic schemas for the documents API.

Covers upload responses, document metadata, preview, and download
endpoints.  Designed so that full extracted text is **never** returned
in a list or metadata response — only via the explicit preview
endpoint (truncated).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.schemas.base import CamelModel


# ── Upload response (POST /api/v1/uploads) ───────────────────────────

class UploadResponse(CamelModel):
    """Returned from POST /api/v1/uploads.

    By default ``preview_text`` is ``None``.  Pass
    ``?include_preview=true`` to get the first *N* characters.
    """

    document_id: str
    filename: str
    content_type: str
    size_bytes: int
    extraction_status: str  # "EXTRACTED" | "STORED_ONLY" | "REJECTED"
    warnings: Optional[list[str]] = None
    preview_text: Optional[str] = Field(
        default=None,
        description="First N characters of extracted text (only when include_preview=true).",
    )
    preview_truncated: Optional[bool] = Field(
        default=None,
        description="True when the preview was truncated.",
    )


# ── Document metadata (GET /api/v1/documents/{id}) ──────────────────

class DocumentMeta(CamelModel):
    """Public metadata for a single document — no full text."""

    document_id: UUID
    filename: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    document_type: str
    extraction_status: str
    warnings: Optional[str] = None
    workspace_id: Optional[UUID] = None
    created_at: datetime


# ── Preview (GET /api/v1/documents/{id}/preview) ────────────────────

class DocumentPreview(CamelModel):
    """Truncated text preview of an extracted document."""

    document_id: UUID
    preview_text: str
    preview_truncated: bool
    char_count: int = Field(
        description="Length of the returned preview_text."
    )
