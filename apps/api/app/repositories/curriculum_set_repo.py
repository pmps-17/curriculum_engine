"""Repository for curriculum-set persistence.

Handles CRUD operations on the ``curriculum_sets`` table.
Each method flushes but never commits — the service layer owns the
transaction boundary.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.curriculum_set import CurriculumSet


class CurriculumSetRepo:
    """Thin data-access layer for the curriculum_sets table."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Create ───────────────────────────────────────────────────────

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        title: str,
        subject: str | None = None,
        grade_band: str | None = None,
        description: str | None = None,
        created_by_user_id: uuid.UUID | None = None,
    ) -> CurriculumSet:
        """Insert a new curriculum set. Flushes but does not commit."""
        cs = CurriculumSet(
            organization_id=organization_id,
            title=title,
            subject=subject,
            grade_band=grade_band,
            description=description,
            created_by_user_id=created_by_user_id,
        )
        self._db.add(cs)
        self._db.flush()
        return cs

    # ── Read ─────────────────────────────────────────────────────────

    def get_by_id(self, cs_id: uuid.UUID) -> CurriculumSet | None:
        """Return a curriculum set by primary key, or ``None``."""
        return self._db.get(CurriculumSet, cs_id)

    def list_for_organization(
        self,
        organization_id: uuid.UUID,
    ) -> list[CurriculumSet]:
        """Return all curriculum sets for an organization, newest first."""
        stmt = (
            select(CurriculumSet)
            .where(CurriculumSet.organization_id == organization_id)
            .order_by(CurriculumSet.created_at.desc())
        )
        return list(self._db.scalars(stmt).all())

    # ── Update ───────────────────────────────────────────────────────

    def update(
        self,
        cs: CurriculumSet,
        **kwargs: object,
    ) -> CurriculumSet:
        """Patch mutable fields on a curriculum set.

        Only keys present in *kwargs* are updated. Uses the same sentinel
        pattern as ``OrganizationRepo.update`` — callers can explicitly
        pass ``None`` to clear nullable fields.
        """
        for key, value in kwargs.items():
            setattr(cs, key, value)
        self._db.flush()
        return cs

    # ── Delete ───────────────────────────────────────────────────────

    def delete(self, cs: CurriculumSet) -> None:
        """Hard-delete a curriculum set. Flushes but does not commit."""
        self._db.delete(cs)
        self._db.flush()
