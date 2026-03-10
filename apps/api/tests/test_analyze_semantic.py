"""Integration tests for the semantic analysis pipeline.

These tests call ``analyze_service.run_analysis()`` directly (not via
HTTP) against a real PostgreSQL database.  They verify that:

1. The analysis completes and returns an ``analysis_run_id``.
2. Pillar scores are returned.
3. ``candidate_matches`` exist in the DB (keyword and/or semantic).
4. ``skill_embeddings`` are populated after the run.
5. ``chunk_embeddings`` are populated after the run.

Prerequisites
-------------
- PostgreSQL must be running (``docker compose up -d``).
- The ``vector`` extension must be enabled (``alembic upgrade head``).
- An active ontology version must be seeded in the DB.

Run with::

    cd apps/api
    pytest tests/test_analyze_semantic.py -v
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.analysis import AnalysisRun, CandidateMatch
from app.models.embeddings import ChunkEmbedding, SkillEmbedding
from app.models.enums import (
    CurriculumItemType,
    OntologyStatus,
    PillarCode,
)
from app.models.ontology import OntologyVersion, Pillar, Skill, SkillIndicator
from app.schemas.analysis import AnalyzeRequest
from app.services.analyze_service import run_analysis


# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture(scope="module")
def db() -> Session:
    """Provide a DB session for the entire test module.

    Uses a single session to keep seeded data visible across tests.
    Rolls back all changes at the end.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="module")
def seeded_ontology(db: Session) -> OntologyVersion:
    """Seed a minimal ontology with 2 pillars, 2 skills each, and indicators.

    This creates test data once per module. Uses unique IDs to avoid
    collisions with existing data.
    """
    # Check if an active ontology already exists
    existing = db.scalars(
        select(OntologyVersion).where(
            OntologyVersion.status == OntologyStatus.ACTIVE
        )
    ).first()
    if existing is not None:
        return existing

    ov = OntologyVersion(
        version_label=f"test-eval-{uuid.uuid4().hex[:8]}",
        status=OntologyStatus.ACTIVE,
        description="Seeded by integration test",
    )
    db.add(ov)
    db.flush()

    # Pillar P3 — Critical Thinking
    p3 = Pillar(
        ontology_version_id=ov.id,
        code=PillarCode.P3,
        name="Critical Thinking & Problem Solving",
    )
    db.add(p3)
    db.flush()

    s1 = Skill(
        pillar_id=p3.id,
        code="P3-S1",
        name="Analytical Reasoning",
        description="Ability to break down complex problems into parts and evaluate evidence.",
        sort_order=1,
    )
    db.add(s1)
    db.flush()

    db.add(SkillIndicator(
        skill_id=s1.id,
        indicator_text="Breaks down problems into component parts",
        keywords="analyze, break down, examine, evaluate, compare, contrast",
        weight=1.0,
    ))

    s2 = Skill(
        pillar_id=p3.id,
        code="P3-S2",
        name="Evidence-Based Reasoning",
        description="Using evidence to support claims and conclusions.",
        sort_order=2,
    )
    db.add(s2)
    db.flush()

    db.add(SkillIndicator(
        skill_id=s2.id,
        indicator_text="Supports claims with evidence",
        keywords="evidence, support, justify, reason, argue, claim, conclusion",
        weight=1.0,
    ))

    # Pillar P1 — Body and Health Intelligence
    p1 = Pillar(
        ontology_version_id=ov.id,
        code=PillarCode.P1,
        name="Body and Health Intelligence",
    )
    db.add(p1)
    db.flush()

    s3 = Skill(
        pillar_id=p1.id,
        code="P1-S1",
        name="Nutrition Foundations",
        description="Understand basic nutrients, balanced meals, and how food impacts energy, focus, and mood.",
        sort_order=1,
    )
    db.add(s3)
    db.flush()

    db.add(SkillIndicator(
        skill_id=s3.id,
        indicator_text="Understands nutrition and balanced meals",
        keywords="nutrition, food, healthy, balanced, nutrients, meal, diet, energy",
        weight=1.0,
    ))

    s4 = Skill(
        pillar_id=p1.id,
        code="P1-S2",
        name="Daily Movement Habits",
        description="Practice regular movement and stretching; understand its role in focus, mood, and health.",
        sort_order=2,
    )
    db.add(s4)
    db.flush()

    db.add(SkillIndicator(
        skill_id=s4.id,
        indicator_text="Practices regular movement and exercise",
        keywords="movement, exercise, physical, activity, stretching, motion, fitness, health",
        weight=1.0,
    ))

    db.commit()
    return ov


# =====================================================================
# Tests
# =====================================================================


SAMPLE_LESSON = (
    "In this lesson, students will analyze primary source documents to "
    "evaluate different perspectives on the American Revolution. They will "
    "break down arguments into claims and evidence, compare contrasting "
    "viewpoints, and write a persuasive essay defending their position. "
    "The lesson concludes with an oral debate where students present and "
    "defend their arguments using the evidence they gathered. "
    "Assessment: Students will be graded on their ability to justify "
    "claims with evidence, the clarity of their written essay, and the "
    "effectiveness of their oral presentation."
)


class TestAnalyzeSemantic:
    """Integration tests for semantic + keyword matching pipeline."""

    def test_analysis_returns_run_id(
        self, db: Session, seeded_ontology: OntologyVersion
    ) -> None:
        """Analysis completes and returns a valid analysis_run_id."""
        request = AnalyzeRequest(
            curriculum_text=SAMPLE_LESSON,
            title="Test Lesson: American Revolution Analysis",
            subject="Social Studies",
            grade_band="Grade 8",
            item_type=CurriculumItemType.LESSON,
            triggered_by="integration-test",
        )
        response = run_analysis(db=db, request=request)

        assert response.analysis_run_id is not None
        assert response.status.value == "completed"

    def test_pillar_scores_returned(
        self, db: Session, seeded_ontology: OntologyVersion
    ) -> None:
        """At least one pillar score is returned."""
        request = AnalyzeRequest(
            curriculum_text=SAMPLE_LESSON,
            title="Test Lesson: Pillar Scores",
            subject="Social Studies",
            grade_band="Grade 8",
            item_type=CurriculumItemType.LESSON,
            triggered_by="integration-test",
        )
        response = run_analysis(db=db, request=request)

        assert len(response.pillar_scores) > 0
        for ps in response.pillar_scores:
            assert 0.0 <= ps.score <= 1.0

    def test_candidate_matches_persisted(
        self, db: Session, seeded_ontology: OntologyVersion
    ) -> None:
        """Candidate matches are persisted in the DB after analysis."""
        request = AnalyzeRequest(
            curriculum_text=SAMPLE_LESSON,
            title="Test Lesson: Candidate Matches",
            subject="Social Studies",
            grade_band="Grade 8",
            item_type=CurriculumItemType.LESSON,
            triggered_by="integration-test",
        )
        response = run_analysis(db=db, request=request)

        match_count = db.scalar(
            select(func.count(CandidateMatch.id)).where(
                CandidateMatch.analysis_run_id == response.analysis_run_id
            )
        )
        assert match_count is not None
        assert match_count > 0

    def test_skill_embeddings_populated(
        self, db: Session, seeded_ontology: OntologyVersion
    ) -> None:
        """Skill embeddings are created after a run that uses semantic matching."""
        request = AnalyzeRequest(
            curriculum_text=SAMPLE_LESSON,
            title="Test Lesson: Skill Embeddings",
            subject="Social Studies",
            grade_band="Grade 8",
            item_type=CurriculumItemType.LESSON,
            triggered_by="integration-test",
        )
        _response = run_analysis(db=db, request=request)

        count = db.scalar(select(func.count(SkillEmbedding.id)))
        assert count is not None
        assert count > 0

    def test_chunk_embeddings_populated(
        self, db: Session, seeded_ontology: OntologyVersion
    ) -> None:
        """Chunk embeddings are created after a run that uses semantic matching."""
        request = AnalyzeRequest(
            curriculum_text=SAMPLE_LESSON,
            title="Test Lesson: Chunk Embeddings",
            subject="Social Studies",
            grade_band="Grade 8",
            item_type=CurriculumItemType.LESSON,
            triggered_by="integration-test",
        )
        _response = run_analysis(db=db, request=request)

        count = db.scalar(select(func.count(ChunkEmbedding.id)))
        assert count is not None
        assert count > 0
