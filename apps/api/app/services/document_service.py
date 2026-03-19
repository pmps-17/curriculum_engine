"""Document service — business logic for the Curriculum Library.

Enforces organization-membership tenancy on every operation.
Repositories handle all SQLAlchemy access; this layer never
touches ``db`` directly beyond ``commit()``.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.repositories.document_repo import DocumentRepo
from app.repositories.organization_repo import OrganizationRepo
from app.schemas.documents import (
    DocumentContentResponse,
    DocumentDetail,
    DocumentLibraryItem,
    DocumentUpdateRequest,
)

logger = logging.getLogger(__name__)


# ── Exceptions (mapped to HTTP codes in the router) ──────────────────


class DocumentNotFoundError(Exception):
    """Raised when the document does not exist, is deleted, or not in the org."""


class DocumentAccessError(Exception):
    """Raised when the caller is not a member of the document's org."""


# ── Helpers ──────────────────────────────────────────────────────────


def _extraction_status_label(doc) -> str:
    """Derive the extraction-status string from the Document model."""
    if doc.raw_text:
        return "EXTRACTED"
    if doc.parse_error:
        return "REJECTED"
    return "STORED_ONLY"


def _ensure_membership(
    org_repo: OrganizationRepo,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Raise ``DocumentAccessError`` if user is not in the org."""
    if not org_repo.is_member(organization_id, user_id):
        raise DocumentAccessError("Not a member of this organization.")


# ── Public API ───────────────────────────────────────────────────────


def list_documents(
    *,
    db: Session,
    current_user: CurrentUser,
    organization_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[DocumentLibraryItem]:
    """Return document summaries for an organization the caller belongs to."""
    org_repo = OrganizationRepo(db)
    user = org_repo.upsert_user(current_user.email)
    _ensure_membership(org_repo, organization_id, user.id)

    doc_repo = DocumentRepo(db)
    rows = doc_repo.list_for_organization(
        organization_id, limit=limit, offset=offset,
    )
    return [
        DocumentLibraryItem(
            document_id=r["document_id"],
            title=r["title"],
            filename=r["filename"],
            content_type=r["content_type"],
            size_bytes=r["size_bytes"],
            extraction_status=r["extraction_status"],
            subject=r["subject"],
            grade_band=r["grade_band"],
            curriculum_set_id=r["curriculum_set_id"],
            created_at=r["created_at"],
            latest_analysis_run_id=r["latest_analysis_run_id"],
            latest_analysis_status=r["latest_analysis_status"],
        )
        for r in rows
    ]


def update_document(
    *,
    db: Session,
    current_user: CurrentUser,
    document_id: uuid.UUID,
    body: DocumentUpdateRequest,
) -> DocumentLibraryItem:
    """Patch user-facing metadata on a document. Caller must be a member."""
    org_repo = OrganizationRepo(db)
    user = org_repo.upsert_user(current_user.email)

    doc_repo = DocumentRepo(db)
    doc = doc_repo.get_document(document_id)
    if doc is None or doc.deleted_at is not None:
        raise DocumentNotFoundError("Document not found.")
    if doc.organization_id is None:
        raise DocumentNotFoundError("Document not found.")
    _ensure_membership(org_repo, doc.organization_id, user.id)

    # Build kwargs — only include fields the client actually sent
    kwargs: dict = {}
    for field_name in ("title", "subject", "grade_band"):
        if field_name in body.model_fields_set:
            kwargs[field_name] = getattr(body, field_name)

    if kwargs:
        doc_repo.update(doc, **kwargs)

    db.commit()
    logger.info(
        "Document %s updated by %s (fields: %s)",
        document_id,
        current_user.email,
        list(kwargs.keys()),
    )

    # Return an up-to-date summary (re-query to include latest analysis)
    for r in doc_repo.list_for_organization(doc.organization_id, limit=200, offset=0):
        if r["document_id"] == document_id:
            return DocumentLibraryItem(
                document_id=r["document_id"],
                title=r["title"],
                filename=r["filename"],
                content_type=r["content_type"],
                size_bytes=r["size_bytes"],
                extraction_status=r["extraction_status"],
                subject=r["subject"],
                grade_band=r["grade_band"],
                curriculum_set_id=r["curriculum_set_id"],
                created_at=r["created_at"],
                latest_analysis_run_id=r["latest_analysis_run_id"],
                latest_analysis_status=r["latest_analysis_status"],
            )

    # Fallback: build from the ORM object directly (no analysis info)
    return DocumentLibraryItem(
        document_id=doc.id,
        title=doc.title,
        filename=doc.filename,
        content_type=doc.mime_type,
        size_bytes=doc.file_size_bytes,
        extraction_status=_extraction_status_label(doc),
        subject=doc.subject,
        grade_band=doc.grade_band,
        curriculum_set_id=doc.curriculum_set_id,
        created_at=doc.created_at,
        latest_analysis_run_id=None,
        latest_analysis_status=None,
    )


def delete_document(
    *,
    db: Session,
    current_user: CurrentUser,
    document_id: uuid.UUID,
) -> None:
    """Soft-delete a document. Caller must be a member of the org."""
    org_repo = OrganizationRepo(db)
    user = org_repo.upsert_user(current_user.email)

    doc_repo = DocumentRepo(db)
    doc = doc_repo.get_document(document_id)
    if doc is None or doc.deleted_at is not None:
        raise DocumentNotFoundError("Document not found.")
    if doc.organization_id is None:
        raise DocumentNotFoundError("Document not found.")
    _ensure_membership(org_repo, doc.organization_id, user.id)

    doc_repo.soft_delete(doc)
    db.commit()
    logger.info("Document %s soft-deleted by %s", document_id, current_user.email)


def get_document_detail(
    *,
    db: Session,
    current_user: CurrentUser,
    document_id: uuid.UUID,
) -> DocumentDetail:
    """Return full document detail including extracted text."""
    org_repo = OrganizationRepo(db)
    user = org_repo.upsert_user(current_user.email)

    doc_repo = DocumentRepo(db)
    doc = doc_repo.get_document(document_id)
    if doc is None or doc.deleted_at is not None:
        raise DocumentNotFoundError("Document not found.")
    if doc.organization_id is not None:
        _ensure_membership(org_repo, doc.organization_id, user.id)

    status_label = _extraction_status_label(doc)
    return DocumentDetail(
        document_id=doc.id,
        filename=doc.filename,
        content_type=doc.mime_type,
        size_bytes=doc.file_size_bytes,
        document_type=doc.document_type if isinstance(doc.document_type, str) else doc.document_type.value,
        extraction_status=status_label,
        warnings=doc.parse_error,
        organization_id=doc.organization_id,
        created_at=doc.created_at,
        title=doc.title,
        subject=doc.subject,
        grade_band=doc.grade_band,
        extracted_text=doc.raw_text if status_label == "EXTRACTED" else None,
    )


def update_document_content(
    *,
    db: Session,
    current_user: CurrentUser,
    document_id: uuid.UUID,
    curriculum_text: str | None = None,
    file_bytes: bytes | None = None,
    filename: str | None = None,
    mime_type: str | None = None,
) -> DocumentContentResponse:
    """Replace document content — either pasted text or a new file upload.

    Exactly one of ``curriculum_text`` or ``file_bytes`` must be provided.
    """
    from app.services.text_extraction_service import extract_text
    from app.services.upload_service import store_file_on_disk

    org_repo = OrganizationRepo(db)
    user = org_repo.upsert_user(current_user.email)

    doc_repo = DocumentRepo(db)
    doc = doc_repo.get_document(document_id)
    if doc is None or doc.deleted_at is not None:
        raise DocumentNotFoundError("Document not found.")
    if doc.organization_id is not None:
        _ensure_membership(org_repo, doc.organization_id, user.id)

    if curriculum_text is not None:
        # Direct text replacement
        extracted_text = curriculum_text
        extraction_status = "EXTRACTED" if extracted_text.strip() else "STORED_ONLY"
        warnings: list[str] = []
    elif file_bytes is not None:
        # Re-extract from uploaded file; also overwrite on-disk blob
        store_file_on_disk(file_bytes, document_id)
        extracted_text, extraction_status, warnings = extract_text(
            file_bytes, filename or doc.filename, mime_type or doc.mime_type or "",
        )
        # Update file-level metadata
        if filename:
            doc.filename = filename
        if mime_type:
            doc.mime_type = mime_type
        doc.file_size_bytes = len(file_bytes)
        db.flush()
    else:
        raise ValueError("Either curriculum_text or file must be provided.")

    doc_repo.update_content(doc, extracted_text, extraction_status, warnings or None)
    db.commit()

    logger.info(
        "Document %s content updated by %s (status=%s)",
        document_id,
        current_user.email,
        extraction_status,
    )

    return DocumentContentResponse(
        document_id=doc.id,
        extraction_status=extraction_status,
        char_count=len(extracted_text) if extracted_text else None,
    )
