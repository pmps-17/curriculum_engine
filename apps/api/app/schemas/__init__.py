"""Schema package — re-exports all public request/response schemas.

Usage::

    from app.schemas import AnalyzeRequest, AnalyzeResponse, ReviewRequest
"""

# ── Analysis ─────────────────────────────────────────────────────────
from app.schemas.analysis import (  # noqa: F401
    AnalyzeRequest,
    AnalyzeResponse,
    EvidenceSnippetOut,
    FindingOut,
    IntakeComplianceResultOut,
    PillarScoreOut,
    SkillScoreOut,
)

# ── Review ───────────────────────────────────────────────────────────
from app.schemas.review import (  # noqa: F401
    ReviewEditIn,
    ReviewEditOut,
    ReviewRequest,
    ReviewResponse,
)

# ── Stored results ───────────────────────────────────────────────────
from app.schemas.results import (  # noqa: F401
    ResultResponse,
    ReviewSummaryOut,
)

# ── Base ─────────────────────────────────────────────────────────────
from app.schemas.base import CamelModel  # noqa: F401

# ── Organizations ─────────────────────────────────────────────────────
from app.schemas.organizations import (  # noqa: F401
    OrganizationCreateRequest,
    OrganizationJoinOut,
    OrganizationJoinRequest,
    OrganizationOut,
    OrganizationUpdateRequest,
)
