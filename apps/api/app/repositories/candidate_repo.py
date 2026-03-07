"""Repository for candidate match persistence.

Handles bulk insertion of candidate matches produced by keyword and/or
semantic matchers.  No business logic — just CRUD.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.analysis import CandidateMatch
from app.models.curriculum import Chunk as ChunkModel
from app.services.scoring_service import CandidateMatchInput


class CandidateRepo:
    """Thin data-access layer for the ``candidate_matches`` table."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def bulk_insert_candidate_matches(
        self,
        *,
        analysis_run_id: uuid.UUID,
        candidates: list[CandidateMatchInput],
        chunk_models: list[ChunkModel],
    ) -> list[CandidateMatch]:
        """Persist candidate matches to the database.

        Builds a ``chunk_index → chunk_id`` lookup from *chunk_models*
        and creates one ``CandidateMatch`` row per candidate.

        Returns the persisted ORM instances (flushed, with IDs).
        """
        index_to_id = {cm.chunk_index: cm.id for cm in chunk_models}
        models: list[CandidateMatch] = []

        for c in candidates:
            chunk_id = index_to_id.get(c.chunk_index)
            if chunk_id is None:
                continue
            m = CandidateMatch(
                analysis_run_id=analysis_run_id,
                chunk_id=chunk_id,
                skill_indicator_id=c.indicator_id,
                match_method=c.match_method,
                raw_score=c.raw_score,
                matched_keywords=c.matched_keywords,
            )
            self._db.add(m)
            models.append(m)

        self._db.flush()
        return models
