"""Embedding-domain models.

Stores precomputed vector embeddings for chunks and skills so that
similarity-based matching can replace (or augment) keyword search.

Both tables use pgvector's ``VECTOR(384)`` column type, matching the
output dimensionality of *sentence-transformers/all-MiniLM-L6-v2*.
"""

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class ChunkEmbedding(Base):
    """Vector embedding for a single :class:`~app.models.curriculum.Chunk`.

    One row per chunk.  The ``embedding_model_name`` column records which
    model produced the vector so that mixed-model scenarios are traceable.
    """

    __tablename__ = "chunk_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    embedding_model_name: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    embedding_vector: Mapped[list[float]] = mapped_column(
        Vector(384), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Indexes ──────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_chunk_embeddings_model_name", "embedding_model_name"),
    )

    # ── Relationships ────────────────────────────────────────────────
    chunk: Mapped["Chunk"] = relationship(  # noqa: F821
        back_populates="embedding",
    )


class SkillEmbedding(Base):
    """Vector embedding for a single :class:`~app.models.ontology.Skill`.

    One row per skill.  Used to compare skill descriptions against chunk
    embeddings via cosine / L2 distance queries.
    """

    __tablename__ = "skill_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    embedding_model_name: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    embedding_vector: Mapped[list[float]] = mapped_column(
        Vector(384), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Indexes ──────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_skill_embeddings_model_name", "embedding_model_name"),
    )

    # ── Relationships ────────────────────────────────────────────────
    skill: Mapped["Skill"] = relationship(  # noqa: F821
        back_populates="embedding",
    )
