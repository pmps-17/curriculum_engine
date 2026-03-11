"""Regression test: ``'str' object has no attribute 'value'`` on pillar_code.

Root cause (fixed):
- ``candidate_matching_service`` passed ``ctx.pillar.code`` (a raw
  string from SQLAlchemy) into ``CandidateMatchInput.pillar_code``
  without wrapping it in ``PillarCode(...)``.
- ``scoring_service._score_skills()`` then called ``.value`` on the
  sort key, which crashed for plain strings.

This test creates ``CandidateMatchInput`` instances with **string**
pillar codes (simulating the DB-returned value) and verifies that
scoring, evidence building, and sorting all succeed.
"""

from __future__ import annotations

import uuid

import pytest

from app.models.enums import MatchMethod, PillarCode, SectionType
from app.services.evidence_service import build_evidence
from app.services.scoring_service import CandidateMatchInput, score


# ── Helpers ──────────────────────────────────────────────────────────

def _make_candidate(
    *,
    pillar_code: PillarCode | str = "P3",
    skill_code: str = "P3.S1",
    skill_name: str = "Test Skill",
    indicator_id: uuid.UUID | None = None,
    raw_score: float = 0.5,
    match_method: MatchMethod = MatchMethod.KEYWORD,
    section_type: SectionType = SectionType.OTHER,
    matched_keywords: str | None = "test",
) -> CandidateMatchInput:
    """Build a ``CandidateMatchInput`` with sensible defaults."""
    return CandidateMatchInput(
        candidate_id=uuid.uuid4(),
        chunk_index=0,
        section_type=section_type,
        skill_id=uuid.uuid4(),
        skill_code=skill_code,
        skill_name=skill_name,
        pillar_id=uuid.uuid4(),
        pillar_code=pillar_code,
        pillar_name=str(pillar_code),
        indicator_id=indicator_id,
        raw_score=raw_score,
        match_method=match_method,
        matched_keywords=matched_keywords,
    )


# ── Tests ────────────────────────────────────────────────────────────


class TestPillarCodeEnumSafety:
    """Verify scoring/evidence never crash when pillar_code is a string."""

    def test_score_with_string_pillar_code(self) -> None:
        """Scoring must not crash when pillar_code is a plain string."""
        candidates = [
            _make_candidate(pillar_code="P1", skill_code="P1.S1"),
            _make_candidate(pillar_code="P3", skill_code="P3.S1"),
        ]
        result = score(candidates, match_method=MatchMethod.KEYWORD)

        assert result.overall_score is not None
        assert result.overall_score > 0
        assert len(result.pillar_scores) == 2

    def test_score_with_enum_pillar_code(self) -> None:
        """Scoring must also work with proper PillarCode enums."""
        candidates = [
            _make_candidate(pillar_code=PillarCode.P1, skill_code="P1.S1"),
            _make_candidate(pillar_code=PillarCode.P3, skill_code="P3.S1"),
        ]
        result = score(candidates, match_method=MatchMethod.KEYWORD)

        assert result.overall_score is not None
        assert len(result.pillar_scores) == 2

    def test_score_with_mixed_pillar_code_types(self) -> None:
        """Scoring must handle a mix of string and enum pillar codes."""
        candidates = [
            _make_candidate(pillar_code="P1", skill_code="P1.S1"),
            _make_candidate(pillar_code=PillarCode.P3, skill_code="P3.S1"),
        ]
        result = score(candidates, match_method=MatchMethod.KEYWORD)

        assert len(result.pillar_scores) == 2
        # Verify pillar names are always clean strings, never "PillarCode.P1"
        for ps in result.pillar_scores:
            assert "PillarCode" not in ps.pillar_name

    def test_evidence_with_string_pillar_code(self) -> None:
        """Evidence building must not crash when pillar_code is a string."""
        candidates = [
            _make_candidate(pillar_code="P3", skill_code="P3.S1"),
            _make_candidate(pillar_code="P3", skill_code="P3.S2"),
        ]
        scoring_result = score(candidates, match_method=MatchMethod.KEYWORD)
        chunk_texts = {0: "Students learn to analyze problems and evaluate evidence."}

        result = build_evidence(
            candidates=candidates,
            scoring_result=scoring_result,
            chunk_texts=chunk_texts,
        )

        assert len(result.snippets) > 0

    def test_score_with_nullable_indicator_id(self) -> None:
        """Scoring must work when indicator_id is None (semantic matches)."""
        candidates = [
            _make_candidate(
                pillar_code=PillarCode.P3,
                indicator_id=None,
                match_method=MatchMethod.EMBEDDING,
                matched_keywords=None,
            ),
            _make_candidate(
                pillar_code=PillarCode.P3,
                skill_code="P3.S2",
                indicator_id=uuid.uuid4(),
                match_method=MatchMethod.KEYWORD,
            ),
        ]
        result = score(candidates, match_method=MatchMethod.HYBRID)

        assert result.overall_score is not None
        # The skill with indicator_id=None should report 0 indicator_hits
        for ps in result.pillar_scores:
            for ss in ps.skill_scores:
                if ss.skill_code == "P3.S1":
                    assert ss.indicator_hits == 0
                elif ss.skill_code == "P3.S2":
                    assert ss.indicator_hits == 1

    def test_pillar_score_sorting_deterministic(self) -> None:
        """Pillar scores must be sorted by pillar code regardless of type."""
        candidates = [
            _make_candidate(pillar_code="P3", skill_code="P3.S1"),
            _make_candidate(pillar_code="P1", skill_code="P1.S1"),
            _make_candidate(pillar_code="P2", skill_code="P2.S1"),
        ]
        result = score(candidates, match_method=MatchMethod.KEYWORD)

        codes = [ps.pillar_code for ps in result.pillar_scores]
        assert codes == sorted(codes, key=lambda c: c.value if hasattr(c, "value") else c)
