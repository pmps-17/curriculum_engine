"""Analysis orchestration service — end-to-end flow for one request.

This is the **thick service** the router calls.  It coordinates every
step of the analysis pipeline:

1. Resolve ontology version
2. Persist document + curriculum item
3. Normalize input
4. Run intake compliance
5. Create sections & chunks
6. Run candidate matching (keyword fallback for v1)
7. Run deterministic scoring
8. Build evidence
9. Persist analysis run, scores, evidence, findings, compliance results
10. Return a structured ``AnalyzeResponse``

All DB work happens inside one transaction.  If any step fails the
transaction rolls back and the run is marked ``FAILED``.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.models.analysis import (
    AnalysisFinding,
    AnalysisRun,
    EvidenceSnippet as EvidenceSnippetModel,
    PillarScore as PillarScoreModel,
    SkillScore as SkillScoreModel,
)
from app.models.compliance import IntakeComplianceResult
from app.models.curriculum import (
    Chunk as ChunkModel,
    CurriculumItem,
)
from app.models.enums import (
    FindingCategory,
    FindingSeverity,
    MatchMethod,
)
from app.models.ontology import OntologyVersion
from app.repositories.analysis_run_repo import AnalysisRunRepo
from app.repositories.candidate_repo import CandidateRepo
from app.repositories.curriculum_repo import CurriculumRepo
from app.repositories.scoring_repo import ScoringRepo
from app.schemas.analysis import (
    AnalyzeRequest,
    AnalyzeResponse,
    EvidenceSnippetOut,
    FindingOut,
    IntakeComplianceResultOut,
    PillarScoreOut,
    SkillScoreOut,
)
from app.services.chunking_service import chunk_sections
from app.services.candidate_matching_service import run_keyword_matching
from app.services.evidence_service import EvidenceResult, build_evidence
from app.services.intake_compliance_service import (
    CheckResult,
    IntakeVerdict,
    run_intake_checks,
)
from app.services.normalization_service import NormalizedItem, normalize
from app.services.scoring_service import (
    CandidateMatchInput,
    ScoringResult,
    score,
)
from app.services.semantic_candidate_matching_service import run_semantic_matching
from app.core.config import get_settings
from app.core.dependencies import get_embedding_provider, get_vector_store

logger = logging.getLogger(__name__)


# =====================================================================
# Exceptions
# =====================================================================


class AnalysisError(Exception):
    """Base exception for analysis-service failures."""


class OntologyNotFoundError(AnalysisError):
    """Raised when no active ontology version is available."""


class IntakeRejectedError(AnalysisError):
    """Raised when intake compliance hard-rejects the submission."""

    def __init__(self, message: str, compliance_results: list[dict]) -> None:
        super().__init__(message)
        self.compliance_results = compliance_results


# =====================================================================
# Internal helpers
# =====================================================================


# ── Ontology resolution (thin query, kept here for exception mapping) ─

def _resolve_ontology_version(
    run_repo: AnalysisRunRepo,
    requested_id: uuid.UUID | None,
) -> OntologyVersion:
    """Return the requested ontology version or the currently active one."""
    version = run_repo.resolve_ontology_version(requested_id)
    if version is None:
        msg = (
            f"Ontology version {requested_id} not found."
            if requested_id
            else "No active ontology version found."
        )
        raise OntologyNotFoundError(msg)
    return version


# =====================================================================
# Candidate merging
# =====================================================================


#: Minimum number of semantic candidates required to skip the keyword
#: fallback.  If semantic returns fewer, keyword results are merged in.
_SEMANTIC_MIN_CANDIDATES: int = 3


def _merge_candidates(
    semantic: list[CandidateMatchInput],
    keyword: list[CandidateMatchInput],
) -> list[CandidateMatchInput]:
    """Merge semantic and keyword candidates, deduplicating by (chunk_index, skill_id).

    When both sources match the same (chunk, skill) pair, the candidate
    with the higher ``raw_score`` wins.  On a tie, the semantic match is
    preferred (richer signal).
    """
    best: dict[tuple[int, uuid.UUID], CandidateMatchInput] = {}

    # Semantic first so ties favour semantic
    for c in semantic:
        key = (c.chunk_index, c.skill_id)
        best[key] = c

    for c in keyword:
        key = (c.chunk_index, c.skill_id)
        existing = best.get(key)
        if existing is None or c.raw_score > existing.raw_score:
            best[key] = c

    return list(best.values())


# =====================================================================
# Response builders
# =====================================================================


def _build_response(
    run: AnalysisRun,
    ci: CurriculumItem,
    ontology_version: OntologyVersion,
    compliance_models: list[IntakeComplianceResult],
    pillar_models: list[PillarScoreModel],
    skill_models: list[SkillScoreModel],
    evidence_models: list[EvidenceSnippetModel],
    finding_models: list[AnalysisFinding],
    scoring_result: ScoringResult,
) -> AnalyzeResponse:
    """Map persisted entities back into the API response schema."""

    # Group skill scores by pillar for nesting
    skill_by_run: dict[uuid.UUID, list[SkillScoreOut]] = {}
    for sm in skill_models:
        out = SkillScoreOut(
            id=sm.id,
            skill_id=sm.skill_id,
            score=sm.score,
            confidence=sm.confidence,
            indicator_hits=sm.indicator_hits,
            explanation=sm.explanation,
        )
        # We need to map skill → pillar; use scoring_result for this
        for ps in scoring_result.pillar_scores:
            for ss in ps.skill_scores:
                if ss.skill_id == sm.skill_id:
                    out = SkillScoreOut(
                        id=sm.id,
                        skill_id=sm.skill_id,
                        skill_code=ss.skill_code,
                        skill_name=ss.skill_name,
                        score=sm.score,
                        confidence=sm.confidence,
                        indicator_hits=sm.indicator_hits,
                        explanation=sm.explanation,
                    )
                    skill_by_run.setdefault(ps.pillar_id, []).append(out)
                    break

    pillar_outs: list[PillarScoreOut] = []
    # Build a lookup for pillar descriptions from the ontology
    pillar_desc_map: dict[uuid.UUID, str | None] = {
        p.id: p.description for p in ontology_version.pillars
    }
    for pm in pillar_models:
        # Find the scoring result for pillar metadata
        pillar_code = None
        pillar_name = None
        for ps in scoring_result.pillar_scores:
            if ps.pillar_id == pm.pillar_id:
                pillar_code = ps.pillar_code
                pillar_name = ps.pillar_name
                break

        pillar_outs.append(
            PillarScoreOut(
                id=pm.id,
                pillar_id=pm.pillar_id,
                pillar_code=pillar_code,
                pillar_name=pillar_name,
                pillar_description=pillar_desc_map.get(pm.pillar_id),
                score=pm.score,
                skill_count=pm.skill_count,
                explanation=pm.explanation,
                skill_scores=skill_by_run.get(pm.pillar_id, []),
            )
        )

    evidence_outs = [
        EvidenceSnippetOut(
            id=em.id,
            chunk_id=em.chunk_id,
            skill_id=em.skill_id,
            snippet_text=em.snippet_text,
            relevance_score=em.relevance_score,
        )
        for em in evidence_models
    ]

    finding_outs = [
        FindingOut(
            id=fm.id,
            severity=fm.severity,
            category=fm.category,
            title=fm.title,
            detail=fm.detail,
            pillar_id=fm.pillar_id,
            skill_id=fm.skill_id,
        )
        for fm in finding_models
    ]

    compliance_outs = [
        IntakeComplianceResultOut(
            id=cm.id,
            check_type=cm.check_type,
            status=cm.status,
            message=cm.message,
            detail=cm.detail,
        )
        for cm in compliance_models
    ]

    return AnalyzeResponse(
        analysis_run_id=run.id,
        curriculum_item_id=ci.id,
        ontology_version_id=ontology_version.id,
        status=run.status,
        triggered_by=run.triggered_by,
        created_at=run.created_at,
        intake_compliance=compliance_outs,
        pillar_scores=pillar_outs,
        evidence_snippets=evidence_outs,
        findings=finding_outs,
        overall_score=scoring_result.overall_score,
        match_method=scoring_result.match_method,
        error_message=run.error_message,
    )


# =====================================================================
# Public API
# =====================================================================


def run_analysis(
    *,
    db: Session,
    request: AnalyzeRequest,
) -> AnalyzeResponse:
    """Execute the full analysis pipeline for a single request.

    Parameters
    ----------
    db:
        Active SQLAlchemy session (from ``Depends(get_db)``).
    request:
        Validated ``AnalyzeRequest`` from the router.
        Must provide either ``curriculum_text`` or ``document_id``.

    Returns
    -------
    AnalyzeResponse
        Complete analysis result ready for the API response.

    Raises
    ------
    OntologyNotFoundError
        If no suitable ontology version exists.
    IntakeRejectedError
        If the submission is hard-rejected by intake compliance.
    AnalysisError
        For any other analysis-pipeline failures.
    """
    run: AnalysisRun | None = None

    # ── Instantiate repositories ─────────────────────────────────────
    run_repo = AnalysisRunRepo(db)
    curriculum_repo = CurriculumRepo(db)
    candidate_repo = CandidateRepo(db)
    scoring_repo = ScoringRepo(db)

    try:
        # ── Step 1: Resolve ontology ─────────────────────────────────
        ontology_version = _resolve_ontology_version(
            run_repo, request.ontology_version_id
        )

        # ── Step 2: Resolve curriculum text ──────────────────────────
        # If document_id provided, load its extracted_text
        curriculum_text = request.curriculum_text
        doc = None

        if request.document_id:
            # Load document from database
            import uuid as uuid_mod

            try:
                doc_uuid = uuid_mod.UUID(request.document_id)
                doc = curriculum_repo.get_document(doc_uuid)
            except (ValueError, AttributeError):
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid document_id format: {request.document_id}",
                )

            if not doc:
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=404,
                    detail=f"Document not found: {request.document_id}",
                )

            # Extract text from document
            if not doc.raw_text:
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=400,
                    detail=f"Document {request.document_id} has no extracted text. "
                    "Upload a supported file type (PDF, DOCX, TXT, etc.) or provide curriculum_text directly.",
                )

            curriculum_text = doc.raw_text
        else:
            # ── Step 2a: Persist document for curriculum_text submission
            _batch, doc = curriculum_repo.create_upload_batch_and_document(
                school_id=request.school_id,
                uploaded_by=request.triggered_by,
                curriculum_text=curriculum_text,
            )

        # ── Step 3: Normalize ────────────────────────────────────────
        normalized: NormalizedItem = normalize(
            title=request.title,
            item_type=request.item_type,
            subject=request.subject,
            grade_band=request.grade_band,
            unit_name=request.unit_name,
            lesson_text=curriculum_text,
            rubric_text=request.rubric_text,
        )

        # ── Step 4: Persist curriculum item ──────────────────────────
        ci = curriculum_repo.create_curriculum_item(
            document_id=doc.id,
            subject_id=request.subject_id,
            title=normalized.title or "Untitled",
            item_type=normalized.item_type,
            description=normalized.subject,
            unit_name=normalized.unit_name,
        )

        # ── Step 5: Create analysis run ──────────────────────────────
        run = run_repo.create_analysis_run(
            curriculum_item_id=ci.id,
            ontology_version_id=ontology_version.id,
            triggered_by=request.triggered_by,
        )

        # ── Step 6: Intake compliance ────────────────────────────────
        compliance_report = run_intake_checks(
            lesson_text=curriculum_text,
            item=normalized,
            rubric_text=request.rubric_text,
        )
        compliance_models = scoring_repo.bulk_insert_compliance_results(
            document_id=doc.id,
            check_results=compliance_report.results,
        )

        if compliance_report.verdict == IntakeVerdict.REJECTED:
            run_repo.mark_failed(run, "Submission rejected by intake compliance.")
            raise IntakeRejectedError(
                "Submission rejected by intake compliance.",
                compliance_results=[
                    {"check": r.check_type.value, "status": r.status.value, "message": r.message}
                    for r in compliance_report.results
                ],
            )

        # ── Step 7: Persist sections & chunks ────────────────────────
        service_chunks = chunk_sections(normalized.sections)
        section_models, chunk_models = curriculum_repo.create_sections_and_chunks(
            document_id=doc.id,
            curriculum_item_id=ci.id,
            normalized_sections=normalized.sections,
            service_chunks=service_chunks,
        )

        # ── Step 8: Candidate matching (semantic + keyword fallback) ──
        settings = get_settings()
        used_fallback = False

        # 8a: Try semantic matching first
        try:
            embedding_provider = get_embedding_provider()
            vector_store = get_vector_store(db)

            semantic_result = run_semantic_matching(
                db=db,
                ontology_version=ontology_version,
                chunk_models=chunk_models,
                section_models=section_models,
                embedding_provider=embedding_provider,
                vector_store=vector_store,
                top_k=settings.MATCH_TOP_K,
                min_similarity=settings.SEMANTIC_MIN_SIMILARITY,
            )
            semantic_candidates = semantic_result.candidates
        except Exception:
            logger.warning(
                "Semantic matching failed — falling back to keyword only.",
                exc_info=True,
            )
            semantic_candidates = []

        # 8b: Always run keyword matching (for merge / fallback)
        keyword_candidates = run_keyword_matching(
            ontology_version=ontology_version,
            chunk_models=chunk_models,
            section_models=section_models,
        )

        # 8c: Decide final candidates
        if len(semantic_candidates) >= _SEMANTIC_MIN_CANDIDATES:
            candidates = _merge_candidates(semantic_candidates, keyword_candidates)
            match_method_used = MatchMethod.HYBRID
        else:
            if semantic_candidates:
                candidates = _merge_candidates(semantic_candidates, keyword_candidates)
                match_method_used = MatchMethod.HYBRID
                used_fallback = True
            else:
                candidates = keyword_candidates
                match_method_used = MatchMethod.KEYWORD
                used_fallback = True

        candidate_repo.bulk_insert_candidate_matches(
            analysis_run_id=run.id,
            candidates=candidates,
            chunk_models=chunk_models,
        )

        # ── Step 9: Scoring ──────────────────────────────────────────
        scoring_result = score(candidates, match_method=match_method_used)

        # ── Step 10: Evidence ────────────────────────────────────────
        chunk_texts = {cm.chunk_index: cm.chunk_text for cm in chunk_models}
        evidence_result = build_evidence(
            candidates=candidates,
            chunk_texts=chunk_texts,
            scoring_result=scoring_result,
        )

        # ── Step 11: Persist scores, evidence, findings ──────────────
        pillar_models, skill_models = scoring_repo.bulk_insert_scores(
            analysis_run_id=run.id,
            scoring_result=scoring_result,
        )
        evidence_models = scoring_repo.bulk_insert_evidence(
            analysis_run_id=run.id,
            evidence_result=evidence_result,
            chunk_models=chunk_models,
        )
        finding_models = scoring_repo.bulk_insert_findings(
            analysis_run_id=run.id,
            scoring_result=scoring_result,
            compliance_verdict=compliance_report.verdict,
        )

        # Add informational finding if semantic matching fell back
        if used_fallback:
            fallback_finding = scoring_repo.insert_single_finding(
                analysis_run_id=run.id,
                severity=FindingSeverity.INFO,
                category=FindingCategory.STRUCTURAL,
                title="Semantic matching fallback",
                detail="Semantic matching returned insufficient candidates. "
                       "Keyword matching was used as fallback or supplement. "
                       "Consider checking skill embeddings and ontology coverage.",
            )
            finding_models.append(fallback_finding)

        # ── Step 12: Mark run complete ───────────────────────────────
        run_repo.mark_completed(run)
        db.commit()

        logger.info(
            "Analysis run %s completed: %d pillar(s), %d finding(s).",
            run.id,
            len(pillar_models),
            len(finding_models),
        )

        # ── Step 13: Build response ──────────────────────────────────
        return _build_response(
            run=run,
            ci=ci,
            ontology_version=ontology_version,
            compliance_models=compliance_models,
            pillar_models=pillar_models,
            skill_models=skill_models,
            evidence_models=evidence_models,
            finding_models=finding_models,
            scoring_result=scoring_result,
        )

    except (OntologyNotFoundError, IntakeRejectedError):
        # These are expected business errors — re-raise after rollback
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()
        logger.exception("Analysis pipeline failed.")

        # If we managed to create the run, mark it failed
        if run and run.id:
            try:
                run_repo.mark_failed(run, str(exc))
                db.commit()
            except Exception:
                logger.exception("Failed to update run status after error.")

        raise AnalysisError(f"Analysis pipeline failed: {exc}") from exc
