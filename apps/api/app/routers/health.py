"""Health-check router — liveness and readiness probes.

- ``GET /health``      — lightweight liveness check (no dependencies).
- ``GET /health/db``   — readiness check that verifies DB connectivity.
- ``GET /health/auth`` — reports the active authentication mode.
"""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.db import check_db_connection

router = APIRouter(prefix="/health", tags=["System"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
)
def liveness() -> dict:
    """Return 200 if the process is alive.  No dependency checks."""
    return {"status": "ok"}


@router.get(
    "/db",
    status_code=status.HTTP_200_OK,
    summary="Database readiness probe",
)
def db_readiness() -> JSONResponse:
    """Return 200 if the database is reachable, 503 otherwise."""
    if check_db_connection():
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ok", "database": "connected"},
        )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "degraded", "database": "unreachable"},
    )


@router.get(
    "/auth",
    status_code=status.HTTP_200_OK,
    summary="Authentication mode",
)
def auth_mode() -> dict:
    """Report the active authentication mode (no secrets exposed)."""
    s = get_settings()
    return {
        "auth_mode": s.AUTH_MODE,
        "google_client_id_set": bool(s.GOOGLE_CLIENT_ID),
    }
