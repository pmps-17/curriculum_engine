"""Document repository for managing document records."""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisRun
from app.models.curriculum import CurriculumItem, Document, UploadBatch, School
from app.models.enums import DocumentStatus, DocumentType, UploadBatchStatus

# Must match upload_service.STORAGE_DIR
_STORAGE_DIR = Path(__file__).parent.parent.parent / "storage"

# Default preview limit (characters)
DEFAULT_PREVIEW_LIMIT = 2000


class DocumentRepo:
    """Repository for document-related database operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_document(
        self,
        upload_batch_id: uuid.UUID,
        filename: str,
        mime_type: str,
        size_bytes: int,
        document_type: str,
        extracted_text: Optional[str] = None,
        status: str = DocumentStatus.UPLOADED.value,
        organization_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        curriculum_set_id: Optional[uuid.UUID] = None,
        title: Optional[str] = None,
        subject: Optional[str] = None,
        grade_band: Optional[str] = None,
    ) -> Document:
        """
        Create a document record in the database.

        Args:
            upload_batch_id: ID of the upload batch
            filename: Original filename
            mime_type: MIME type
            size_bytes: File size in bytes
            document_type: Document type (from DocumentType enum)
            extracted_text: Extracted text (optional)
            status: Document status (default: UPLOADED)
            organization_id: Organization UUID for tenancy (optional)
            document_id: Pre-assigned UUID (matches on-disk file name)

        Returns:
            Created Document model instance
        """
        kwargs: dict = dict(
            upload_batch_id=upload_batch_id,
            filename=filename,
            mime_type=mime_type,
            file_size_bytes=size_bytes,
            document_type=document_type,
            raw_text=extracted_text,
            status=status,
            organization_id=organization_id,
            curriculum_set_id=curriculum_set_id,
            title=title,
            subject=subject,
            grade_band=grade_band,
        )
        if document_id is not None:
            kwargs["id"] = document_id
        doc = Document(**kwargs)
        self.db.add(doc)
        self.db.flush()
        return doc

    def get_document(self, document_id: uuid.UUID) -> Optional[Document]:
        """
        Retrieve a document by ID.

        Args:
            document_id: Document UUID

        Returns:
            Document model or None if not found
        """
        stmt = select(Document).where(Document.id == document_id)
        return self.db.scalars(stmt).first()

    def update_document_extraction(
        self,
        document_id: uuid.UUID,
        extracted_text: Optional[str],
        extraction_status: str,
        warnings: Optional[list[str]] = None,
    ) -> Optional[Document]:
        """
        Update document with extraction results.

        Args:
            document_id: Document UUID
            extracted_text: Extracted text from file
            extraction_status: "EXTRACTED" | "STORED_ONLY" | "REJECTED"
            warnings: Optional list of warnings

        Returns:
            Updated Document or None if not found
        """
        doc = self.get_document(document_id)
        if not doc:
            return None

        doc.raw_text = extracted_text
        doc.status = (
            DocumentStatus.PROCESSED
            if extraction_status == "EXTRACTED"
            else DocumentStatus.UPLOADED
        )

        if warnings:
            doc.parse_error = "; ".join(warnings)

        self.db.flush()
        return doc

    def create_upload_batch_and_document(
        self,
        school_id: uuid.UUID,
        filename: str,
        mime_type: str,
        size_bytes: int,
        document_type: str,
        extracted_text: Optional[str] = None,
        title: Optional[str] = None,
        subject: Optional[str] = None,
        grade_band: Optional[str] = None,
        organization_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        curriculum_set_id: Optional[uuid.UUID] = None,
    ) -> tuple[UploadBatch, Document]:
        """
        Create an upload batch and document in one transaction.

        This is a convenience method for file uploads that don't have
        an existing batch.

        For POC: if school doesn't exist, creates a default school first.

        Args:
            school_id: School UUID
            filename: Document filename
            mime_type: MIME type
            size_bytes: File size in bytes
            document_type: Document type
            extracted_text: Extracted text (optional)
            subject: Subject/topic (optional)
            grade_band: Grade band (optional)
            organization_id: Organization UUID for tenancy (optional)
            document_id: Pre-assigned UUID (matches on-disk filename)

        Returns:
            Tuple of (UploadBatch, Document)
        """
        from sqlalchemy import select

        # POC: Check if school exists; if not, create it
        school_stmt = select(School).where(School.id == school_id)
        school = self.db.scalars(school_stmt).first()

        if not school:
            # Create default school for POC
            school = School(
                id=school_id,
                name=f"School {str(school_id)[:8]}",
                description="Auto-created school for file uploads",
            )
            self.db.add(school)
            self.db.flush()

        # Create upload batch
        batch = UploadBatch(
            school_id=school_id,
            status=UploadBatchStatus.COMPLETED,
            notes=f"File: {filename}; Subject: {subject or 'N/A'}; Grade: {grade_band or 'N/A'}",
        )
        self.db.add(batch)
        self.db.flush()

        # Create document
        doc = self.create_document(
            upload_batch_id=batch.id,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            document_type=document_type,
            extracted_text=extracted_text,
            organization_id=organization_id,
            document_id=document_id,
            curriculum_set_id=curriculum_set_id,
            title=title,
            subject=subject,
            grade_band=grade_band,
        )

        return batch, doc

    # ── New privacy / access-controlled helpers ──────────────────────

    def get_document_preview(
        self,
        document_id: uuid.UUID,
        limit: int = DEFAULT_PREVIEW_LIMIT,
    ) -> tuple[str, bool] | None:
        """Return (preview_text, truncated) or *None* if not found / not extracted."""
        doc = self.get_document(document_id)
        if doc is None or not doc.raw_text:
            return None
        text = doc.raw_text
        truncated = len(text) > limit
        return text[:limit], truncated

    def get_file_path(self, document_id: uuid.UUID) -> Path | None:
        """Return the on-disk path for the stored file, or *None*."""
        path = _STORAGE_DIR / f"{document_id}.bin"
        return path if path.is_file() else None

    # ── Library (org-scoped) helpers ─────────────────────────────────

    def list_for_organization(
        self,
        organization_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Return document summaries for an organization (newest first).

        Joins through ``curriculum_items`` → ``analysis_runs`` to derive
        ``latest_analysis_run_id`` and ``latest_analysis_status``.

        Only non-deleted documents are returned.
        Returns plain dicts — the service maps them into Pydantic models.
        """
        from sqlalchemy import func, literal_column
        from sqlalchemy.orm import aliased

        # Subquery: latest analysis run per document
        # path: analysis_runs.curriculum_item_id → curriculum_items.document_id
        latest_run_sq = (
            select(
                CurriculumItem.document_id.label("doc_id"),
                func.max(AnalysisRun.created_at).label("max_created"),
            )
            .join(CurriculumItem, CurriculumItem.id == AnalysisRun.curriculum_item_id)
            .group_by(CurriculumItem.document_id)
            .subquery("latest_run_sq")
        )

        # Subquery: get the actual run row for the latest created_at
        LatestRun = aliased(AnalysisRun, name="lr")
        LatestCI = aliased(CurriculumItem, name="lci")

        run_detail_sq = (
            select(
                LatestCI.document_id.label("doc_id"),
                LatestRun.id.label("run_id"),
                LatestRun.status.label("run_status"),
            )
            .join(LatestCI, LatestCI.id == LatestRun.curriculum_item_id)
            .join(
                latest_run_sq,
                (LatestCI.document_id == latest_run_sq.c.doc_id)
                & (LatestRun.created_at == latest_run_sq.c.max_created),
            )
            .subquery("run_detail_sq")
        )

        # Derive extraction_status as a SQL expression
        extraction_status_expr = case(
            (Document.raw_text.isnot(None), literal_column("'EXTRACTED'")),
            (Document.parse_error.isnot(None), literal_column("'REJECTED'")),
            else_=literal_column("'STORED_ONLY'"),
        ).label("extraction_status")

        stmt = (
            select(
                Document.id.label("document_id"),
                Document.title,
                Document.filename,
                Document.mime_type.label("content_type"),
                Document.file_size_bytes.label("size_bytes"),
                extraction_status_expr,
                Document.subject,
                Document.grade_band,
                Document.curriculum_set_id,
                Document.created_at,
                run_detail_sq.c.run_id.label("latest_analysis_run_id"),
                run_detail_sq.c.run_status.label("latest_analysis_status"),
            )
            .outerjoin(
                run_detail_sq,
                run_detail_sq.c.doc_id == Document.id,
            )
            .where(Document.organization_id == organization_id)
            .where(Document.deleted_at.is_(None))
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        rows = self.db.execute(stmt).mappings().all()
        return [dict(r) for r in rows]

    # ── Mutable fields accepted by update() ─────────────────────────

    _MUTABLE_FIELDS: frozenset = frozenset({"title", "subject", "grade_band"})

    def update(self, doc: Document, **kwargs: object) -> Document:
        """Patch mutable metadata fields on a document. Flushes only."""
        for key, value in kwargs.items():
            if key not in self._MUTABLE_FIELDS:
                raise ValueError(f"Field '{key}' is not a mutable document field.")
            setattr(doc, key, value)
        self.db.flush()
        return doc

    def update_content(
        self,
        doc: Document,
        extracted_text: Optional[str],
        extraction_status: str,
        warnings: Optional[list[str]] = None,
    ) -> Document:
        """Replace document content (raw_text) and update status. Flushes only."""
        doc.raw_text = extracted_text
        doc.status = (
            DocumentStatus.PROCESSED
            if extraction_status == "EXTRACTED"
            else DocumentStatus.UPLOADED
        )
        doc.parse_error = "; ".join(warnings) if warnings else None
        self.db.flush()
        return doc

    def soft_delete(self, doc: Document) -> None:
        """Set ``deleted_at`` to now. Flushes but does not commit."""
        doc.deleted_at = datetime.now(timezone.utc)
        self.db.flush()
