"""Add curriculum_sets table and link documents + analysis_runs.

Revision ID: 0007
Revises: 0006
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Create curriculum_sets table ──────────────────────────────
    op.create_table(
        "curriculum_sets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("grade_band", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── 2. Add nullable FK columns to existing tables ────────────────
    op.add_column(
        "documents",
        sa.Column("curriculum_set_id", UUID(as_uuid=True), sa.ForeignKey("curriculum_sets.id"), nullable=True),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("curriculum_set_id", UUID(as_uuid=True), sa.ForeignKey("curriculum_sets.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analysis_runs", "curriculum_set_id")
    op.drop_column("documents", "curriculum_set_id")
    op.drop_table("curriculum_sets")
