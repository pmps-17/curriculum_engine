"""Scoring service — converts candidate matches into skill and pillar scores.

This is **pure business logic**: no DB reads or writes.  The service
receives pre-fetched candidate matches and ontology metadata, applies
deterministic section-type weighting, and returns structured scores.

Scoring pipeline
----------------
1. Weight each candidate match by its source ``SectionType``.
2. Group weighted matches by **skill**.
3. For each skill, compute a normalised score and confidence level.
4. Derive ``taught_flag`` and ``assessed_flag`` from section-type
   evidence.
5. Roll up skill scores into **pillar** scores.

Design principles
-----------------
- A lesson may map to one, several, or zero pillars — absence of an
  unrelated pillar is *not* a failure.
- Scoring is *descriptive*, not punitive.
- Every number is deterministic: same input → same output.
"""

from __future__ import annotations

import enum
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from uuid import UUID

from app.models.enums import MatchMethod, PillarCode, SectionType

logger = logging.getLogger(__name__)


def _ev(x: object) -> str:
    """Return the ``.value`` of an enum, or the object itself if already a string."""
    return x.value if hasattr(x, "value") else x  # type: ignore[return-value]


# =====================================================================
# Configuration — section-type weights
# =====================================================================

#: How much a match in a given section type contributes to the score.
#: Higher weight = stronger evidence.
SECTION_TYPE_WEIGHTS: dict[SectionType, float] = {
    SectionType.OTHER: 0.5,       # generic / unknown section
    SectionType.CONTENT: 0.5,     # instructional content
    SectionType.OBJECTIVE: 1.0,   # learning objectives
    SectionType.ACTIVITY: 2.0,    # instruction / activities
    SectionType.ASSESSMENT: 3.0,  # assessment items
    SectionType.RUBRIC: 3.0,      # rubric criteria (same as assessment)
}

#: Maximum raw weighted score per skill used to normalise into [0, 1].
#: This caps the effect of many redundant matches on one skill.
MAX_WEIGHTED_SCORE_PER_SKILL: float = 10.0

#: Thresholds for confidence levels based on the normalised score.
CONFIDENCE_HIGH_THRESHOLD: float = 0.6
CONFIDENCE_MEDIUM_THRESHOLD: float = 0.3
CONFIDENCE_LOW_THRESHOLD: float = 0.1


# =====================================================================
# Enums specific to scoring output
# =====================================================================


class ConfidenceLevel(str, enum.Enum):
    """Confidence tier assigned to a skill or pillar score."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"


# =====================================================================
# Input value objects — the service boundary
# =====================================================================


@dataclass(frozen=True)
class CandidateMatchInput:
    """A single candidate match passed into the scoring service.

    This is the service's *input contract*.  It does not depend on ORM
    models or API schemas.

    ``skill_id`` is always set (the semantic unit).
    ``indicator_id`` is set only for keyword matches that resolved to a
    specific indicator; ``None`` for embedding-only matches.
    """

    candidate_id: UUID
    chunk_index: int
    section_type: SectionType
    skill_id: UUID
    skill_code: str
    skill_name: str
    pillar_id: UUID
    pillar_code: PillarCode
    pillar_name: str
    indicator_id: UUID | None
    raw_score: float
    match_method: MatchMethod
    matched_keywords: str | None = None


# =====================================================================
# Output value objects
# =====================================================================


@dataclass(frozen=True)
class SkillScoreResult:
    """Computed score for one skill within an analysis run.

    Attributes:
        skill_id / skill_code / skill_name:
            Identity of the scored skill.
        pillar_id / pillar_code:
            Parent pillar for easy grouping.
        score:
            Normalised score in [0, 1].
        confidence:
            Derived confidence tier.
        indicator_hits:
            Distinct indicators matched.
        weighted_sum:
            Raw weighted sum before normalisation.
        taught_flag:
            True if evidence comes from OBJECTIVE, ACTIVITY, or CONTENT.
        assessed_flag:
            True if evidence comes from ASSESSMENT or RUBRIC.
        explanation:
            Human-readable scoring rationale.
    """

    skill_id: UUID
    skill_code: str
    skill_name: str
    pillar_id: UUID
    pillar_code: PillarCode
    score: float
    confidence: ConfidenceLevel
    indicator_hits: int
    weighted_sum: float
    taught_flag: bool
    assessed_flag: bool
    explanation: str


@dataclass(frozen=True)
class PillarScoreResult:
    """Aggregate score for one pillar, rolled up from its skill scores."""

    pillar_id: UUID
    pillar_code: PillarCode
    pillar_name: str
    score: float
    confidence: ConfidenceLevel
    skill_count: int
    taught_flag: bool
    assessed_flag: bool
    explanation: str
    skill_scores: list[SkillScoreResult] = field(default_factory=list)


@dataclass(frozen=True)
class ScoringResult:
    """Top-level output of the scoring service."""

    pillar_scores: list[PillarScoreResult] = field(default_factory=list)
    overall_score: float | None = None
    match_method: MatchMethod = MatchMethod.KEYWORD


# =====================================================================
# Internal helpers
# =====================================================================


def _get_weight(section_type: SectionType) -> float:
    """Return the weight for a ``SectionType``, defaulting to 0.5."""
    return SECTION_TYPE_WEIGHTS.get(section_type, 0.5)


def _derive_confidence(score: float) -> ConfidenceLevel:
    """Map a normalised [0, 1] score to a confidence tier."""
    if score >= CONFIDENCE_HIGH_THRESHOLD:
        return ConfidenceLevel.HIGH
    if score >= CONFIDENCE_MEDIUM_THRESHOLD:
        return ConfidenceLevel.MEDIUM
    if score >= CONFIDENCE_LOW_THRESHOLD:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.INSUFFICIENT


_TAUGHT_SECTION_TYPES: frozenset[SectionType] = frozenset({
    SectionType.OBJECTIVE,
    SectionType.ACTIVITY,
    SectionType.CONTENT,
})

_ASSESSED_SECTION_TYPES: frozenset[SectionType] = frozenset({
    SectionType.ASSESSMENT,
    SectionType.RUBRIC,
})


def _compute_taught_flag(section_types: set[SectionType]) -> bool:
    """Return ``True`` if any match comes from a teaching-oriented section."""
    return bool(section_types & _TAUGHT_SECTION_TYPES)


def _compute_assessed_flag(section_types: set[SectionType]) -> bool:
    """Return ``True`` if any match comes from an assessment-oriented section."""
    return bool(section_types & _ASSESSED_SECTION_TYPES)


def _build_skill_explanation(
    skill_code: str,
    weighted_sum: float,
    score: float,
    indicator_hits: int,
    taught: bool,
    assessed: bool,
    section_types: set[SectionType],
) -> str:
    """Generate a human-readable explanation for a skill score."""
    parts = [
        f"Skill {skill_code}: normalised score {score:.2f} "
        f"(weighted sum {weighted_sum:.2f}, "
        f"{indicator_hits} indicator(s) matched).",
    ]
    section_labels = sorted(st.value for st in section_types)
    parts.append(f"Evidence from section types: {', '.join(section_labels)}.")
    if taught:
        parts.append("Taught: yes (found in objectives, activities, or content).")
    if assessed:
        parts.append("Assessed: yes (found in assessment or rubric).")
    if not taught and not assessed:
        parts.append("No direct teaching or assessment evidence; generic match only.")
    return " ".join(parts)


def _build_pillar_explanation(
    pillar_code: PillarCode,
    score: float,
    skill_count: int,
    taught: bool,
    assessed: bool,
) -> str:
    """Generate a human-readable explanation for a pillar score."""
    parts = [
        f"Pillar {_ev(pillar_code)}: aggregate score {score:.2f} "
        f"across {skill_count} skill(s).",
    ]
    if taught:
        parts.append("Teaching evidence present.")
    if assessed:
        parts.append("Assessment evidence present.")
    return " ".join(parts)


# =====================================================================
# Core scoring logic
# =====================================================================


def _score_skills(
    candidates: list[CandidateMatchInput],
) -> list[SkillScoreResult]:
    """Aggregate candidates into per-skill scores.

    For each skill:
    1. Sum ``raw_score × section_weight`` across all candidates.
    2. Normalise by ``MAX_WEIGHTED_SCORE_PER_SKILL`` and clamp to [0, 1].
    3. Derive confidence, taught_flag, assessed_flag.
    """
    # Group by skill_id
    skill_groups: dict[UUID, list[CandidateMatchInput]] = defaultdict(list)
    for c in candidates:
        skill_groups[c.skill_id].append(c)

    results: list[SkillScoreResult] = []
    for skill_id, matches in skill_groups.items():
        first = matches[0]  # for metadata

        weighted_sum = sum(
            m.raw_score * _get_weight(m.section_type) for m in matches
        )
        score = min(weighted_sum / MAX_WEIGHTED_SCORE_PER_SKILL, 1.0)
        confidence = _derive_confidence(score)

        indicator_ids = {m.indicator_id for m in matches if m.indicator_id is not None}
        section_types = {m.section_type for m in matches}
        taught = _compute_taught_flag(section_types)
        assessed = _compute_assessed_flag(section_types)

        explanation = _build_skill_explanation(
            skill_code=first.skill_code,
            weighted_sum=weighted_sum,
            score=score,
            indicator_hits=len(indicator_ids),
            taught=taught,
            assessed=assessed,
            section_types=section_types,
        )

        results.append(
            SkillScoreResult(
                skill_id=skill_id,
                skill_code=first.skill_code,
                skill_name=first.skill_name,
                pillar_id=first.pillar_id,
                pillar_code=first.pillar_code,
                score=round(score, 4),
                confidence=confidence,
                indicator_hits=len(indicator_ids),
                weighted_sum=round(weighted_sum, 4),
                taught_flag=taught,
                assessed_flag=assessed,
                explanation=explanation,
            )
        )

    # Sort for deterministic output
    results.sort(key=lambda r: (_ev(r.pillar_code), r.skill_code))
    return results


def _rollup_pillar_scores(
    skill_scores: list[SkillScoreResult],
) -> list[PillarScoreResult]:
    """Roll up skill scores into pillar-level aggregates.

    The pillar score is the **mean** of its child skill scores.  Flags
    are ``OR``-ed across skills (if any skill is taught → pillar is
    taught).
    """
    pillar_groups: dict[UUID, list[SkillScoreResult]] = defaultdict(list)
    for ss in skill_scores:
        pillar_groups[ss.pillar_id].append(ss)

    results: list[PillarScoreResult] = []
    for pillar_id, skills in pillar_groups.items():
        first = skills[0]

        avg_score = sum(s.score for s in skills) / len(skills)
        taught = any(s.taught_flag for s in skills)
        assessed = any(s.assessed_flag for s in skills)
        confidence = _derive_confidence(avg_score)

        explanation = _build_pillar_explanation(
            pillar_code=first.pillar_code,
            score=avg_score,
            skill_count=len(skills),
            taught=taught,
            assessed=assessed,
        )

        results.append(
            PillarScoreResult(
                pillar_id=pillar_id,
                pillar_code=first.pillar_code,
                pillar_name=_ev(first.pillar_code),  # use pillar_code as label
                score=round(avg_score, 4),
                confidence=confidence,
                skill_count=len(skills),
                taught_flag=taught,
                assessed_flag=assessed,
                explanation=explanation,
                skill_scores=skills,
            )
        )

    # Sort for deterministic output
    results.sort(key=lambda r: _ev(r.pillar_code))
    return results


# =====================================================================
# Public API
# =====================================================================


def score(
    candidates: list[CandidateMatchInput],
    match_method: MatchMethod = MatchMethod.KEYWORD,
) -> ScoringResult:
    """Score a list of candidate matches and return pillar + skill scores.

    Parameters
    ----------
    candidates:
        Pre-fetched candidate matches (from the matching service).
        If empty, returns a ``ScoringResult`` with no pillar scores and
        ``overall_score = 0.0``.
    match_method:
        The primary match method used (carried through to the result for
        logging / UI display).

    Returns
    -------
    ScoringResult
        Pillar-level and skill-level scores with explanations.
    """
    if not candidates:
        logger.debug("No candidate matches — returning empty scoring result.")
        return ScoringResult(
            pillar_scores=[],
            overall_score=0.0,
            match_method=match_method,
        )

    skill_scores = _score_skills(candidates)
    pillar_scores = _rollup_pillar_scores(skill_scores)

    # Overall score = mean of pillar scores (only over pillars that have
    # evidence — absence of a pillar is NOT penalised).
    overall = (
        sum(p.score for p in pillar_scores) / len(pillar_scores)
        if pillar_scores
        else 0.0
    )

    logger.debug(
        "Scoring complete: %d pillar(s), %d skill(s), overall=%.4f",
        len(pillar_scores),
        len(skill_scores),
        overall,
    )

    return ScoringResult(
        pillar_scores=pillar_scores,
        overall_score=round(overall, 4),
        match_method=match_method,
    )
