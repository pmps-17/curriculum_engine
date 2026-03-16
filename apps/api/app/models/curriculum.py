"""Curriculum-domain models.

Covers the ingestion and structural decomposition side of the engine:
schools → upload batches → documents → packages / subjects →
curriculum items → sections → chunks.  Also includes assessment
artifacts linked to curriculum items.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import (
    CurriculumItemType,
    DocumentStatus,
    DocumentType,
    SectionType,
    UploadBatchStatus,
)
from app.models.mixins import TimestampMixin


# ── School ───────────────────────────────────────────────────────────

class School(TimestampMixin, Base):
    """An institution whose curriculum is being analysed."""

    __tablename__ = "schools"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    upload_batches: Mapped[list["UploadBatch"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )
    curriculum_packages: Mapped[list["CurriculumPackage"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )


# ── Upload Batch ─────────────────────────────────────────────────────

class UploadBatch(TimestampMixin, Base):
    """A logical grouping of documents uploaded together."""

    __tablename__ = "upload_batches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False
    )
    status: Mapped[UploadBatchStatus] = mapped_column(
        String(30), default=UploadBatchStatus.PENDING, nullable=False
    )
    uploaded_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    school: Mapped["School"] = relationship(back_populates="upload_batches")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="upload_batch", cascade="all, delete-orphan"
    )


# ── Document ─────────────────────────────────────────────────────────

class Document(TimestampMixin, Base):
    """A single uploaded file (PDF, DOCX, etc.)."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    upload_batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("upload_batches.id"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        String(30), default=DocumentType.OTHER, nullable=False
    )
    status: Mapped[DocumentStatus] = mapped_column(
        String(30), default=DocumentStatus.UPLOADED, nullable=False
    )
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    upload_batch: Mapped["UploadBatch"] = relationship(back_populates="documents")
    curriculum_items: Mapped[list["CurriculumItem"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    sections: Mapped[list["Section"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


# ── Curriculum Package ───────────────────────────────────────────────

class CurriculumPackage(TimestampMixin, Base):
    """A top-level curriculum bundle (e.g. 'Grade 5 Science 2026')."""

    __tablename__ = "curriculum_packages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    grade_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    academic_year: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # relationships
    school: Mapped["School"] = relationship(back_populates="curriculum_packages")
    subjects: Mapped[list["Subject"]] = relationship(
        back_populates="curriculum_package", cascade="all, delete-orphan"
    )


# ── Subject ──────────────────────────────────────────────────────────

class Subject(TimestampMixin, Base):
    """A subject area within a curriculum package (e.g. 'Mathematics')."""

    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    curriculum_package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("curriculum_packages.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    curriculum_package: Mapped["CurriculumPackage"] = relationship(
        back_populates="subjects"
    )
    curriculum_items: Mapped[list["CurriculumItem"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )


# ── Curriculum Item ──────────────────────────────────────────────────

class CurriculumItem(TimestampMixin, Base):
    """A normalised lesson / activity / unit extracted from a document."""

    __tablename__ = "curriculum_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    item_type: Mapped[CurriculumItemType] = mapped_column(
        String(30), default=CurriculumItemType.LESSON, nullable=False
    )
    sequence_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # relationships
    document: Mapped["Document"] = relationship(back_populates="curriculum_items")
    subject: Mapped["Subject | None"] = relationship(
        back_populates="curriculum_items"
    )
    assessment_artifacts: Mapped[list["AssessmentArtifact"]] = relationship(
        back_populates="curriculum_item", cascade="all, delete-orphan"
    )
    sections: Mapped[list["Section"]] = relationship(
        back_populates="curriculum_item", cascade="all, delete-orphan"
    )


# ── Assessment Artifact ──────────────────────────────────────────────

class AssessmentArtifact(TimestampMixin, Base):
    """An assessment or rubric artefact attached to a curriculum item."""

    __tablename__ = "assessment_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    curriculum_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("curriculum_items.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    artifact_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # relationships
    curriculum_item: Mapped["CurriculumItem"] = relationship(
        back_populates="assessment_artifacts"
    )


# ── Section ──────────────────────────────────────────────────────────

class Section(TimestampMixin, Base):
    """A semantic section extracted from a document or curriculum item."""

    __tablename__ = "sections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    curriculum_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("curriculum_items.id"), nullable=True
    )
    section_type: Mapped[SectionType] = mapped_column(
        String(30), default=SectionType.OTHER, nullable=False
    )
    heading: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sequence_order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # relationships
    document: Mapped["Document"] = relationship(back_populates="sections")
    curriculum_item: Mapped["CurriculumItem | None"] = relationship(
        back_populates="sections"
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="section", cascade="all, delete-orphan"
    )


# ── Chunk ────────────────────────────────────────────────────────────

class Chunk(TimestampMixin, Base):
    """A small text fragment derived from a section for analysis.

    Chunks are the atomic unit fed into scoring / embedding pipelines.
    """

    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sections.id"), nullable=False
    )
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # relationships
    section: Mapped["Section"] = relationship(back_populates="chunks")
    embedding: Mapped["ChunkEmbedding | None"] = relationship(
        back_populates="chunk", uselist=False, cascade="all, delete-orphan"
    )
