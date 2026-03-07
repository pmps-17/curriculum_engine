"""pgvector-backed vector store adapter.

Stores and retrieves embedding vectors using the ``chunk_embeddings``
and ``skill_embeddings`` tables via SQLAlchemy ORM models and the
pgvector cosine-distance operator (``<=>``).

This adapter performs **exact** nearest-neighbour search (no ANN index).
For large datasets, add an HNSW or IVFFlat index in a future migration.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.vector_store.base import SkillCandidate
from app.models.embeddings import ChunkEmbedding, SkillEmbedding

logger = logging.getLogger(__name__)


class PgVectorStore:
    """Vector store backed by PostgreSQL + pgvector.

    Parameters
    ----------
    db:
        An active SQLAlchemy session.  The caller (service / dependency
        layer) is responsible for committing or rolling back.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Chunk embeddings ─────────────────────────────────────────────

    def upsert_chunk_embedding(
        self,
        chunk_id: uuid.UUID,
        vector: list[float],
        model_name: str,
    ) -> None:
        """Insert or update the embedding for a chunk.

        If a ``ChunkEmbedding`` row already exists for *chunk_id* it is
        updated in place; otherwise a new row is inserted.  The session
        is flushed but **not** committed.
        """
        existing = self._db.execute(
            select(ChunkEmbedding).where(ChunkEmbedding.chunk_id == chunk_id)
        ).scalar_one_or_none()

        if existing is not None:
            existing.embedding_vector = vector
            existing.embedding_model_name = model_name
            logger.debug("Updated chunk embedding for chunk_id=%s", chunk_id)
        else:
            self._db.add(
                ChunkEmbedding(
                    chunk_id=chunk_id,
                    embedding_vector=vector,
                    embedding_model_name=model_name,
                )
            )
            logger.debug("Inserted chunk embedding for chunk_id=%s", chunk_id)

        self._db.flush()

    # ── Skill embeddings ─────────────────────────────────────────────

    def upsert_skill_embedding(
        self,
        skill_id: uuid.UUID,
        vector: list[float],
        model_name: str,
    ) -> None:
        """Insert or update the embedding for a skill.

        Same upsert semantics as :meth:`upsert_chunk_embedding`.
        """
        existing = self._db.execute(
            select(SkillEmbedding).where(SkillEmbedding.skill_id == skill_id)
        ).scalar_one_or_none()

        if existing is not None:
            existing.embedding_vector = vector
            existing.embedding_model_name = model_name
            logger.debug("Updated skill embedding for skill_id=%s", skill_id)
        else:
            self._db.add(
                SkillEmbedding(
                    skill_id=skill_id,
                    embedding_vector=vector,
                    embedding_model_name=model_name,
                )
            )
            logger.debug("Inserted skill embedding for skill_id=%s", skill_id)

        self._db.flush()

    # ── Similarity search ────────────────────────────────────────────

    def query_similar_skills(
        self,
        query_vector: list[float],
        model_name: str,
        top_k: int = 5,
    ) -> list[SkillCandidate]:
        """Find the *top_k* skills most similar to *query_vector*.

        Uses the pgvector **cosine distance** operator (``<=>``) which
        returns values in ``[0, 2]``:

        - ``0`` → identical direction
        - ``1`` → orthogonal
        - ``2`` → opposite direction

        Similarity is derived as ``1 - distance``.

        Parameters
        ----------
        query_vector:
            The embedding of the source text (e.g. a curriculum chunk).
        model_name:
            Only compare against skill embeddings produced by this model.
        top_k:
            Maximum number of results.

        Returns
        -------
        list[SkillCandidate]
            Ordered by ascending distance (best match first).
        """
        distance_expr = SkillEmbedding.embedding_vector.cosine_distance(query_vector)

        stmt = (
            select(
                SkillEmbedding.skill_id,
                distance_expr.label("distance"),
            )
            .where(SkillEmbedding.embedding_model_name == model_name)
            .order_by(distance_expr.asc())
            .limit(top_k)
        )

        rows = self._db.execute(stmt).all()

        candidates: list[SkillCandidate] = []
        for row in rows:
            candidates.append(
                SkillCandidate(
                    skill_id=row.skill_id,
                    distance=float(row.distance),
                    similarity_score=1.0 - float(row.distance),
                    model_name=model_name,
                )
            )

        logger.debug(
            "query_similar_skills returned %d candidates (model=%s, top_k=%d)",
            len(candidates),
            model_name,
            top_k,
        )
        return candidates
