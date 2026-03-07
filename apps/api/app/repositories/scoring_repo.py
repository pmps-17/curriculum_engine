"""Repository for scoring / evidence / findings / compliance persistence.

Handles bulk insertion of all analysis output entities.  Each method
builds ORM instances, adds them, and flushes — never commits.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.analysis import (
    AnalysisFinding,
    EvidenceSnippet as EvidenceSnippetModel,
    PillarScore as PillarScoreModel,
    SkillScore as SkillScoreModel,
)
from app.models.compliance import IntakeComplianceResult
from app.models.curriculum import Chunk as ChunkModel
from app.models.enums import (
    FindingCategory,
    FindingSeverity,
)
from app.services.evidence_service import EvidenceResult
from app.services.intake_compliance_service import CheckResult, IntakeVerdict
from app.services.scoring_service import ScoringResult


class ScoringRepo:
    """Thin data-access layer for scores, evidence, findings, and compliance."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Scores ───────────────────────────────────────────────────────

    def bulk_insert_scores(
        self,
        *,
        analysis_run_id: uuid.UUID,
        scoring_result: ScoringResult,
    ) -> tuple[list[PillarScoreModel], list[SkillScoreModel]]:
        """Persist pillar and skill scores from a ``ScoringResult``."""
        pillar_models: list[PillarScoreModel] = []
        skill_models: list[SkillScoreModel] = []

        for ps in scoring_result.pillar_scores:
            pm = PillarScoreModel(
                analysis_run_id=analysis_run_id,
                pillar_id=ps.pillar_id,
                score=ps.score,
                skill_count=ps.skill_count,
                explanation=ps.explanation,
            )
            self._db.add(pm)
            pillar_models.append(pm)

            for ss in ps.skill_scores:
                sm = SkillScoreModel(
                    analysis_run_id=analysis_run_id,
                    skill_id=ss.skill_id,
                    score=ss.score,
                    confidence=ss.score,
                    indicator_hits=ss.indicator_hits,
                    explanation=ss.explanation,
                )
                self._db.add(sm)
                skill_models.append(sm)

        self._db.flush()
        return pillar_models, skill_models

    # ── Evidence ─────────────────────────────────────────────────────

    def bulk_insert_evidence(
        self,
        *,
        analysis_run_id: uuid.UUID,
        evidence_result: EvidenceResult,
        chunk_models: list[ChunkModel],
    ) -> list[EvidenceSnippetModel]:
        """Persist evidence snippets from an ``EvidenceResult``."""
        index_to_id = {cm.chunk_index: cm.id for cm in chunk_models}
        models: list[EvidenceSnippetModel] = []

        for es in evidence_result.snippets:
            chunk_id = index_to_id.get(es.chunk_index)
            if chunk_id is None:
                continue
            m = EvidenceSnippetModel(
                analysis_run_id=analysis_run_id,
                chunk_id=chunk_id,
                skill_id=es.skill_id,
                snippet_text=es.snippet_text,
                relevance_score=es.relevance_score,
            )
            self._db.add(m)
            models.append(m)

        self._db.flush()
        return models

    # ── Findings ─────────────────────────────────────────────────────

    def bulk_insert_findings(
        self,
        *,
        analysis_run_id: uuid.UUID,
        scoring_result: ScoringResult,
        compliance_verdict: IntakeVerdict,
    ) -> list[AnalysisFinding]:
        """Generate and persist analysis findings based on scoring results."""
        findings: list[AnalysisFinding] = []

        if compliance_verdict == IntakeVerdict.PASS_WITH_WARNINGS:
            findings.append(AnalysisFinding(
                analysis_run_id=analysis_run_id,
                severity=FindingSeverity.WARNING,
                category=FindingCategory.COMPLIANCE,
                title="Intake compliance passed with warnings",
                detail="Some intake checks produced warnings. Review the "
                       "compliance results for details.",
            ))

        if not scoring_result.pillar_scores:
            findings.append(AnalysisFinding(
                analysis_run_id=analysis_run_id,
                severity=FindingSeverity.WARNING,
                category=FindingCategory.MISSING_COVERAGE,
                title="No pillar coverage detected",
                detail="The analysis did not find evidence for any pillar. "
                       "This may indicate that the ontology keywords do not "
                       "match the curriculum vocabulary.",
            ))

        for ps in scoring_result.pillar_scores:
            if ps.score < 0.1:
                findings.append(AnalysisFinding(
                    analysis_run_id=analysis_run_id,
                    severity=FindingSeverity.INFO,
                    category=FindingCategory.LOW_CONFIDENCE,
                    title=f"Low confidence for pillar {ps.pillar_code.value}",
                    detail=f"Pillar {ps.pillar_code.value} scored {ps.score:.2f} "
                           f"with {ps.skill_count} skill(s) evaluated.",
                    pillar_id=ps.pillar_id,
                ))

        self._db.add_all(findings)
        self._db.flush()
        return findings

    def insert_single_finding(
        self,
        *,
        analysis_run_id: uuid.UUID,
        severity: FindingSeverity,
        category: FindingCategory,
        title: str,
        detail: str,
    ) -> AnalysisFinding:
        """Insert a single ad-hoc finding (e.g. fallback notice)."""
        f = AnalysisFinding(
            analysis_run_id=analysis_run_id,
            severity=severity,
            category=category,
            title=title,
            detail=detail,
        )
        self._db.add(f)
        self._db.flush()
        return f

    # ── Compliance ───────────────────────────────────────────────────

    def bulk_insert_compliance_results(
        self,
        *,
        document_id: uuid.UUID,
        check_results: list[CheckResult],
    ) -> list[IntakeComplianceResult]:
        """Persist intake compliance check results."""
        models: list[IntakeComplianceResult] = []
        for cr in check_results:
            m = IntakeComplianceResult(
                document_id=document_id,
                check_type=cr.check_type,
                status=cr.status,
                message=cr.message,
                detail=cr.detail,
            )
            self._db.add(m)
            models.append(m)
        self._db.flush()
        return models
