"""Add workspace tenancy: users, workspaces, workspace_members tables
and workspace_id FK on documents and analysis_runs.

Backfill strategy: if existing rows found, create a "Default Workspace"
owned by a system user and assign all orphaned documents and analysis_runs.

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-12
"""

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# ── Revision identifiers ────────────────────────────────────────────
revision: str = "0004"
down_revision: str = "0003"
branch_labels: str | None = None
depends_on: str | None = None

# ── Constants for backfill ───────────────────────────────────────────
_SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_SYSTEM_USER_EMAIL = "system@curriculum-engine.local"
_DEFAULT_WS_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
_DEFAULT_WS_NAME = "Default Workspace"
_DEFAULT_WS_CODE = "DEFAULT0"


def upgrade() -> None:
    """Create tenancy tables, add workspace_id columns, backfill."""

    now = datetime.now(timezone.utc)

    # ── 1. Create users table ────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── 2. Create workspaces table ───────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("invite_code", sa.String(12), nullable=False),
        sa.Column("owner_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_workspaces_invite_code", "workspaces", ["invite_code"], unique=True)

    # ── 3. Create workspace_members table ────────────────────────────
    op.create_table(
        "workspace_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_ws_user"),
    )
    op.create_index("ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"])
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])

    # ── 4. Add workspace_id to documents (nullable for backfill) ─────
    op.add_column(
        "documents",
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=True),
    )

    # ── 5. Add workspace_id to analysis_runs (nullable for backfill) ─
    op.add_column(
        "analysis_runs",
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=True),
    )

    # ── 6. Backfill: create default user + workspace if rows exist ───
    conn = op.get_bind()

    doc_count = conn.execute(sa.text("SELECT count(*) FROM documents")).scalar()
    run_count = conn.execute(sa.text("SELECT count(*) FROM analysis_runs")).scalar()

    if doc_count or run_count:
        # Insert system user
        conn.execute(
            sa.text(
                "INSERT INTO users (id, email, name, created_at, updated_at) "
                "VALUES (:id, :email, :name, :ca, :ua) "
                "ON CONFLICT (email) DO NOTHING"
            ),
            {
                "id": _SYSTEM_USER_ID,
                "email": _SYSTEM_USER_EMAIL,
                "name": "System",
                "ca": now,
                "ua": now,
            },
        )
        # Insert default workspace
        conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, name, invite_code, owner_user_id, created_at, updated_at) "
                "VALUES (:id, :name, :code, :owner, :ca, :ua) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "id": _DEFAULT_WS_ID,
                "name": _DEFAULT_WS_NAME,
                "code": _DEFAULT_WS_CODE,
                "owner": _SYSTEM_USER_ID,
                "ca": now,
                "ua": now,
            },
        )
        # Add system user as member
        conn.execute(
            sa.text(
                "INSERT INTO workspace_members (id, workspace_id, user_id, created_at, updated_at) "
                "VALUES (:id, :ws, :usr, :ca, :ua) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "id": uuid.uuid4(),
                "ws": _DEFAULT_WS_ID,
                "usr": _SYSTEM_USER_ID,
                "ca": now,
                "ua": now,
            },
        )

        # Backfill workspace_id on orphaned rows
        conn.execute(
            sa.text("UPDATE documents SET workspace_id = :ws WHERE workspace_id IS NULL"),
            {"ws": _DEFAULT_WS_ID},
        )
        conn.execute(
            sa.text("UPDATE analysis_runs SET workspace_id = :ws WHERE workspace_id IS NULL"),
            {"ws": _DEFAULT_WS_ID},
        )

    # ── 7. Add FK constraints ────────────────────────────────────────
    op.create_foreign_key(
        "fk_documents_workspace_id_workspaces",
        "documents",
        "workspaces",
        ["workspace_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_analysis_runs_workspace_id_workspaces",
        "analysis_runs",
        "workspaces",
        ["workspace_id"],
        ["id"],
    )

    # ── 8. Indexes on workspace_id ───────────────────────────────────
    op.create_index("ix_documents_workspace_id", "documents", ["workspace_id"])
    op.create_index("ix_analysis_runs_workspace_id", "analysis_runs", ["workspace_id"])


def downgrade() -> None:
    """Remove tenancy tables and columns."""

    op.drop_index("ix_analysis_runs_workspace_id", table_name="analysis_runs")
    op.drop_index("ix_documents_workspace_id", table_name="documents")

    op.drop_constraint("fk_analysis_runs_workspace_id_workspaces", "analysis_runs", type_="foreignkey")
    op.drop_constraint("fk_documents_workspace_id_workspaces", "documents", type_="foreignkey")

    op.drop_column("analysis_runs", "workspace_id")
    op.drop_column("documents", "workspace_id")

    op.drop_table("workspace_members")
    op.drop_table("workspaces")
    op.drop_table("users")
