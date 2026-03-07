"""Add embedding tables.

Creates ``chunk_embeddings`` and ``skill_embeddings`` tables to store
precomputed vector embeddings produced by sentence-transformers
(all-MiniLM-L6-v2, 384 dimensions).

These tables depend on the ``vector`` extension enabled in revision 0001
and the base tables created in revision 0001a.
No ANN indexes (HNSW / IVFFlat) are added yet — the v1 refactor uses
exact (brute-force) nearest-neighbour search.

Revision ID: 0002
Revises: 0001a (create base tables)
Create Date: 2026-03-05
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# ── Revision identifiers ────────────────────────────────────────────
revision: str = "0002"
down_revision: str = "0001a"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create chunk_embeddings and skill_embeddings tables."""

    # ── chunk_embeddings ─────────────────────────────────────────────
    op.create_table(
        "chunk_embeddings",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chunk_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chunks.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("embedding_model_name", sa.String(128), nullable=False),
        sa.Column("embedding_vector", Vector(384), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_chunk_embeddings_model_name",
        "chunk_embeddings",
        ["embedding_model_name"],
    )

    # ── skill_embeddings ─────────────────────────────────────────────
    op.create_table(
        "skill_embeddings",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "skill_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("embedding_model_name", sa.String(128), nullable=False),
        sa.Column("embedding_vector", Vector(384), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_skill_embeddings_model_name",
        "skill_embeddings",
        ["embedding_model_name"],
    )


def downgrade() -> None:
    """Drop both embedding tables (indexes are removed automatically)."""
    op.drop_table("skill_embeddings")
    op.drop_table("chunk_embeddings")
