"""Repository for analysis run lifecycle persistence.

Handles creation, status updates, and lookup of ``AnalysisRun`` rows.
All methods flush but never commit — the caller owns the transaction.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisRun
from app.models.enums import AnalysisRunStatus, OntologyStatus
from app.models.ontology import OntologyVersion


class AnalysisRunRepo:
    """Thin data-access layer for the ``analysis_runs`` table."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def resolve_ontology_version(
        self,
        requested_id: uuid.UUID | None,
    ) -> OntologyVersion | None:
        """Return the requested ontology version or the latest active one.

        Returns ``None`` if nothing suitable exists (caller decides the error).
        """
        if requested_id:
            return self._db.get(OntologyVersion, requested_id)

        stmt = (
            select(OntologyVersion)
            .where(OntologyVersion.status == OntologyStatus.ACTIVE)
            .order_by(OntologyVersion.created_at.desc())
            .limit(1)
        )
        return self._db.scalars(stmt).first()

    def create_analysis_run(
        self,
        *,
        curriculum_item_id: uuid.UUID,
        ontology_version_id: uuid.UUID,
        triggered_by: str | None = None,
        organization_id: uuid.UUID | None = None,
        curriculum_set_id: uuid.UUID | None = None,
    ) -> AnalysisRun:
        """Insert a new analysis run in ``RUNNING`` state."""
        run = AnalysisRun(
            curriculum_item_id=curriculum_item_id,
            ontology_version_id=ontology_version_id,
            status=AnalysisRunStatus.RUNNING,
            triggered_by=triggered_by,
            organization_id=organization_id,
            curriculum_set_id=curriculum_set_id,
        )
        self._db.add(run)
        self._db.flush()
        return run

    def mark_completed(self, run: AnalysisRun) -> None:
        """Set the run status to ``COMPLETED`` and flush."""
        run.status = AnalysisRunStatus.COMPLETED
        self._db.flush()

    def mark_failed(
        self,
        run: AnalysisRun,
        error_message: str | None = None,
    ) -> None:
        """Set the run status to ``FAILED`` with an optional message."""
        run.status = AnalysisRunStatus.FAILED
        run.error_message = (error_message or "")[:2000]
        self._db.flush()

    def get_by_id(self, run_id: uuid.UUID) -> AnalysisRun | None:
        """Return an analysis run by primary key."""
        return self._db.get(AnalysisRun, run_id)

    def list_for_organization(
        self,
        organization_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Return lightweight run summaries for an organization.

        Joins through ``curriculum_items`` (title, document_id) and
        optionally ``subjects`` (name) in a single query to avoid N+1.

        Returns plain dicts — the router maps them into Pydantic models.
        """
        from app.models.curriculum import CurriculumItem, Subject

        stmt = (
            select(
                AnalysisRun.id.label("analysis_run_id"),
                CurriculumItem.title.label("title"),
                Subject.name.label("subject"),
                AnalysisRun.status,
                AnalysisRun.created_at,
                CurriculumItem.document_id.label("document_id"),
            )
            .join(
                CurriculumItem,
                CurriculumItem.id == AnalysisRun.curriculum_item_id,
            )
            .outerjoin(
                Subject,
                Subject.id == CurriculumItem.subject_id,
            )
            .where(AnalysisRun.organization_id == organization_id)
            .order_by(AnalysisRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = self._db.execute(stmt).mappings().all()
        return [dict(r) for r in rows]
