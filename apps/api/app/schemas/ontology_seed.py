"""Pydantic schemas for ontology seeding validation.

These schemas validate JSON structure from packages/ontology/ files
before persisting to the database.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PillarSeedSchema(BaseModel):
    """Schema for a pillar in the seed JSON."""

    pillar_code: str = Field(
        ..., 
        description="Unique pillar code (e.g., P1, P2, P3)."
    )
    name: str = Field(
        ..., 
        description="Display name of the pillar."
    )
    description: Optional[str] = Field(
        default=None,
        description="Detailed description of the pillar.",
    )
    definition: Optional[str] = Field(
        default=None,
        description="Alternative name for description field; ignored if description present.",
    )
    boundaries: Optional[str] = Field(
        default=None,
        description="Optional scope/boundaries of the pillar.",
    )

    @field_validator("pillar_code")
    @classmethod
    def validate_pillar_code(cls, v: str) -> str:
        """Pillar code must be 1-10 chars, alphanumeric with dash allowed."""
        if not v or len(v) > 10:
            raise ValueError("pillar_code must be 1-10 characters")
        if not all(c.isalnum() or c == "-" for c in v):
            raise ValueError("pillar_code must be alphanumeric (dash allowed)")
        return v.upper()

    def get_description(self) -> str:
        """Return description, falling back to definition if available."""
        return self.description or self.definition or ""


class SkillSeedSchema(BaseModel):
    """Schema for a skill in the seed JSON."""

    pillar_code: str = Field(
        ...,
        description="Parent pillar code (e.g., P1, P2, P3)."
    )
    skill_code: str = Field(
        ...,
        description="Unique skill code (e.g., P1-S1, P2-S2, P3-S3)."
    )
    name: str = Field(
        ...,
        description="Display name of the skill."
    )
    description: str = Field(
        ...,
        description="Detailed description of what this skill entails."
    )

    @field_validator("skill_code")
    @classmethod
    def validate_skill_code(cls, v: str) -> str:
        """Skill code must be 1-50 chars, alphanumeric with dash and period allowed."""
        if not v or len(v) > 50:
            raise ValueError("skill_code must be 1-50 characters")
        if not all(c.isalnum() or c in "-." for c in v):
            raise ValueError("skill_code must be alphanumeric (dash and period allowed)")
        return v.upper()


class IndicatorSeedSchema(BaseModel):
    """Schema for a skill indicator in the seed JSON."""

    skill_code: str = Field(
        ...,
        description="Parent skill code (e.g., P1-S1, P2-S2, P3-S3)."
    )
    indicator_type: str = Field(
        ...,
        description="Type of indicator (e.g., 'keyword', 'behavior', 'observable')."
    )
    indicator_text: str = Field(
        ...,
        description="The actual indicator text (keywords, behavior description, etc.)."
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Optional weight for this indicator (default: 1.0).",
    )
    strength: Optional[str] = Field(
        default=None,
        description="Ignored field; kept for data format compatibility.",
    )

    @field_validator("indicator_type")
    @classmethod
    def validate_indicator_type(cls, v: str) -> str:
        """Indicator type must be lowercase alphanumeric with underscores."""
        if not v or len(v) > 50:
            raise ValueError("indicator_type must be 1-50 characters")
        if not all(c.isalnum() or c == "_" for c in v):
            raise ValueError("indicator_type must be alphanumeric with underscores")
        return v.lower()
