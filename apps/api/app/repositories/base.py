"""Generic base repository with common CRUD helpers.

.. warning::
   **Not currently used.**  All concrete repos define their own
   ``__init__(db)`` and query methods directly.  This class is
   retained as a convenience base for future repositories that
   want generic ``get_by_id`` / ``list_all`` / ``create`` / ``delete``
   helpers.  Delete this file if it remains unused.
"""

from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Thin generic data-access wrapper around a SQLAlchemy session.

    Subclasses set ``model`` to the ORM class they manage.

    Parameters
    ----------
    db:
        An active SQLAlchemy ``Session`` — typically injected via
        FastAPI's ``Depends(get_db)``.
    """

    model: type[T]

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Read ─────────────────────────────────────────────────────────

    def get_by_id(self, entity_id: UUID) -> T | None:
        """Return a single entity by primary key, or ``None``."""
        return self.db.get(self.model, entity_id)

    def list_all(self, *, limit: int = 100, offset: int = 0) -> list[T]:
        """Return a paginated list of entities (newest first by default)."""
        stmt = (
            select(self.model)
            .order_by(self.model.id)  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(stmt).all())

    # ── Write ────────────────────────────────────────────────────────

    def create(self, entity: T) -> T:
        """Add a single entity to the session and flush.

        The caller (service) is responsible for ``db.commit()``.
        """
        self.db.add(entity)
        self.db.flush()
        return entity

    def create_many(self, entities: list[T]) -> list[T]:
        """Add multiple entities to the session and flush."""
        self.db.add_all(entities)
        self.db.flush()
        return entities

    def delete(self, entity: T) -> None:
        """Mark an entity for deletion.  Caller must commit."""
        self.db.delete(entity)
        self.db.flush()
