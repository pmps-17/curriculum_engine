"""Repository package — thin data-access layer over SQLAlchemy sessions.

Repositories encapsulate all direct ``session`` usage (queries, inserts,
flushes).  They contain **no** business logic — that belongs in the
service layer.

Usage::

    from app.repositories.analysis_run_repo import AnalysisRunRepo
    repo = AnalysisRunRepo(db)
    run = repo.create_analysis_run(...)
"""

from app.repositories.analysis_run_repo import AnalysisRunRepo  # noqa: F401
from app.repositories.candidate_repo import CandidateRepo  # noqa: F401
from app.repositories.curriculum_repo import CurriculumRepo  # noqa: F401
from app.repositories.document_repo import DocumentRepo  # noqa: F401
from app.repositories.embedding_repo import EmbeddingRepo  # noqa: F401
from app.repositories.results_repo import ResultsRepo  # noqa: F401
from app.repositories.review_repo import ReviewRepo  # noqa: F401
from app.repositories.scoring_repo import ScoringRepo  # noqa: F401
from app.repositories.organization_repo import OrganizationRepo  # noqa: F401
