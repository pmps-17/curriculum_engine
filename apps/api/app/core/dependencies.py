"""Dependency factories for the adapter layer.

These functions are used with FastAPI's ``Depends()`` or called directly
by services.  They wire protocol interfaces to concrete implementations
based on application settings.

Adding a new embedding provider (e.g. OpenAI) only requires:
1. A new class implementing ``EmbeddingProvider``.
2. A new ``elif`` branch in :func:`get_embedding_provider`.
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy.orm import Session

from app.adapters.embeddings.base import EmbeddingProvider
from app.adapters.vector_store.base import VectorStore
from app.adapters.vector_store.pgvector_store import PgVectorStore
from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    """Return a cached embedding provider instance.

    The provider is chosen by ``settings.EMBEDDING_PROVIDER``:

    - ``"local"`` → :class:`LocalSentenceTransformerProvider`
      (sentence-transformers, runs in-process).
    - ``"openai"`` → :class:`OpenAIEmbeddingProvider`
      (calls the OpenAI embeddings API via httpx).

    Returns
    -------
    EmbeddingProvider
        A singleton provider reused for the lifetime of the process.

    Raises
    ------
    ValueError
        If the configured provider name is not recognised.
    """
    settings = get_settings()

    provider_name = settings.EMBEDDING_PROVIDER

    if provider_name == "local":
        from app.adapters.embeddings.local_sentence_transformer import (
            LocalSentenceTransformerProvider,
        )

        return LocalSentenceTransformerProvider(
            model_name=settings.EMBEDDING_MODEL_NAME,
        )

    if provider_name == "openai":
        settings.validate_openai_config()

        from app.adapters.embeddings.openai_provider import (
            OpenAIEmbeddingProvider,
        )

        return OpenAIEmbeddingProvider(
            api_key=settings.OPENAI_API_KEY,  # type: ignore[arg-type]
            model=settings.OPENAI_EMBEDDING_MODEL,
            base_url=settings.OPENAI_BASE_URL,
            timeout_seconds=settings.OPENAI_TIMEOUT_SECONDS,
        )

    raise ValueError(
        f"Unknown EMBEDDING_PROVIDER: '{provider_name}'. "
        f"Supported values: 'local', 'openai'."
    )


def get_vector_store(db: Session) -> VectorStore:
    """Return a vector store bound to the given database session.

    A new instance is created per request / per session because the
    store holds a reference to the active ``Session``.

    Parameters
    ----------
    db:
        An active SQLAlchemy session (typically from ``Depends(get_db)``).

    Returns
    -------
    VectorStore
        A :class:`PgVectorStore` wired to the provided session.
    """
    return PgVectorStore(db=db)
