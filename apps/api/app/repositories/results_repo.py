"""Repository for read-only results assembly queries.

All DB reads needed by the results endpoint live here.
This repo never writes — it only fetches and returns ORM instances.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisRun
from app.models.compliance import IntakeComplianceResult
from app.models.curriculum import CurriculumItem
from app.models.ontology import OntologyVersion
from app.models.review import Review


class ResultsRepo:
    """Thin read-only data-access layer for the results endpoint."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_analysis_run(self, run_id: uuid.UUID) -> AnalysisRun | None:
        """Return an analysis run by primary key, or ``None``."""
        return self._db.get(AnalysisRun, run_id)

    def get_curriculum_item(self, item_id: uuid.UUID) -> CurriculumItem | None:
        """Return a curriculum item by primary key, or ``None``."""
        return self._db.get(CurriculumItem, item_id)

    def get_ontology_version(self, version_id: uuid.UUID) -> OntologyVersion | None:
        """Return an ontology version by primary key, or ``None``."""
        return self._db.get(OntologyVersion, version_id)

    def get_compliance_results_for_document(
        self,
        document_id: uuid.UUID,
    ) -> list[IntakeComplianceResult]:
        """Return intake compliance results for a document, ordered by date."""
        stmt = (
            select(IntakeComplianceResult)
            .where(IntakeComplianceResult.document_id == document_id)
            .order_by(IntakeComplianceResult.created_at)
        )
        return list(self._db.scalars(stmt).all())

    def get_reviews_for_run(
        self,
        analysis_run_id: uuid.UUID,
    ) -> list[Review]:
        """Return all reviews for an analysis run, ordered by date."""
        stmt = (
            select(Review)
            .where(Review.analysis_run_id == analysis_run_id)
            .order_by(Review.created_at)
        )
        return list(self._db.scalars(stmt).all())
