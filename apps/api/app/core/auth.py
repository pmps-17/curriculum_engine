"""Authentication dependency for FastAPI route handlers.

Provides ``get_current_user`` which reads the ``Authorization`` header,
verifies the Google ID token (JWT), upserts the user row, and returns
a lightweight ``CurrentUser`` context.

Supports two auth modes (controlled by ``AUTH_MODE`` in config):

- ``"google_jwt"`` — production mode; verifies Google ID tokens via
  JWKS.  Returns 401 on missing/invalid tokens.

- ``"dev_header"``  — local development mode; trusts the
  ``X-User-Email`` header (POC compatibility).  Prints a startup
  warning.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import GoogleClaims, TokenVerificationError, verify_google_id_token
from app.repositories.workspace_repo import WorkspaceRepo

logger = logging.getLogger(__name__)

_DEV_MODE_WARNING_LOGGED = False


# =====================================================================
# Value object returned to route handlers
# =====================================================================


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Authenticated user context available in route handlers."""

    user_id: uuid.UUID
    email: str
    name: str | None = None
    auth_mode: str = "google_jwt"


# =====================================================================
# FastAPI dependency
# =====================================================================


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> CurrentUser:
    """Resolve and verify the caller's identity.

    Usage in a router::

        from app.core.auth import CurrentUser, get_current_user

        @router.get("/protected")
        def protected(user: CurrentUser = Depends(get_current_user)):
            ...

    Returns
    -------
    CurrentUser
        Authenticated user context with ``user_id`` and ``email``.

    Raises
    ------
    HTTPException 401
        If no valid credentials are provided.
    """
    settings = get_settings()

    if settings.AUTH_MODE == "dev_header":
        return _resolve_dev_header(request, db)

    return _resolve_google_jwt(request, db)


# =====================================================================
# Internal resolvers
# =====================================================================


def _resolve_google_jwt(request: Request, db: Session) -> CurrentUser:
    """Verify a ``Bearer <id_token>`` from the Authorization header."""

    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    try:
        claims: GoogleClaims = verify_google_id_token(token)
    except TokenVerificationError as exc:
        logger.warning("Token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # Upsert user by email (same as existing workspace_repo logic)
    ws_repo = WorkspaceRepo(db)
    user = ws_repo.upsert_user(claims.email.strip().lower())

    # Update name if provided and not yet set
    if claims.name and not user.name:
        user.name = claims.name
        db.flush()

    return CurrentUser(
        user_id=user.id,
        email=user.email,
        name=user.name,
        auth_mode="google_jwt",
    )


def _resolve_dev_header(request: Request, db: Session) -> CurrentUser:
    """Trust the ``X-User-Email`` header (local development only)."""

    global _DEV_MODE_WARNING_LOGGED
    if not _DEV_MODE_WARNING_LOGGED:
        logger.warning(
            "AUTH_MODE=dev_header — trusting X-User-Email header. "
            "Do NOT use this in production."
        )
        _DEV_MODE_WARNING_LOGGED = True

    email = request.headers.get("x-user-email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Email header (dev mode).",
        )

    email = email.strip().lower()
    ws_repo = WorkspaceRepo(db)
    user = ws_repo.upsert_user(email)

    return CurrentUser(
        user_id=user.id,
        email=user.email,
        name=user.name,
        auth_mode="dev_header",
    )
