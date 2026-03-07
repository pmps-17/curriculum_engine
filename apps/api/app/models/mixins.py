"""Reusable column mixins for SQLAlchemy models.

Mixins keep cross-cutting concerns (timestamps, soft-delete, etc.) in
one place so that individual model files stay focused on domain columns.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Adds ``created_at`` and ``updated_at`` columns.

    ``created_at`` is set once on insert; ``updated_at`` is refreshed on
    every ``UPDATE`` statement.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
