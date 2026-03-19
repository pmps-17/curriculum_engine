"""Add title, subject, grade_band, deleted_at to documents.

These columns support the Curriculum Library feature: user-facing
title, filterable metadata, and soft-delete.

Revision ID: 0009
Revises: 0008
"""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("title", sa.String(500), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("subject", sa.String(255), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("grade_band", sa.String(100), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "deleted_at")
    op.drop_column("documents", "grade_band")
    op.drop_column("documents", "subject")
    op.drop_column("documents", "title")
