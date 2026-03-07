"""Port (interface) for vector storage and similarity retrieval.

Services depend on this abstraction to store and query embedding vectors.
The concrete implementation (pgvector, Pinecone, Qdrant, etc.) is
injected at runtime via the dependency layer.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


# ── Value object returned by similarity queries ──────────────────────

@dataclass(frozen=True, slots=True)
class SkillCandidate:
    """A skill matched via vector similarity search.

    Attributes
    ----------
    skill_id:
        Primary key of the matched :class:`~app.models.ontology.Skill`.
    distance:
        Raw cosine distance (0 = identical, 2 = opposite).
    similarity_score:
        Normalised similarity derived as ``1 - distance``.  Values
        closer to 1.0 indicate stronger alignment.
    model_name:
        Which embedding model produced this match (for traceability).
    """

    skill_id: uuid.UUID
    distance: float
    similarity_score: float
    model_name: str


# ── Protocol ─────────────────────────────────────────────────────────

@runtime_checkable
class VectorStore(Protocol):
    """Contract that every vector-store adapter must fulfil."""

    def upsert_chunk_embedding(
        self,
        chunk_id: uuid.UUID,
        vector: list[float],
        model_name: str,
    ) -> None:
        """Insert or update the embedding for a single chunk.

        If a row already exists for *(chunk_id, model_name)* it is
        updated in place; otherwise a new row is inserted.
        """
        ...

    def upsert_skill_embedding(
        self,
        skill_id: uuid.UUID,
        vector: list[float],
        model_name: str,
    ) -> None:
        """Insert or update the embedding for a single skill.

        Same upsert semantics as :meth:`upsert_chunk_embedding`.
        """
        ...

    def query_similar_skills(
        self,
        query_vector: list[float],
        model_name: str,
        top_k: int = 5,
    ) -> list[SkillCandidate]:
        """Find the *top_k* most similar skills to a query vector.

        Parameters
        ----------
        query_vector:
            The embedding of the source text (e.g. a chunk).
        model_name:
            Only compare against skill embeddings produced by this model.
        top_k:
            Maximum number of results to return.

        Returns
        -------
        list[SkillCandidate]
            Ordered by ascending distance (best match first).
        """
        ...
