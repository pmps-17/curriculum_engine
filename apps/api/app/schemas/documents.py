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
    organization_id: Optional[UUID] = None
    created_at: datetime


class DocumentDetail(DocumentMeta):
    """Full document detail including extracted text (single-doc fetch)."""

    title: Optional[str] = None
    subject: Optional[str] = None
    grade_band: Optional[str] = None
    extracted_text: Optional[str] = Field(
        default=None,
        description="Full extracted text. None when extraction_status != EXTRACTED.",
    )


# ── Preview (GET /api/v1/documents/{id}/preview) ────────────────────

class DocumentPreview(CamelModel):
    """Truncated text preview of an extracted document."""

    document_id: UUID
    preview_text: str
    preview_truncated: bool
    char_count: int = Field(
        description="Length of the returned preview_text."
    )


# ── Library list item (GET /api/v1/documents?organization_id=…) ─────

class DocumentLibraryItem(CamelModel):
    """Summary row for a document in the Curriculum Library grid."""

    document_id: UUID
    title: Optional[str] = Field(
        default=None,
        description="User-given title; falls back to filename when None.",
    )
    filename: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    extraction_status: str
    subject: Optional[str] = None
    grade_band: Optional[str] = None
    curriculum_set_id: Optional[UUID] = None
    created_at: datetime
    latest_analysis_run_id: Optional[UUID] = None
    latest_analysis_status: Optional[str] = None


# ── Patch request (PATCH /api/v1/documents/{document_id}) ───────────

class DocumentUpdateRequest(CamelModel):
    """Partial update of user-facing metadata on a document."""

    title: Optional[str] = Field(
        default=None, min_length=1, max_length=500,
        description="Display title.",
    )
    subject: Optional[str] = Field(
        default=None, max_length=255,
        description="Subject area (send null to clear).",
    )
    grade_band: Optional[str] = Field(
        default=None, max_length=100,
        description="Grade band (send null to clear).",
    )


# ── Content update response (PATCH /api/v1/documents/{id}/content) ──

class DocumentContentResponse(CamelModel):
    """Returned after replacing document content."""

    document_id: UUID
    extraction_status: str
    char_count: Optional[int] = Field(
        default=None,
        description="Character count of newly extracted / supplied text.",
    )
