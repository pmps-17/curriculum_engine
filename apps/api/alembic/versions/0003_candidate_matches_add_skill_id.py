"""Add skill_id to candidate_matches, make skill_indicator_id nullable.

Semantic vector retrieval resolves to the **skill** level, not the
indicator level.  This migration adds ``skill_id`` as the primary
semantic reference and relaxes ``skill_indicator_id`` to nullable so
that embedding-based matches can omit it.

Existing rows are backfilled: ``skill_id`` is derived by joining
``skill_indicators.skill_id`` through the existing FK.

Revision ID: 0003
Revises: 0002 (add embedding tables)
Create Date: 2026-03-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# ── Revision identifiers ────────────────────────────────────────────
revision: str = "0003"
down_revision: str = "0002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add skill_id column, make skill_indicator_id nullable, backfill."""

    # 1. Add skill_id column (nullable initially for backfill)
    op.add_column(
        "candidate_matches",
        sa.Column(
            "skill_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # 2. Add FK constraint for skill_id -> skills.id
    op.create_foreign_key(
        "fk_candidate_matches_skill_id_skills",
        "candidate_matches",
        "skills",
        ["skill_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 3. Backfill skill_id from skill_indicators for existing rows
    op.execute(
        """
        UPDATE candidate_matches cm
        SET    skill_id = si.skill_id
        FROM   skill_indicators si
        WHERE  cm.skill_indicator_id = si.id
          AND  cm.skill_id IS NULL
        """
    )

    # 4. Make skill_id NOT NULL now that backfill is done
    op.alter_column(
        "candidate_matches",
        "skill_id",
        nullable=False,
    )

    # 5. Make skill_indicator_id nullable (was NOT NULL)
    op.alter_column(
        "candidate_matches",
        "skill_indicator_id",
        existing_type=UUID(as_uuid=True),
        nullable=True,
    )

    # 6. Add indexes for common query patterns
    op.create_index(
        "ix_candidate_matches_analysis_run_id",
        "candidate_matches",
        ["analysis_run_id"],
    )
    op.create_index(
        "ix_candidate_matches_skill_id",
        "candidate_matches",
        ["skill_id"],
    )
    op.create_index(
        "ix_candidate_matches_run_chunk",
        "candidate_matches",
        ["analysis_run_id", "chunk_id"],
    )


def downgrade() -> None:
    """Remove skill_id column, restore skill_indicator_id to NOT NULL."""

    # Drop indexes
    op.drop_index("ix_candidate_matches_run_chunk", table_name="candidate_matches")
    op.drop_index("ix_candidate_matches_skill_id", table_name="candidate_matches")
    op.drop_index("ix_candidate_matches_analysis_run_id", table_name="candidate_matches")

    # Restore skill_indicator_id NOT NULL (delete rows that would violate)
    op.execute(
        "DELETE FROM candidate_matches WHERE skill_indicator_id IS NULL"
    )
    op.alter_column(
        "candidate_matches",
        "skill_indicator_id",
        existing_type=UUID(as_uuid=True),
        nullable=False,
    )

    # Drop FK constraint and column
    op.drop_constraint(
        "fk_candidate_matches_skill_id_skills",
        "candidate_matches",
        type_="foreignkey",
    )
    op.drop_column("candidate_matches", "skill_id")
