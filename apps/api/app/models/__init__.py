"""Model package — re-exports every ORM model for easy discovery.

Alembic's ``env.py`` only needs to import ``Base`` and this package to
see every table via ``Base.metadata``.

Usage::

    from app.models import School, Document, AnalysisRun  # etc.
"""

# ── Curriculum domain ────────────────────────────────────────────────
from app.models.curriculum import (  # noqa: F401
    AssessmentArtifact,
    Chunk,
    CurriculumItem,
    CurriculumPackage,
    Document,
    School,
    Section,
    Subject,
    UploadBatch,
)

# ── Ontology domain ─────────────────────────────────────────────────
from app.models.ontology import (  # noqa: F401
    OntologyVersion,
    Pillar,
    Skill,
    SkillIndicator,
)

# ── Analysis domain ──────────────────────────────────────────────────
from app.models.analysis import (  # noqa: F401
    AnalysisFinding,
    AnalysisRun,
    CandidateMatch,
    EvidenceSnippet,
    PillarScore,
    SkillScore,
)

# ── Compliance / coverage / risk ─────────────────────────────────────
from app.models.compliance import (  # noqa: F401
    CoverageAssessment,
    CoverageControl,
    ImprovementAction,
    IntakeComplianceResult,
    RiskScore,
)

# ── Review / audit ───────────────────────────────────────────────────
from app.models.review import (  # noqa: F401
    AuditLog,
    Review,
    ReviewEdit,
)

# ── Embeddings (pgvector) ────────────────────────────────────────────
from app.models.embeddings import (  # noqa: F401
    ChunkEmbedding,
    SkillEmbedding,
)
