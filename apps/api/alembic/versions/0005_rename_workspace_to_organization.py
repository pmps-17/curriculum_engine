"""Rename workspace → organization across all tables and columns.

Renames:
- workspaces           → organizations
- workspace_members    → organization_members
- workspace_id columns → organization_id (documents, analysis_runs, organization_members)
- All related FK constraints, indexes, and unique constraints

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-15
"""

from alembic import op

# ── Revision identifiers ────────────────────────────────────────────
revision: str = "0005"
down_revision: str = "0004"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Rename workspace → organization everywhere."""

    # ── 1. Rename tables ─────────────────────────────────────────────
    op.rename_table("workspaces", "organizations")
    op.rename_table("workspace_members", "organization_members")

    # ── 2. Rename columns ────────────────────────────────────────────
    op.alter_column("organization_members", "workspace_id", new_column_name="organization_id")
    op.alter_column("documents", "workspace_id", new_column_name="organization_id")
    op.alter_column("analysis_runs", "workspace_id", new_column_name="organization_id")

    # ── 3. Rename indexes on organizations (was workspaces) ──────────
    op.execute("ALTER INDEX ix_workspaces_invite_code RENAME TO ix_organizations_invite_code")
    op.execute("ALTER INDEX pk_workspaces RENAME TO pk_organizations")

    # ── 4. Rename indexes on organization_members (was workspace_members)
    op.execute(
        "ALTER INDEX ix_workspace_members_workspace_id "
        "RENAME TO ix_organization_members_organization_id"
    )
    op.execute(
        "ALTER INDEX ix_workspace_members_user_id "
        "RENAME TO ix_organization_members_user_id"
    )
    op.execute("ALTER INDEX pk_workspace_members RENAME TO pk_organization_members")

    # ── 5. Rename unique constraint on organization_members ──────────
    op.execute(
        "ALTER TABLE organization_members "
        "RENAME CONSTRAINT uq_workspace_members_ws_user "
        "TO uq_organization_members_org_user"
    )

    # ── 6. Rename FK constraints ─────────────────────────────────────
    # organization_members.organization_id → organizations.id
    op.execute(
        "ALTER TABLE organization_members "
        "RENAME CONSTRAINT fk_workspace_members_workspace_id_workspaces "
        "TO fk_organization_members_organization_id_organizations"
    )
    # organization_members.user_id → users.id
    op.execute(
        "ALTER TABLE organization_members "
        "RENAME CONSTRAINT fk_workspace_members_user_id_users "
        "TO fk_organization_members_user_id_users"
    )
    # organizations.owner_user_id → users.id
    op.execute(
        "ALTER TABLE organizations "
        "RENAME CONSTRAINT fk_workspaces_owner_user_id_users "
        "TO fk_organizations_owner_user_id_users"
    )
    # documents.organization_id → organizations.id
    op.execute(
        "ALTER TABLE documents "
        "RENAME CONSTRAINT fk_documents_workspace_id_workspaces "
        "TO fk_documents_organization_id_organizations"
    )
    # analysis_runs.organization_id → organizations.id
    op.execute(
        "ALTER TABLE analysis_runs "
        "RENAME CONSTRAINT fk_analysis_runs_workspace_id_workspaces "
        "TO fk_analysis_runs_organization_id_organizations"
    )


def downgrade() -> None:
    """Revert organization → workspace everywhere."""

    # FK constraints
    op.execute(
        "ALTER TABLE analysis_runs "
        "RENAME CONSTRAINT fk_analysis_runs_organization_id_organizations "
        "TO fk_analysis_runs_workspace_id_workspaces"
    )
    op.execute(
        "ALTER TABLE documents "
        "RENAME CONSTRAINT fk_documents_organization_id_organizations "
        "TO fk_documents_workspace_id_workspaces"
    )
    op.execute(
        "ALTER TABLE organizations "
        "RENAME CONSTRAINT fk_organizations_owner_user_id_users "
        "TO fk_workspaces_owner_user_id_users"
    )
    op.execute(
        "ALTER TABLE organization_members "
        "RENAME CONSTRAINT fk_organization_members_user_id_users "
        "TO fk_workspace_members_user_id_users"
    )
    op.execute(
        "ALTER TABLE organization_members "
        "RENAME CONSTRAINT fk_organization_members_organization_id_organizations "
        "TO fk_workspace_members_workspace_id_workspaces"
    )

    # Unique constraint
    op.execute(
        "ALTER TABLE organization_members "
        "RENAME CONSTRAINT uq_organization_members_org_user "
        "TO uq_workspace_members_ws_user"
    )

    # Indexes
    op.execute(
        "ALTER INDEX ix_organization_members_user_id "
        "RENAME TO ix_workspace_members_user_id"
    )
    op.execute(
        "ALTER INDEX ix_organization_members_organization_id "
        "RENAME TO ix_workspace_members_workspace_id"
    )
    op.execute("ALTER INDEX ix_organizations_invite_code RENAME TO ix_workspaces_invite_code")
    op.execute("ALTER INDEX pk_organizations RENAME TO pk_workspaces")
    op.execute("ALTER INDEX pk_organization_members RENAME TO pk_workspace_members")

    # Columns
    op.alter_column("analysis_runs", "organization_id", new_column_name="workspace_id")
    op.alter_column("documents", "organization_id", new_column_name="workspace_id")
    op.alter_column("organization_members", "organization_id", new_column_name="workspace_id")

    # Tables
    op.rename_table("organization_members", "workspace_members")
    op.rename_table("organizations", "workspaces")
