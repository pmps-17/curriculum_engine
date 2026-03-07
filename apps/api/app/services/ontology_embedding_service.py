"""Ontology embedding service — ensure skill embeddings exist in the DB.

Iterates over all skills in the active ontology, builds a rich text
representation for each (name + description + top indicator texts),
batch-embeds them via the configured ``EmbeddingProvider``, and upserts
the vectors into ``skill_embeddings`` via the ``VectorStore``.

This is **idempotent**: by default it skips skills that already have an
embedding for the active model.  Pass ``force_rebuild=True`` to
re-embed everything.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.adapters.embeddings.base import EmbeddingProvider
from app.adapters.vector_store.base import VectorStore
from app.models.ontology import OntologyVersion, Skill
from app.repositories.embedding_repo import EmbeddingRepo

logger = logging.getLogger(__name__)

#: Maximum number of indicator texts to include in the skill
#: representation.  Keeps the input manageable for short-context models.
_MAX_INDICATORS_PER_SKILL: int = 10

#: Batch size for embedding calls (controls memory usage).
_EMBED_BATCH_SIZE: int = 64


# =====================================================================
# Result value object
# =====================================================================


@dataclass(frozen=True, slots=True)
class OntologyEmbeddingResult:
    """Summary returned after ensuring skill embeddings exist."""

    model_name: str
    total_skills: int
    created: int
    skipped: int


# =====================================================================
# Helpers
# =====================================================================


def _build_skill_text(skill: Skill) -> str:
    """Build a rich text representation of a skill for embedding.

    Format::

        Skill Name. Skill description.
        Indicators: indicator_1 text; indicator_2 text; …

    Limiting to the first ``_MAX_INDICATORS_PER_SKILL`` indicators keeps
    the text within typical model context windows.
    """
    parts: list[str] = []

    parts.append(skill.name)
    if skill.description:
        parts.append(skill.description)

    indicators = list(skill.indicators)[:_MAX_INDICATORS_PER_SKILL]
    if indicators:
        indicator_texts = "; ".join(
            ind.indicator_text for ind in indicators if ind.indicator_text
        )
        if indicator_texts:
            parts.append(f"Indicators: {indicator_texts}")

    return ". ".join(parts)


# =====================================================================
# Public API
# =====================================================================


def ensure_skill_embeddings(
    *,
    db: Session,
    ontology_version: OntologyVersion,
    embedding_provider: EmbeddingProvider,
    vector_store: VectorStore,
    force_rebuild: bool = False,
) -> OntologyEmbeddingResult:
    """Ensure every skill in *ontology_version* has a stored embedding.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    ontology_version:
        The ontology whose skills need embeddings.
    embedding_provider:
        The provider that converts text → vectors.
    vector_store:
        The store that persists vectors.
    force_rebuild:
        If ``True``, re-embed and upsert every skill regardless of
        whether an embedding already exists.

    Returns
    -------
    OntologyEmbeddingResult
        Counts of created / skipped skills and the model used.
    """
    model_name = embedding_provider.model_name

    # Collect all skills from the ontology tree
    all_skills: list[Skill] = []
    for pillar in ontology_version.pillars:
        all_skills.extend(pillar.skills)

    if not all_skills:
        logger.warning("No skills found in ontology version %s.", ontology_version.id)
        return OntologyEmbeddingResult(
            model_name=model_name, total_skills=0, created=0, skipped=0,
        )

    # Determine which skills need embedding
    if force_rebuild:
        skills_to_embed = all_skills
    else:
        embedding_repo = EmbeddingRepo(db)
        existing_ids = embedding_repo.get_existing_skill_ids(model_name)
        skills_to_embed = [s for s in all_skills if s.id not in existing_ids]

    skipped = len(all_skills) - len(skills_to_embed)

    if not skills_to_embed:
        logger.info(
            "All %d skill embeddings already exist for model '%s' — skipping.",
            len(all_skills),
            model_name,
        )
        return OntologyEmbeddingResult(
            model_name=model_name,
            total_skills=len(all_skills),
            created=0,
            skipped=skipped,
        )

    # Build texts and batch-embed
    texts = [_build_skill_text(s) for s in skills_to_embed]
    created = 0

    for batch_start in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch_texts = texts[batch_start : batch_start + _EMBED_BATCH_SIZE]
        batch_skills = skills_to_embed[batch_start : batch_start + _EMBED_BATCH_SIZE]

        vectors = embedding_provider.embed_texts(batch_texts)

        for skill, vector in zip(batch_skills, vectors):
            vector_store.upsert_skill_embedding(
                skill_id=skill.id,
                vector=vector,
                model_name=model_name,
            )
            created += 1

    logger.info(
        "Skill embeddings: %d created, %d skipped (model='%s', ontology=%s).",
        created,
        skipped,
        model_name,
        ontology_version.id,
    )

    return OntologyEmbeddingResult(
        model_name=model_name,
        total_skills=len(all_skills),
        created=created,
        skipped=skipped,
    )
