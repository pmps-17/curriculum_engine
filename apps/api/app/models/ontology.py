"""Ontology-domain models.

Represents the skills framework the engine maps curriculum against:
ontology versions → pillars → skills → skill indicators.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import OntologyStatus, PillarCode
from app.models.mixins import TimestampMixin


# ── Ontology Version ─────────────────────────────────────────────────

class OntologyVersion(TimestampMixin, Base):
    """A versioned snapshot of the skills ontology.

    Multiple versions can co-exist (draft / active / deprecated) so that
    historical analysis results remain reproducible.
    """

    __tablename__ = "ontology_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version_label: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[OntologyStatus] = mapped_column(
        String(30), default=OntologyStatus.DRAFT, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    pillars: Mapped[list["Pillar"]] = relationship(
        back_populates="ontology_version", cascade="all, delete-orphan"
    )


# ── Pillar ───────────────────────────────────────────────────────────

class Pillar(TimestampMixin, Base):
    """A high-level competency pillar (e.g. P1, P2, P3)."""

    __tablename__ = "pillars"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ontology_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ontology_versions.id"), nullable=False
    )
    code: Mapped[PillarCode] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    ontology_version: Mapped["OntologyVersion"] = relationship(
        back_populates="pillars"
    )
    skills: Mapped[list["Skill"]] = relationship(
        back_populates="pillar", cascade="all, delete-orphan"
    )


# ── Skill ────────────────────────────────────────────────────────────

class Skill(TimestampMixin, Base):
    """A discrete skill within a pillar."""

    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pillar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pillars.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # relationships
    pillar: Mapped["Pillar"] = relationship(back_populates="skills")
    indicators: Mapped[list["SkillIndicator"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    embedding: Mapped["SkillEmbedding | None"] = relationship(
        back_populates="skill", uselist=False, cascade="all, delete-orphan"
    )


# ── Skill Indicator ──────────────────────────────────────────────────

class SkillIndicator(TimestampMixin, Base):
    """Observable behaviour or keyword set that signals skill presence.

    Indicators drive keyword-based matching and can later anchor
    embedding-based retrieval.
    """

    __tablename__ = "skill_indicators"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False
    )
    indicator_text: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        doc="Comma-separated keywords for rule-based matching."
    )
    weight: Mapped[float] = mapped_column(default=1.0, nullable=False)

    # relationships
    skill: Mapped["Skill"] = relationship(back_populates="indicators")
