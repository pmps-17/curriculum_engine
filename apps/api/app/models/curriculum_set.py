"""CurriculumSet domain model.

A CurriculumSet is the Library-level unit under an Organization.
Documents and AnalysisRuns optionally link to a CurriculumSet so that
related artefacts are grouped together in the UI.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin


class CurriculumSet(TimestampMixin, Base):
    """A named grouping of curriculum artefacts within an organization.

    Every curriculum set belongs to exactly one organization and is
    created by a specific user.  Title duplicates are allowed (different
    versions, subjects, etc.).
    """

    __tablename__ = "curriculum_sets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    grade_band: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # ── Relationships ────────────────────────────────────────────────

    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization", lazy="select",
    )
    created_by: Mapped["User | None"] = relationship(  # noqa: F821
        "User", lazy="select",
    )
