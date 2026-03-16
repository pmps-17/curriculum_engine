"""Repository for curriculum-domain persistence.

Handles creation of upload batches, documents, curriculum items,
sections, and chunks.  Each method builds ORM instances, adds them
to the session, and flushes — but never commits.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.curriculum import (
    Chunk as ChunkModel,
    CurriculumItem,
    Document,
    School,
    Section as SectionModel,
    UploadBatch,
)
from app.models.enums import (
    DocumentStatus,
    DocumentType,
    UploadBatchStatus,
)
from app.services.chunking_service import Chunk as ServiceChunk
from app.services.normalization_service import NormalizedItem, NormalizedSection


class CurriculumRepo:
    """Thin data-access layer for curriculum-domain tables."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_document(self, document_id: uuid.UUID) -> Document | None:
        """Retrieve a document by ID.

        Args:
            document_id: Document UUID

        Returns:
            Document model or None if not found
        """
        from sqlalchemy import select

        stmt = select(Document).where(Document.id == document_id)
        return self._db.scalars(stmt).first()

    def create_upload_batch_and_document(
        self,
        *,
        school_id: uuid.UUID | None,
        uploaded_by: str | None,
        curriculum_text: str,
        workspace_id: uuid.UUID | None = None,
    ) -> tuple[UploadBatch, Document]:
        """Create a minimal upload batch + inline document.

        Returns the batch and document (both flushed with IDs assigned).
        """
        from sqlalchemy import select

        resolved_school_id = school_id or uuid.uuid4()

        # POC: auto-create school if it doesn't exist
        stmt = select(School).where(School.id == resolved_school_id)
        existing = self._db.scalars(stmt).first()
        if not existing:
            school = School(
                id=resolved_school_id,
                name=f"School {str(resolved_school_id)[:8]}",
                description="Auto-created school for inline analysis",
            )
            self._db.add(school)
            self._db.flush()

        batch = UploadBatch(
            school_id=resolved_school_id,
            status=UploadBatchStatus.COMPLETED,
            uploaded_by=uploaded_by,
        )
        self._db.add(batch)
        self._db.flush()

        doc = Document(
            upload_batch_id=batch.id,
            filename=f"inline_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.txt",
            document_type=DocumentType.LESSON_PLAN,
            status=DocumentStatus.PARSED,
            raw_text=curriculum_text,
            workspace_id=workspace_id,
        )
        self._db.add(doc)
        self._db.flush()
        return batch, doc

    def create_curriculum_item(
        self,
        *,
        document_id: uuid.UUID,
        subject_id: uuid.UUID | None,
        title: str,
        item_type: str,
        description: str | None,
        unit_name: str | None,
    ) -> CurriculumItem:
        """Persist a normalised curriculum item."""
        ci = CurriculumItem(
            document_id=document_id,
            subject_id=subject_id,
            title=title or "Untitled",
            item_type=item_type,
            description=description,
            unit_name=unit_name,
        )
        self._db.add(ci)
        self._db.flush()
        return ci

    def create_sections_and_chunks(
        self,
        *,
        document_id: uuid.UUID,
        curriculum_item_id: uuid.UUID,
        normalized_sections: list[NormalizedSection],
        service_chunks: list[ServiceChunk],
    ) -> tuple[list[SectionModel], list[ChunkModel]]:
        """Persist sections and their chunks.  Returns both lists.

        Sections are created first so that chunks can reference their IDs.
        """
        section_models: list[SectionModel] = []
        chunk_models: list[ChunkModel] = []

        # Persist sections
        section_map: dict[int, SectionModel] = {}
        for ns in normalized_sections:
            sm = SectionModel(
                document_id=document_id,
                curriculum_item_id=curriculum_item_id,
                section_type=ns.section_type,
                heading=ns.heading,
                body_text=ns.body,
                sequence_order=ns.sequence,
            )
            self._db.add(sm)
            self._db.flush()
            section_map[ns.sequence] = sm
            section_models.append(sm)

        # Persist chunks, linking to sections
        for sc in service_chunks:
            section_model = section_map.get(sc.section_sequence)
            if section_model is None:
                continue
            cm = ChunkModel(
                section_id=section_model.id,
                chunk_text=sc.text,
                chunk_index=sc.chunk_index,
                token_count=sc.token_estimate,
            )
            self._db.add(cm)
            chunk_models.append(cm)

        self._db.flush()
        return section_models, chunk_models
