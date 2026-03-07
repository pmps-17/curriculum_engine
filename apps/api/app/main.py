"""Curriculum Engine API — application entry point."""

from fastapi import FastAPI

from app.routers.analyze import router as analyze_router
from app.routers.health import router as health_router
from app.routers.results import router as results_router
from app.routers.review import router as review_router

app = FastAPI(
    title="Curriculum Engine API",
    description="Research-grade curriculum governance and pillar mapping engine.",
    version="0.1.0",
)

# ── Routers ──────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(analyze_router)
app.include_router(results_router)
app.include_router(review_router)