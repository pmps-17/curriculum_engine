"""Curriculum Engine API — application entry point."""

from fastapi import FastAPI

from app.routers.analyze import router as analyze_router
from app.routers.analysis_runs import router as analysis_runs_router
from app.routers.documents import router as documents_router
from app.routers.health import router as health_router
from app.routers.results import router as results_router
from app.routers.review import router as review_router
from app.routers.uploads import router as uploads_router
from app.routers.workspaces import router as workspaces_router

app = FastAPI(
    title="Curriculum Engine API",
    description="Research-grade curriculum governance and pillar mapping engine.",
    version="0.1.0",
)

# ── Routers ──────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(analyze_router)
app.include_router(analysis_runs_router)
app.include_router(documents_router)
app.include_router(results_router)
app.include_router(review_router)
app.include_router(uploads_router)
app.include_router(workspaces_router)