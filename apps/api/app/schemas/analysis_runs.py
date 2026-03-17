"""Response schemas for the analysis-runs listing endpoint.

Provides a lightweight ``AnalysisRunSummary`` — just enough for the
Compare selector and organization dashboards without the full result
payload.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import AnalysisRunStatus
from app.schemas.base import CamelModel


class AnalysisRunSummary(CamelModel):
    """One row in the analysis-runs listing."""

    analysis_run_id: UUID = Field(description="Unique run identifier.")
    title: str | None = Field(
        default=None, description="Curriculum item title."
    )
    subject: str | None = Field(
        default=None, description="Subject name, if known."
    )
    grade_band: str | None = Field(
        default=None, description="Grade band, if known."
    )
    status: AnalysisRunStatus = Field(description="Run status.")
    created_at: datetime = Field(description="When the run was created.")
    document_id: UUID | None = Field(
        default=None, description="Source document, if applicable."
    )
