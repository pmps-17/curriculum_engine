"""Evidence service — builds explainable evidence for skill and pillar scores.

Takes the raw candidate matches (the same list fed into the scoring
service) together with a chunk-text lookup, and produces a concise,
ranked set of evidence snippets per skill.

The service is **pure**: no DB reads or writes.

Selection strategy (v1)
-----------------------
1. For each skill, collect all candidate matches.
2. Compute a ``contribution`` for each candidate:
   ``raw_score × section_type_weight``.
3. Sort descending by contribution.
4. Take the top ``MAX_EVIDENCE_PER_SKILL`` candidates.
5. Truncate the snippet text to ``MAX_SNIPPET_CHARS`` for UI display.
"""

from __future__ import annotations

import enum
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from uuid import UUID

from app.models.enums import PillarCode, SectionType
from app.services.scoring_service import (
    SECTION_TYPE_WEIGHTS,
    CandidateMatchInput,
    ScoringResult,
    _ev,
)

logger = logging.getLogger(__name__)


# =====================================================================
# Configuration
# =====================================================================

#: Maximum evidence snippets retained per skill.
MAX_EVIDENCE_PER_SKILL: int = 5

#: Maximum character length for a single snippet displayed in the UI.
MAX_SNIPPET_CHARS: int = 500


# =====================================================================
# Enums
# =====================================================================


class ReasonType(str, enum.Enum):
    """Why this snippet was selected as evidence.

    Allows the UI to show a badge/icon next to each snippet.
    """

    KEYWORD_MATCH = "keyword_match"
    HIGH_WEIGHT_SECTION = "high_weight_section"
    STRONG_RAW_SCORE = "strong_raw_score"
    GENERAL = "general"


# =====================================================================
# Value objects
# =====================================================================


@dataclass(frozen=True)
class EvidenceSnippet:
    """A single piece of supporting evidence for a skill score.

    Attributes:
        skill_id:           Skill this evidence supports.
        skill_code:         Human-readable skill code.
        pillar_id:          Parent pillar.
        pillar_code:        Pillar code enum value.
        chunk_index:        Source chunk position within its section.
        section_type:       Section the evidence was drawn from.
        snippet_text:       Text excerpt (may be truncated).
        reason_type:        Why this snippet was selected.
        contribution:       raw_score × section_weight (sort key).
        relevance_score:    Normalised [0, 1] relevance for the API.
        matched_keywords:   Keywords that triggered the match, if any.
    """

    skill_id: UUID
    skill_code: str
    pillar_id: UUID
    pillar_code: PillarCode
    chunk_index: int
    section_type: SectionType
    snippet_text: str
    reason_type: ReasonType
    contribution: float
    relevance_score: float
    matched_keywords: str | None = None


@dataclass(frozen=True)
class EvidenceResult:
    """Complete evidence output for an analysis run."""

    snippets: list[EvidenceSnippet] = field(default_factory=list)
    total_candidates_evaluated: int = 0


# =====================================================================
# Internal helpers
# =====================================================================


def _get_weight(section_type: SectionType) -> float:
    """Return the section-type weight, consistent with the scoring service."""
    return SECTION_TYPE_WEIGHTS.get(section_type, 0.5)


def _truncate(text: str, max_chars: int = MAX_SNIPPET_CHARS) -> str:
    """Truncate *text* to *max_chars*, appending '…' if trimmed."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def _classify_reason(
    candidate: CandidateMatchInput,
    contribution: float,
    weight: float,
) -> ReasonType:
    """Determine the primary reason this candidate is good evidence.

    Heuristic priority:
    1. Explicit keyword match present → ``KEYWORD_MATCH``
    2. Section weight ≥ 2.0 (activity/assessment) → ``HIGH_WEIGHT_SECTION``
    3. Raw score ≥ 0.7 → ``STRONG_RAW_SCORE``
    4. Else → ``GENERAL``
    """
    if candidate.matched_keywords:
        return ReasonType.KEYWORD_MATCH
    if weight >= 2.0:
        return ReasonType.HIGH_WEIGHT_SECTION
    if candidate.raw_score >= 0.7:
        return ReasonType.STRONG_RAW_SCORE
    return ReasonType.GENERAL


def _normalise_relevance(
    contribution: float,
    max_contribution: float,
) -> float:
    """Normalise a contribution value to [0, 1] relative to the group max."""
    if max_contribution <= 0:
        return 0.0
    return round(min(contribution / max_contribution, 1.0), 4)


# =====================================================================
# Public API
# =====================================================================


def build_evidence(
    *,
    candidates: list[CandidateMatchInput],
    chunk_texts: dict[int, str],
    scoring_result: ScoringResult | None = None,
) -> EvidenceResult:
    """Select and rank evidence snippets from candidate matches.

    Parameters
    ----------
    candidates:
        The same candidate-match list fed into the scoring service.
    chunk_texts:
        Mapping from ``chunk_index`` → raw chunk text.  Used to pull
        the verbatim snippet.  If a chunk_index is missing the
        candidate is silently skipped.
    scoring_result:
        Optional — not currently used but reserved for future logic
        that might weight evidence differently based on final scores.

    Returns
    -------
    EvidenceResult
        Ranked, truncated evidence snippets ready for persistence and
        API responses.
    """
    if not candidates:
        return EvidenceResult(snippets=[], total_candidates_evaluated=0)

    # ── Group candidates by skill ────────────────────────────────────
    skill_groups: dict[UUID, list[CandidateMatchInput]] = defaultdict(list)
    for c in candidates:
        skill_groups[c.skill_id].append(c)

    all_snippets: list[EvidenceSnippet] = []

    for skill_id, matches in skill_groups.items():
        # Compute contribution for each candidate
        scored: list[tuple[CandidateMatchInput, float, float]] = []
        for m in matches:
            weight = _get_weight(m.section_type)
            contribution = m.raw_score * weight
            scored.append((m, contribution, weight))

        # Sort descending by contribution (deterministic: break ties by
        # chunk_index then indicator_id).
        scored.sort(
            key=lambda t: (-t[1], t[0].chunk_index, str(t[0].indicator_id))
        )

        # Take top-N
        top = scored[: MAX_EVIDENCE_PER_SKILL]

        # Find max contribution in this skill group for normalisation
        max_contrib = top[0][1] if top else 1.0

        for candidate, contribution, weight in top:
            raw_text = chunk_texts.get(candidate.chunk_index)
            if raw_text is None:
                # Chunk text not available — skip silently
                continue

            snippet_text = _truncate(raw_text)
            reason = _classify_reason(candidate, contribution, weight)
            relevance = _normalise_relevance(contribution, max_contrib)

            all_snippets.append(
                EvidenceSnippet(
                    skill_id=candidate.skill_id,
                    skill_code=candidate.skill_code,
                    pillar_id=candidate.pillar_id,
                    pillar_code=candidate.pillar_code,
                    chunk_index=candidate.chunk_index,
                    section_type=candidate.section_type,
                    snippet_text=snippet_text,
                    reason_type=reason,
                    contribution=round(contribution, 4),
                    relevance_score=relevance,
                    matched_keywords=candidate.matched_keywords,
                )
            )

    # Final sort: by pillar → skill → descending contribution
    all_snippets.sort(
        key=lambda s: (_ev(s.pillar_code), s.skill_code, -s.contribution)
    )

    logger.debug(
        "Evidence built: %d snippet(s) from %d candidate(s) across %d skill(s).",
        len(all_snippets),
        len(candidates),
        len(skill_groups),
    )

    return EvidenceResult(
        snippets=all_snippets,
        total_candidates_evaluated=len(candidates),
    )
