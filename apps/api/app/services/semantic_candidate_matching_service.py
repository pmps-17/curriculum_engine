"""Semantic candidate matching service — embedding-based skill retrieval.

This is the **primary** matching strategy.  It embeds curriculum chunks
via the configured ``EmbeddingProvider``, then queries
``skill_embeddings`` via pgvector cosine distance to find the most
relevant skills.

The output is a list of ``CandidateMatchInput`` objects — the **same**
structure the scoring service consumes — so it is a drop-in replacement
for the keyword-based matcher (which now serves as fallback only).

Design notes
------------
- Chunk embeddings are cached: if a ``ChunkEmbedding`` row already
  exists for ``(chunk_id, model_name)`` it is reused.
- Skill embeddings are ensured via ``ontology_embedding_service`` before
  any similarity queries run.
- Similarity is ``1 - cosine_distance`` clamped to ``[0, 1]``.
- Candidates are **skill_id-centered**: ``indicator_id`` is always
  ``None`` -- we match at the skill level, not the indicator level.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.adapters.embeddings.base import EmbeddingProvider
from app.adapters.vector_store.base import VectorStore
from app.models.curriculum import Chunk as ChunkModel, Section as SectionModel
from app.models.enums import MatchMethod, PillarCode, SectionType
from app.models.ontology import OntologyVersion, Skill
from app.repositories.embedding_repo import EmbeddingRepo
from app.services.ontology_embedding_service import ensure_skill_embeddings
from app.services.scoring_service import CandidateMatchInput

logger = logging.getLogger(__name__)


# =====================================================================
# Input value object (lightweight struct for chunk info)
# =====================================================================


@dataclass(frozen=True, slots=True)
class ChunkInfo:
    """Minimal chunk descriptor passed into the semantic matcher."""

    chunk_id: uuid.UUID
    chunk_index: int
    section_type: SectionType
    chunk_text: str


# =====================================================================
# Result value object
# =====================================================================


@dataclass(frozen=True, slots=True)
class SemanticMatchingResult:
    """Wrapper around the candidate list with diagnostic metadata."""

    candidates: list[CandidateMatchInput]
    model_name: str
    chunks_embedded: int
    chunks_cached: int


# =====================================================================
# Internal helpers
# =====================================================================


def _build_chunk_infos(
    chunk_models: list[ChunkModel],
    section_models: list[SectionModel],
) -> list[ChunkInfo]:
    """Convert ORM chunk/section models into lightweight ``ChunkInfo``s."""
    section_type_by_id: dict[uuid.UUID, SectionType] = {
        sm.id: sm.section_type for sm in section_models
    }
    return [
        ChunkInfo(
            chunk_id=cm.id,
            chunk_index=cm.chunk_index,
            section_type=section_type_by_id.get(cm.section_id, SectionType.OTHER),
            chunk_text=cm.chunk_text,
        )
        for cm in chunk_models
    ]


def _build_skill_lookup(
    ontology_version: OntologyVersion,
) -> dict[uuid.UUID, Skill]:
    """Build a flat skill_id → Skill mapping from the ontology tree."""
    lookup: dict[uuid.UUID, Skill] = {}
    for pillar in ontology_version.pillars:
        for skill in pillar.skills:
            lookup[skill.id] = skill
    return lookup


# =====================================================================
# Public API
# =====================================================================


def run_semantic_matching(
    *,
    db: Session,
    ontology_version: OntologyVersion,
    chunk_models: list[ChunkModel],
    section_models: list[SectionModel],
    embedding_provider: EmbeddingProvider,
    vector_store: VectorStore,
    top_k: int = 5,
    min_similarity: float = 0.22,
) -> SemanticMatchingResult:
    """Produce candidate matches using embedding similarity search.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    ontology_version:
        Ontology with eagerly-loaded pillars/skills/indicators.
    chunk_models:
        Persisted chunk ORM instances.
    section_models:
        Persisted section ORM instances (for section-type lookup).
    embedding_provider:
        Provider that converts text → vectors.
    vector_store:
        Store for upserting / querying vectors.
    top_k:
        How many similar skills to retrieve per chunk.
    min_similarity:
        Minimum similarity score (``1 - distance``) to accept a match.

    Returns
    -------
    SemanticMatchingResult
        Candidates in the same ``CandidateMatchInput`` structure that
        the scoring service expects.
    """
    model_name = embedding_provider.model_name

    # ── 1. Ensure skill embeddings exist ─────────────────────────────
    ensure_skill_embeddings(
        db=db,
        ontology_version=ontology_version,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    # ── 2. Build chunk infos & skill lookup ──────────────────────────
    chunk_infos = _build_chunk_infos(chunk_models, section_models)
    skill_lookup = _build_skill_lookup(ontology_version)

    if not chunk_infos or not skill_lookup:
        return SemanticMatchingResult(
            candidates=[], model_name=model_name,
            chunks_embedded=0, chunks_cached=0,
        )

    # ── 3. Embed chunks (skip cached) ───────────────────────────────
    embedding_repo = EmbeddingRepo(db)
    cached_ids = embedding_repo.get_cached_chunk_ids(model_name)
    chunks_to_embed = [ci for ci in chunk_infos if ci.chunk_id not in cached_ids]
    chunks_cached = len(chunk_infos) - len(chunks_to_embed)

    if chunks_to_embed:
        texts = [ci.chunk_text for ci in chunks_to_embed]
        vectors = embedding_provider.embed_texts(texts)

        for ci, vector in zip(chunks_to_embed, vectors):
            vector_store.upsert_chunk_embedding(
                chunk_id=ci.chunk_id,
                vector=vector,
                model_name=model_name,
            )

    # ── 4. For each chunk, query similar skills ──────────────────────
    candidates: list[CandidateMatchInput] = []

    # Re-read all chunk embeddings so cached ones are included
    all_chunk_vectors = embedding_repo.load_chunk_vectors(
        chunk_ids=[ci.chunk_id for ci in chunk_infos],
        model_name=model_name,
    )

    for ci in chunk_infos:
        query_vector = all_chunk_vectors.get(ci.chunk_id)
        if query_vector is None:
            continue

        skill_candidates = vector_store.query_similar_skills(
            query_vector=query_vector,
            model_name=model_name,
            top_k=top_k,
        )

        for sc in skill_candidates:
            similarity = max(0.0, min(1.0, sc.similarity_score))
            if similarity < min_similarity:
                continue

            skill = skill_lookup.get(sc.skill_id)
            if skill is None:
                continue

            pillar = skill.pillar

            candidates.append(
                CandidateMatchInput(
                    candidate_id=uuid.uuid4(),
                    chunk_index=ci.chunk_index,
                    section_type=ci.section_type,
                    skill_id=skill.id,
                    skill_code=skill.code,
                    skill_name=skill.name,
                    pillar_id=pillar.id,
                    pillar_code=PillarCode(pillar.code),
                    pillar_name=pillar.name,
                    indicator_id=None,  # semantic match is skill-level
                    raw_score=similarity,
                    match_method=MatchMethod.EMBEDDING,
                    matched_keywords=None,
                )
            )

    logger.info(
        "Semantic matching: %d chunk(s) → %d candidate(s) "
        "(model='%s', top_k=%d, min_sim=%.2f, embedded=%d, cached=%d).",
        len(chunk_infos),
        len(candidates),
        model_name,
        top_k,
        min_similarity,
        len(chunks_to_embed),
        chunks_cached,
    )

    return SemanticMatchingResult(
        candidates=candidates,
        model_name=model_name,
        chunks_embedded=len(chunks_to_embed),
        chunks_cached=chunks_cached,
    )
