"""Google OIDC JWT verification.

Fetches Google's JWKS (public keys) with in-memory caching and
verifies Google-issued ID tokens (JWTs) against them.

Security guarantees:
- Signature verified using Google's published RSA keys.
- Issuer must be ``accounts.google.com`` or ``https://accounts.google.com``.
- Audience must match ``GOOGLE_CLIENT_ID``.
- ``exp`` and ``iat`` are enforced by PyJWT.
- Tokens are never logged.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import httpx
import jwt
from jwt import PyJWKClient, PyJWKClientError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


# =====================================================================
# Value object returned after successful verification
# =====================================================================


@dataclass(frozen=True, slots=True)
class GoogleClaims:
    """Verified claims extracted from a Google ID token."""

    sub: str
    email: str
    email_verified: bool = True
    name: str | None = None
    picture: str | None = None


# =====================================================================
# Cached JWKS client (singleton with TTL)
# =====================================================================

_jwks_client: PyJWKClient | None = None
_jwks_client_created_at: float = 0.0


def _get_jwks_client() -> PyJWKClient:
    """Return a cached ``PyJWKClient`` instance.

    The client is re-created when the cache TTL expires so that
    rotated keys are picked up automatically.
    """
    global _jwks_client, _jwks_client_created_at

    settings = get_settings()
    now = time.monotonic()

    if (
        _jwks_client is None
        or (now - _jwks_client_created_at) > settings.JWKS_CACHE_TTL_SECONDS
    ):
        _jwks_client = PyJWKClient(
            settings.GOOGLE_JWKS_URI,
            cache_jwk_set=True,
            lifespan=settings.JWKS_CACHE_TTL_SECONDS,
        )
        _jwks_client_created_at = now
        logger.debug("JWKS client created/refreshed.")

    return _jwks_client


# =====================================================================
# Public API
# =====================================================================


class TokenVerificationError(Exception):
    """Raised when an ID token cannot be verified."""


def verify_google_id_token(token: str) -> GoogleClaims:
    """Verify a Google-issued ID token and return its claims.

    Parameters
    ----------
    token:
        The raw JWT string (``id_token`` from Google OAuth).

    Returns
    -------
    GoogleClaims
        Verified claims including ``sub``, ``email``, ``name``.

    Raises
    ------
    TokenVerificationError
        If the token is invalid, expired, has wrong audience/issuer,
        or if the JWKS endpoint is unreachable.
    """
    settings = get_settings()

    if not settings.GOOGLE_CLIENT_ID:
        raise TokenVerificationError(
            "GOOGLE_CLIENT_ID is not configured on the server."
        )

    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.GOOGLE_CLIENT_ID,
            issuer=settings.GOOGLE_ISSUERS,
            options={
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenVerificationError("Token has expired.") from exc
    except jwt.InvalidAudienceError as exc:
        raise TokenVerificationError("Invalid audience.") from exc
    except jwt.InvalidIssuerError as exc:
        raise TokenVerificationError("Invalid issuer.") from exc
    except (jwt.InvalidTokenError, PyJWKClientError) as exc:
        raise TokenVerificationError(f"Token verification failed: {exc}") from exc
    except httpx.HTTPError as exc:
        raise TokenVerificationError(
            f"Could not fetch JWKS keys: {exc}"
        ) from exc

    # Extract required claims
    sub = payload.get("sub")
    email = payload.get("email")
    if not sub or not email:
        raise TokenVerificationError(
            "Token is missing required claims (sub, email)."
        )

    return GoogleClaims(
        sub=sub,
        email=email,
        email_verified=payload.get("email_verified", False),
        name=payload.get("name"),
        picture=payload.get("picture"),
    )
