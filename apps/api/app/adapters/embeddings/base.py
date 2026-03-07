"""Port (interface) for embedding providers.

Any class that satisfies this protocol can be used as the embedding
backend — local sentence-transformers, OpenAI, Cohere, etc.  Services
depend on this abstraction, never on a concrete library.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Contract that every embedding adapter must fulfil."""

    @property
    def model_name(self) -> str:
        """Return the canonical name of the underlying model.

        This value is persisted alongside every stored vector so that
        mixed-model scenarios remain traceable.
        """
        ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Encode a batch of texts into embedding vectors.

        Parameters
        ----------
        texts:
            One or more plain-text strings to embed.

        Returns
        -------
        list[list[float]]
            A list of vectors, one per input text.  Each vector has
            exactly ``EMBEDDING_DIM`` dimensions (e.g. 384 for
            all-MiniLM-L6-v2).

        Raises
        ------
        EmbeddingError
            If the underlying model fails.
        """
        ...

    def embed_text(self, text: str) -> list[float]:
        """Encode a single text string (convenience wrapper).

        Default implementations should delegate to :meth:`embed_texts`
        with a single-element list.
        """
        ...


class EmbeddingError(Exception):
    """Raised when an embedding provider fails to encode text."""
