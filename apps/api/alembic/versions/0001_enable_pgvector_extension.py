"""Enable pgvector extension.

This is the first migration in the project.  It enables the ``vector``
PostgreSQL extension which is a prerequisite for all future vector-search
columns (e.g. embedding columns on the ``chunks`` table).

The extension must exist *before* any migration attempts to create a
column of type ``VECTOR(...)``, so this revision should always remain
at the base of the migration chain.

Revision ID: 0001
Revises: (none — initial migration)
Create Date: 2026-03-05
"""

from alembic import op

# ── Revision identifiers ────────────────────────────────────────────
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Enable the pgvector extension for vector similarity search.

    ``IF NOT EXISTS`` makes this safe to run multiple times (idempotent).
    Requires that the ``vector`` extension is available on the PostgreSQL
    server — install it with ``apt install postgresql-16-pgvector`` or
    use a Docker image that bundles it (e.g. ``pgvector/pgvector:pg16``).
    """
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")


def downgrade() -> None:
    """Remove the pgvector extension.

    ``IF EXISTS`` ensures the downgrade is safe even if the extension
    was already removed manually.

    WARNING: dropping the extension will cascade-drop any columns or
    indexes that depend on the ``vector`` type.
    """
    op.execute("DROP EXTENSION IF EXISTS vector;")
