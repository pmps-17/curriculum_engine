"""Shared Pydantic base configuration and common schema primitives.

All API schemas inherit from ``CamelModel`` which enables:
- ``model_config`` with ``from_attributes = True`` for ORM compatibility.
- Consistent JSON behaviour across every endpoint.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CamelModel(BaseModel):
    """Base model for all API schemas.

    Despite the name, this does **not** apply camelCase alias generation.
    It provides shared config: ``from_attributes`` for ORM compatibility,
    ``populate_by_name`` and ``str_strip_whitespace``.

    TODO: rename to ``AppModel`` or add ``alias_generator = to_camel``
    if camelCase JSON keys are desired.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


# ── Tiny reusable types ─────────────────────────────────────────────

class TimestampOut(CamelModel):
    """Mixin-style fields for any response that includes timestamps."""

    created_at: datetime = Field(description="UTC timestamp when the record was created.")
    updated_at: datetime = Field(description="UTC timestamp when the record was last modified.")


class IdTimestampOut(TimestampOut):
    """Response base with ``id`` + timestamps — the most common pattern."""

    id: UUID = Field(description="Unique identifier (UUID).")
