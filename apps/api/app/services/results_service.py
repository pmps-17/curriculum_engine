"""Results service — assembles a stored analysis run into a ``ResultResponse``.

Reads all related entities for one analysis run and maps them into the
API response schema.  This is a **read-only** service with no side
effects.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.analysis import AnalysisRun
from app.models.enums import MatchMethod
from app.models.ontology import Pillar, Skill
from app.repositories.results_repo import ResultsRepo
from app.schemas.analysis import (
    EvidenceSnippetOut,
    FindingOut,
    IntakeComplianceResultOut,
    PillarScoreOut,
    SkillScoreOut,
)
from app.schemas.results import ResultResponse, ReviewSummaryOut

logger = logging.getLogger(__name__)


# =====================================================================
# Exceptions
# =====================================================================


class RunNotFoundError(Exception):
    """Raised when the requested analysis run does not exist."""


# =====================================================================
# Public API
# =====================================================================


def get_result(*, db: Session, analysis_run_id: UUID) -> ResultResponse:
    """Load a completed analysis run and return a ``ResultResponse``.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    analysis_run_id:
        Primary key of the analysis run.

    Raises
    ------
    RunNotFoundError
        If no run with the given ID exists.
    """
    repo = ResultsRepo(db)
    run = repo.get_analysis_run(analysis_run_id)
    if run is None:
        raise RunNotFoundError(f"Analysis run {analysis_run_id} not found.")

    # ── Load related entities ────────────────────────────────────────
    ci = repo.get_curriculum_item(run.curriculum_item_id)
    ontology = repo.get_ontology_version(run.ontology_version_id)

    # Build skill lookup for denormalisation
    skill_map: dict[UUID, Skill] = {}
    pillar_map: dict[UUID, Pillar] = {}
    if ontology:
        for pillar in ontology.pillars:
            pillar_map[pillar.id] = pillar
            for skill in pillar.skills:
                skill_map[skill.id] = skill

    # Compliance results (linked to the document, not the run)
    compliance_models = []
    if ci:
        compliance_models = repo.get_compliance_results_for_document(ci.document_id)

    # Reviews linked to this run
    reviews = repo.get_reviews_for_run(run.id)

    # ── Build nested skill scores grouped by pillar ──────────────────
    skill_scores_by_pillar: dict[UUID, list[SkillScoreOut]] = {}
    for ss in run.skill_scores:
        skill = skill_map.get(ss.skill_id)
        pillar_id: UUID | None = None
        if skill:
            pillar_id = skill.pillar_id

        out = SkillScoreOut(
            id=ss.id,
            skill_id=ss.skill_id,
            skill_code=skill.code if skill else None,
            skill_name=skill.name if skill else None,
            score=ss.score,
            confidence=ss.confidence,
            indicator_hits=ss.indicator_hits,
            explanation=ss.explanation,
        )
        if pillar_id:
            skill_scores_by_pillar.setdefault(pillar_id, []).append(out)

    # ── Build pillar scores ──────────────────────────────────────────
    pillar_outs: list[PillarScoreOut] = []
    for pm in run.pillar_scores:
        pillar = pillar_map.get(pm.pillar_id)
        pillar_outs.append(
            PillarScoreOut(
                id=pm.id,
                pillar_id=pm.pillar_id,
                pillar_code=pillar.code if pillar else None,
                pillar_name=pillar.name if pillar else None,
                score=pm.score,
                skill_count=pm.skill_count,
                explanation=pm.explanation,
                skill_scores=skill_scores_by_pillar.get(pm.pillar_id, []),
            )
        )

    # Overall score = mean of pillar scores
    overall_score: float | None = None
    if pillar_outs:
        overall_score = round(
            sum(p.score for p in pillar_outs) / len(pillar_outs), 4
        )

    # ── Map remaining entities ───────────────────────────────────────
    evidence_outs = [
        EvidenceSnippetOut(
            id=es.id,
            chunk_id=es.chunk_id,
            skill_id=es.skill_id,
            snippet_text=es.snippet_text,
            relevance_score=es.relevance_score,
        )
        for es in run.evidence_snippets
    ]

    finding_outs = [
        FindingOut(
            id=f.id,
            severity=f.severity,
            category=f.category,
            title=f.title,
            detail=f.detail,
            pillar_id=f.pillar_id,
            skill_id=f.skill_id,
        )
        for f in run.findings
    ]

    compliance_outs = [
        IntakeComplianceResultOut(
            id=cr.id,
            check_type=cr.check_type,
            status=cr.status,
            message=cr.message,
            detail=cr.detail,
        )
        for cr in compliance_models
    ]

    review_outs = [
        ReviewSummaryOut(
            id=r.id,
            reviewer=r.reviewer,
            status=r.status,
            comments=r.comments,
            created_at=r.created_at,
        )
        for r in reviews
    ]

    # ── Curriculum-item context ──────────────────────────────────────
    subject_name: str | None = None
    if ci and ci.subject_id:
        subj = ci.subject
        if subj:
            subject_name = subj.name

    return ResultResponse(
        analysis_run_id=run.id,
        status=run.status,
        triggered_by=run.triggered_by,
        created_at=run.created_at,
        updated_at=run.updated_at,
        curriculum_item_id=run.curriculum_item_id,
        title=ci.title if ci else None,
        item_type=ci.item_type.value if ci else None,
        subject_name=subject_name,
        unit_name=ci.unit_name if ci else None,
        grade_level=None,  # TODO: derive from package/subject metadata
        ontology_version_id=run.ontology_version_id,
        ontology_version_label=ontology.version_label if ontology else None,
        pillar_scores=pillar_outs,
        overall_score=overall_score,
        match_method=run.candidate_matches[0].match_method
        if run.candidate_matches
        else MatchMethod.KEYWORD,
        evidence_snippets=evidence_outs,
        findings=finding_outs,
        intake_compliance=compliance_outs,
        reviews=review_outs,
        error_message=run.error_message,
    )
