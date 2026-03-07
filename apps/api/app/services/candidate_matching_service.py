"""Candidate matching service — keyword-based skill indicator matching.

Compares chunk text against skill indicator keyword lists to produce
candidate matches.  This is the **keyword fallback** strategy used
alongside the embedding-based semantic matcher in
``semantic_candidate_matching_service.py``.

The orchestrator (``analyze_service``) runs both matchers and merges
results via ``_merge_candidates()``, preferring semantic matches when
available.

The service is **read-only with respect to the database** — it reads
ontology data (pillars → skills → indicators) but writes nothing.
The orchestration service is responsible for persisting matches.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from app.models.curriculum import Chunk as ChunkModel, Section as SectionModel
from app.models.enums import MatchMethod, SectionType
from app.models.ontology import OntologyVersion, Pillar, Skill, SkillIndicator
from app.services.scoring_service import CandidateMatchInput

logger = logging.getLogger(__name__)


# =====================================================================
# Configuration
# =====================================================================

#: Minimum fraction of indicator keywords that must match for a
#: candidate to be emitted.  Set to 0 to allow single-keyword hits.
MIN_KEYWORD_MATCH_RATIO: float = 0.0


# =====================================================================
# Internal value object for pre-loaded indicators
# =====================================================================


@dataclass(frozen=True)
class _IndicatorContext:
    """Pre-loaded indicator with parent skill/pillar metadata."""

    indicator: SkillIndicator
    skill: Skill
    pillar: Pillar
    keywords: list[str]  # pre-split, lowered, stripped


# =====================================================================
# Internal helpers
# =====================================================================


def _preload_indicators(
    ontology_version: OntologyVersion,
) -> list[_IndicatorContext]:
    """Flatten the ontology tree into a list of indicator contexts.

    Walks pillars → skills → indicators once and pre-splits keyword
    strings so the hot loop doesn't repeat that work.
    """
    contexts: list[_IndicatorContext] = []
    for pillar in ontology_version.pillars:
        for skill in pillar.skills:
            for indicator in skill.indicators:
                raw = indicator.keywords or ""
                keywords = [
                    kw.strip().lower()
                    for kw in raw.split(",")
                    if kw.strip()
                ]
                if not keywords:
                    # No keywords → skip (nothing to match against)
                    continue
                contexts.append(
                    _IndicatorContext(
                        indicator=indicator,
                        skill=skill,
                        pillar=pillar,
                        keywords=keywords,
                    )
                )
    return contexts


def _build_section_type_lookup(
    section_models: list[SectionModel],
    chunk_models: list[ChunkModel],
) -> dict[uuid.UUID, SectionType]:
    """Build a mapping from chunk ID → SectionType.

    Two-step lookup: chunk → section → section_type.
    Falls back to ``SectionType.OTHER`` if any link is missing.
    """
    section_type_by_id = {
        sm.id: sm.section_type for sm in section_models
    }
    result: dict[uuid.UUID, SectionType] = {}
    for cm in chunk_models:
        st = section_type_by_id.get(cm.section_id, SectionType.OTHER)
        result[cm.id] = st
    return result


def _match_chunk_against_indicator(
    chunk_text_lower: str,
    ctx: _IndicatorContext,
) -> tuple[float, list[str]] | None:
    """Check whether *chunk_text_lower* matches *ctx*'s keywords.

    Returns ``(raw_score, matched_keywords)`` if there is a hit,
    or ``None`` if no keywords matched or the ratio is below the
    configured threshold.
    """
    matched = [kw for kw in ctx.keywords if kw in chunk_text_lower]
    if not matched:
        return None

    ratio = len(matched) / len(ctx.keywords)
    if ratio < MIN_KEYWORD_MATCH_RATIO:
        return None

    return ratio, matched


# =====================================================================
# Public API
# =====================================================================


def run_keyword_matching(
    *,
    ontology_version: OntologyVersion,
    chunk_models: list[ChunkModel],
    section_models: list[SectionModel],
) -> list[CandidateMatchInput]:
    """Match chunk text against ontology indicator keywords.

    For every ``(chunk, indicator)`` pair where at least one keyword
    appears in the chunk text (case-insensitive), a ``CandidateMatchInput``
    is emitted.

    Parameters
    ----------
    ontology_version:
        The active ontology with eagerly-loaded pillars/skills/indicators.
    chunk_models:
        Persisted chunk ORM instances with ``chunk_text`` populated.
    section_models:
        Persisted section ORM instances (for section-type lookup).

    Returns
    -------
    list[CandidateMatchInput]
        Zero or more candidate matches ready for the scoring service.

    Notes
    -----
    Complexity is O(chunks × indicators × avg_keywords).  For v1 data
    volumes (< 1 000 chunks, < 200 indicators) this is sub-millisecond.
    Embedding-based retrieval is handled by
    ``semantic_candidate_matching_service.run_semantic_matching()``.
    """
    indicators = _preload_indicators(ontology_version)
    if not indicators:
        logger.warning("No keyword indicators found in ontology — skipping matching.")
        return []

    chunk_section_types = _build_section_type_lookup(section_models, chunk_models)

    candidates: list[CandidateMatchInput] = []

    for cm in chunk_models:
        chunk_text_lower = cm.chunk_text.lower()
        section_type = chunk_section_types.get(cm.id, SectionType.OTHER)

        for ctx in indicators:
            result = _match_chunk_against_indicator(chunk_text_lower, ctx)
            if result is None:
                continue

            raw_score, matched_keywords = result

            candidates.append(
                CandidateMatchInput(
                    candidate_id=uuid.uuid4(),
                    chunk_index=cm.chunk_index,
                    section_type=section_type,
                    skill_id=ctx.skill.id,
                    skill_code=ctx.skill.code,
                    skill_name=ctx.skill.name,
                    pillar_id=ctx.pillar.id,
                    pillar_code=ctx.pillar.code,
                    pillar_name=ctx.pillar.name,
                    indicator_id=ctx.indicator.id,
                    raw_score=raw_score,
                    match_method=MatchMethod.KEYWORD,
                    matched_keywords=", ".join(matched_keywords),
                )
            )

    logger.debug(
        "Keyword matching: %d chunk(s) × %d indicator(s) → %d candidate(s).",
        len(chunk_models),
        len(indicators),
        len(candidates),
    )
    return candidates
