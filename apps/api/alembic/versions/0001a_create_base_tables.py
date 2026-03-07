"""Create base tables.

Creates all 27 domain tables defined in the ORM models, in strict
foreign-key topological order.  This migration must run after the
pgvector extension (0001) and before the embedding tables (0002).

Revision ID: 0001a
Revises: 0001 (enable pgvector extension)
Create Date: 2026-03-05
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# ── Revision identifiers ────────────────────────────────────────────
revision: str = "0001a"
down_revision: str = "0001"
branch_labels: str | None = None
depends_on: str | None = None


# ── Helpers ──────────────────────────────────────────────────────────

def _uuid_pk() -> sa.Column:
    return sa.Column("id", UUID(as_uuid=True), primary_key=True)


def _uuid_fk(name: str, target: str, nullable: bool = False) -> sa.Column:
    return sa.Column(
        name, UUID(as_uuid=True),
        sa.ForeignKey(target), nullable=nullable,
    )


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    """Create all 27 base tables in FK-safe topological order."""

    # ── Tier 0: no foreign keys ──────────────────────────────────────

    op.create_table(
        "schools",
        _uuid_pk(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), unique=True, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "ontology_versions",
        _uuid_pk(),
        sa.Column("version_label", sa.String(100), nullable=False, unique=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("description", sa.Text, nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "audit_logs",
        _uuid_pk(),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor", sa.String(255), nullable=True),
        sa.Column("detail", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Tier 1: FK → Tier 0 ─────────────────────────────────────────

    op.create_table(
        "upload_batches",
        _uuid_pk(),
        _uuid_fk("school_id", "schools.id"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("uploaded_by", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "curriculum_packages",
        _uuid_pk(),
        _uuid_fk("school_id", "schools.id"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("grade_level", sa.String(50), nullable=True),
        sa.Column("academic_year", sa.String(20), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "pillars",
        _uuid_pk(),
        _uuid_fk("ontology_version_id", "ontology_versions.id"),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        *_timestamps(),
    )

    # ── Tier 2: FK → Tier 1 ─────────────────────────────────────────

    op.create_table(
        "documents",
        _uuid_pk(),
        _uuid_fk("upload_batch_id", "upload_batches.id"),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("document_type", sa.String(30), nullable=False, server_default="other"),
        sa.Column("status", sa.String(30), nullable=False, server_default="uploaded"),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column("raw_text", sa.Text, nullable=True),
        sa.Column("parse_error", sa.Text, nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "subjects",
        _uuid_pk(),
        _uuid_fk("curriculum_package_id", "curriculum_packages.id"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "skills",
        _uuid_pk(),
        _uuid_fk("pillar_id", "pillars.id"),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        *_timestamps(),
    )

    # ── Tier 3: FK → Tier 2 ─────────────────────────────────────────

    op.create_table(
        "curriculum_items",
        _uuid_pk(),
        _uuid_fk("document_id", "documents.id"),
        _uuid_fk("subject_id", "subjects.id", nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("item_type", sa.String(30), nullable=False, server_default="lesson"),
        sa.Column("sequence_order", sa.Integer, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("unit_name", sa.String(255), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "skill_indicators",
        _uuid_pk(),
        _uuid_fk("skill_id", "skills.id"),
        sa.Column("indicator_text", sa.Text, nullable=False),
        sa.Column("keywords", sa.Text, nullable=True),
        sa.Column("weight", sa.Float, nullable=False, server_default="1.0"),
        *_timestamps(),
    )

    # ── Tier 4: FK → Tier 3 ─────────────────────────────────────────

    op.create_table(
        "assessment_artifacts",
        _uuid_pk(),
        _uuid_fk("curriculum_item_id", "curriculum_items.id"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("artifact_text", sa.Text, nullable=True),
        sa.Column("artifact_type", sa.String(50), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "sections",
        _uuid_pk(),
        _uuid_fk("document_id", "documents.id"),
        _uuid_fk("curriculum_item_id", "curriculum_items.id", nullable=True),
        sa.Column("section_type", sa.String(30), nullable=False, server_default="other"),
        sa.Column("heading", sa.String(500), nullable=True),
        sa.Column("body_text", sa.Text, nullable=True),
        sa.Column("sequence_order", sa.Integer, nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "analysis_runs",
        _uuid_pk(),
        _uuid_fk("curriculum_item_id", "curriculum_items.id"),
        _uuid_fk("ontology_version_id", "ontology_versions.id"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("triggered_by", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        *_timestamps(),
    )

    # ── Tier 5: FK → Tier 4 ─────────────────────────────────────────

    op.create_table(
        "chunks",
        _uuid_pk(),
        _uuid_fk("section_id", "sections.id"),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("token_count", sa.Integer, nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "intake_compliance_results",
        _uuid_pk(),
        _uuid_fk("document_id", "documents.id"),
        sa.Column("check_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("detail", sa.Text, nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "coverage_controls",
        _uuid_pk(),
        sa.Column("scope", sa.String(30), nullable=False),
        sa.Column("scope_ref_id", UUID(as_uuid=True), nullable=False),
        _uuid_fk("pillar_id", "pillars.id"),
        sa.Column("target_score", sa.Float, nullable=False, server_default="0.7"),
        sa.Column("description", sa.Text, nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "candidate_matches",
        _uuid_pk(),
        _uuid_fk("analysis_run_id", "analysis_runs.id"),
        _uuid_fk("chunk_id", "chunks.id"),
        _uuid_fk("skill_indicator_id", "skill_indicators.id"),
        sa.Column("match_method", sa.String(30), nullable=False, server_default="keyword"),
        sa.Column("raw_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("matched_keywords", sa.Text, nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "skill_scores",
        _uuid_pk(),
        _uuid_fk("analysis_run_id", "analysis_runs.id"),
        _uuid_fk("skill_id", "skills.id"),
        sa.Column("score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("indicator_hits", sa.Integer, nullable=False, server_default="0"),
        sa.Column("explanation", sa.Text, nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "pillar_scores",
        _uuid_pk(),
        _uuid_fk("analysis_run_id", "analysis_runs.id"),
        _uuid_fk("pillar_id", "pillars.id"),
        sa.Column("score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("skill_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("explanation", sa.Text, nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "evidence_snippets",
        _uuid_pk(),
        _uuid_fk("analysis_run_id", "analysis_runs.id"),
        _uuid_fk("chunk_id", "chunks.id"),
        _uuid_fk("skill_id", "skills.id"),
        sa.Column("snippet_text", sa.Text, nullable=False),
        sa.Column("relevance_score", sa.Float, nullable=False, server_default="0.0"),
        *_timestamps(),
    )

    op.create_table(
        "analysis_findings",
        _uuid_pk(),
        _uuid_fk("analysis_run_id", "analysis_runs.id"),
        sa.Column("severity", sa.String(30), nullable=False, server_default="info"),
        sa.Column("category", sa.String(30), nullable=False, server_default="other"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("detail", sa.Text, nullable=True),
        _uuid_fk("pillar_id", "pillars.id", nullable=True),
        _uuid_fk("skill_id", "skills.id", nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "reviews",
        _uuid_pk(),
        _uuid_fk("analysis_run_id", "analysis_runs.id"),
        sa.Column("reviewer", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("comments", sa.Text, nullable=True),
        *_timestamps(),
    )

    # ── Tier 6: FK → Tier 5 ─────────────────────────────────────────

    op.create_table(
        "review_edits",
        _uuid_pk(),
        _uuid_fk("review_id", "reviews.id"),
        sa.Column("edit_type", sa.String(30), nullable=False),
        sa.Column("target_entity", sa.String(100), nullable=True),
        sa.Column("target_id", UUID(as_uuid=True), nullable=True),
        sa.Column("old_value", sa.Float, nullable=True),
        sa.Column("new_value", sa.Float, nullable=True),
        sa.Column("comment", sa.Text, nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "coverage_assessments",
        _uuid_pk(),
        _uuid_fk("coverage_control_id", "coverage_controls.id"),
        sa.Column("actual_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("item_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("gap", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("detail", sa.Text, nullable=True),
        *_timestamps(),
    )

    # ── Tier 7: FK → Tier 6 ─────────────────────────────────────────

    op.create_table(
        "risk_scores",
        _uuid_pk(),
        _uuid_fk("coverage_assessment_id", "coverage_assessments.id"),
        sa.Column("risk_level", sa.String(30), nullable=False),
        sa.Column("risk_value", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("explanation", sa.Text, nullable=True),
        *_timestamps(),
    )

    # ── Tier 8: FK → Tier 7 ─────────────────────────────────────────

    op.create_table(
        "improvement_actions",
        _uuid_pk(),
        _uuid_fk("risk_score_id", "risk_scores.id"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("priority", sa.String(30), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("assigned_to", sa.String(255), nullable=True),
        *_timestamps(),
    )


def downgrade() -> None:
    """Drop all 27 base tables in reverse topological order."""
    op.drop_table("improvement_actions")
    op.drop_table("risk_scores")
    op.drop_table("coverage_assessments")
    op.drop_table("review_edits")
    op.drop_table("reviews")
    op.drop_table("analysis_findings")
    op.drop_table("evidence_snippets")
    op.drop_table("pillar_scores")
    op.drop_table("skill_scores")
    op.drop_table("candidate_matches")
    op.drop_table("coverage_controls")
    op.drop_table("intake_compliance_results")
    op.drop_table("chunks")
    op.drop_table("analysis_runs")
    op.drop_table("sections")
    op.drop_table("assessment_artifacts")
    op.drop_table("skill_indicators")
    op.drop_table("curriculum_items")
    op.drop_table("skills")
    op.drop_table("subjects")
    op.drop_table("documents")
    op.drop_table("pillars")
    op.drop_table("curriculum_packages")
    op.drop_table("upload_batches")
    op.drop_table("audit_logs")
    op.drop_table("ontology_versions")
    op.drop_table("schools")
