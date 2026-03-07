"""Domain enums used across SQLAlchemy models and Pydantic schemas.

Every status / type / category field in the database is backed by a
Python ``enum.Enum`` so that:
- Only valid values can be persisted.
- Code can compare against named members instead of magic strings.
- Schema validation is automatic via Pydantic.

PostgreSQL stores these as ``VARCHAR`` — the enum *name* is persisted
(not the value), matching SQLAlchemy's default behaviour.
"""

import enum


# ── Upload / Document lifecycle ──────────────────────────────────────

class UploadBatchStatus(str, enum.Enum):
    """Lifecycle of a batch upload."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentStatus(str, enum.Enum):
    """Lifecycle of an individual document."""

    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"


class DocumentType(str, enum.Enum):
    """Broad document classification."""

    LESSON_PLAN = "lesson_plan"
    UNIT_PLAN = "unit_plan"
    SYLLABUS = "syllabus"
    ASSESSMENT = "assessment"
    RUBRIC = "rubric"
    OTHER = "other"


# ── Curriculum ───────────────────────────────────────────────────────

class CurriculumItemType(str, enum.Enum):
    """Granularity level of a curriculum item."""

    LESSON = "lesson"
    ACTIVITY = "activity"
    MODULE = "module"
    UNIT = "unit"


class SectionType(str, enum.Enum):
    """Semantic role of a document section."""

    OBJECTIVE = "objective"
    CONTENT = "content"
    ACTIVITY = "activity"
    ASSESSMENT = "assessment"
    RUBRIC = "rubric"
    OTHER = "other"


# ── Ontology ─────────────────────────────────────────────────────────

class PillarCode(str, enum.Enum):
    """Pillar identifiers for v1 (P2, P3, P5)."""

    P2 = "P2"
    P3 = "P3"
    P5 = "P5"


class OntologyStatus(str, enum.Enum):
    """Publication state of an ontology version."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


# ── Analysis ─────────────────────────────────────────────────────────

class AnalysisRunStatus(str, enum.Enum):
    """Lifecycle of a single analysis run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MatchMethod(str, enum.Enum):
    """How a candidate skill match was produced."""

    KEYWORD = "keyword"
    EMBEDDING = "embedding"
    HYBRID = "hybrid"
    MANUAL = "manual"


class FindingSeverity(str, enum.Enum):
    """Severity level for an analysis finding."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class FindingCategory(str, enum.Enum):
    """Category bucket for an analysis finding."""

    MISSING_COVERAGE = "missing_coverage"
    LOW_CONFIDENCE = "low_confidence"
    STRUCTURAL = "structural"
    COMPLIANCE = "compliance"
    OTHER = "other"


# ── Intake compliance ────────────────────────────────────────────────

class ComplianceStatus(str, enum.Enum):
    """Outcome of an intake compliance check."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIPPED = "skipped"


class ComplianceCheckType(str, enum.Enum):
    """Type of compliance check executed during intake."""

    FORMAT_VALIDATION = "format_validation"
    REQUIRED_SECTIONS = "required_sections"
    LENGTH_CHECK = "length_check"
    LANGUAGE_CHECK = "language_check"
    DUPLICATE_CHECK = "duplicate_check"
    OTHER = "other"


# ── Coverage / Risk ──────────────────────────────────────────────────

class CoverageScope(str, enum.Enum):
    """Scope at which aggregate coverage is evaluated."""

    UNIT = "unit"
    SUBJECT = "subject"
    PACKAGE = "package"


class RiskLevel(str, enum.Enum):
    """Risk tier derived from coverage gaps."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionStatus(str, enum.Enum):
    """Lifecycle of an improvement action."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ActionPriority(str, enum.Enum):
    """Priority of an improvement action."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ── Review ───────────────────────────────────────────────────────────

class ReviewStatus(str, enum.Enum):
    """Lifecycle of a human review."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewEditType(str, enum.Enum):
    """Kind of edit made during a review."""

    SCORE_OVERRIDE = "score_override"
    MATCH_ADDED = "match_added"
    MATCH_REMOVED = "match_removed"
    COMMENT = "comment"


# ── Audit ────────────────────────────────────────────────────────────

class AuditAction(str, enum.Enum):
    """High-level action categories for the audit log."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    REVIEW = "review"
    ANALYSIS_RUN = "analysis_run"
    COMPLIANCE_CHECK = "compliance_check"
