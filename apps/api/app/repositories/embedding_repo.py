"""Repository for embedding-related read queries.

Provides helpers to check which skill/chunk embeddings already exist
and to bulk-load chunk embedding vectors.  Write operations are handled
by the ``VectorStore`` adapter — this repo only reads.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.embeddings import ChunkEmbedding, SkillEmbedding


class EmbeddingRepo:
    """Thin read-only data-access layer for embedding lookup tables."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_existing_skill_ids(self, model_name: str) -> set[uuid.UUID]:
        """Return skill IDs that already have an embedding for *model_name*."""
        stmt = (
            select(SkillEmbedding.skill_id)
            .where(SkillEmbedding.embedding_model_name == model_name)
        )
        return set(self._db.scalars(stmt).all())

    def get_cached_chunk_ids(self, model_name: str) -> set[uuid.UUID]:
        """Return chunk IDs that already have an embedding for *model_name*."""
        stmt = (
            select(ChunkEmbedding.chunk_id)
            .where(ChunkEmbedding.embedding_model_name == model_name)
        )
        return set(self._db.scalars(stmt).all())

    def load_chunk_vectors(
        self,
        chunk_ids: list[uuid.UUID],
        model_name: str,
    ) -> dict[uuid.UUID, list[float]]:
        """Load embedding vectors for the given chunk IDs.

        Returns a mapping of ``chunk_id → vector`` (as a plain list of
        floats).  Chunks without an embedding are silently omitted.
        """
        if not chunk_ids:
            return {}

        stmt = (
            select(ChunkEmbedding.chunk_id, ChunkEmbedding.embedding_vector)
            .where(
                ChunkEmbedding.chunk_id.in_(chunk_ids),
                ChunkEmbedding.embedding_model_name == model_name,
            )
        )
        result: dict[uuid.UUID, list[float]] = {}
        for row in self._db.execute(stmt).all():
            vec = row.embedding_vector
            result[row.chunk_id] = (
                vec.tolist() if hasattr(vec, "tolist") else list(vec)
            )
        return result
