"""Local sentence-transformers embedding provider.

Uses the ``sentence-transformers`` library to run an embedding model
in-process.  The model is loaded lazily on first call and cached for
the lifetime of the process, keeping cold-start cost to a single load.

Default model: **all-MiniLM-L6-v2** (384 dimensions, ~80 MB).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.adapters.embeddings.base import EmbeddingError

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ── Module-level model cache ─────────────────────────────────────────
_model_cache: dict[str, "SentenceTransformer"] = {}


def _get_model(model_name: str) -> "SentenceTransformer":
    """Return a cached ``SentenceTransformer`` instance.

    The import is deferred so that the heavy ``torch`` / ``transformers``
    stack is only loaded when this provider is actually used.
    """
    if model_name not in _model_cache:
        try:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading sentence-transformer model '%s' …", model_name)
            _model_cache[model_name] = SentenceTransformer(model_name)
            logger.info("Model '%s' loaded successfully.", model_name)
        except Exception as exc:
            raise EmbeddingError(
                f"Failed to load sentence-transformer model '{model_name}': {exc}"
            ) from exc
    return _model_cache[model_name]


class LocalSentenceTransformerProvider:
    """Embedding provider backed by a local sentence-transformers model.

    Parameters
    ----------
    model_name:
        Hugging Face model identifier.  Defaults to ``all-MiniLM-L6-v2``
        which outputs 384-dimensional vectors.

    Example
    -------
    >>> provider = LocalSentenceTransformerProvider()
    >>> vec = provider.embed_text("Students analyse rock formations")
    >>> len(vec)
    384
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name

    # ── EmbeddingProvider protocol ───────────────────────────────────

    @property
    def model_name(self) -> str:
        """Canonical model name persisted alongside stored vectors."""
        return self._model_name

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Encode a batch of texts into embedding vectors.

        Parameters
        ----------
        texts:
            Plain-text strings to embed.

        Returns
        -------
        list[list[float]]
            One 384-dim vector per input text.

        Raises
        ------
        EmbeddingError
            If encoding fails (model not found, CUDA OOM, etc.).
        """
        if not texts:
            return []

        model = _get_model(self._model_name)
        try:
            embeddings = model.encode(
                texts,
                batch_size=64,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            # numpy ndarray → list[list[float]]
            return [row.tolist() for row in embeddings]
        except Exception as exc:
            raise EmbeddingError(
                f"Failed to encode {len(texts)} texts with "
                f"model '{self._model_name}': {exc}"
            ) from exc

    def embed_text(self, text: str) -> list[float]:
        """Encode a single text string (convenience wrapper).

        Delegates to :meth:`embed_texts` with a one-element list.
        """
        results = self.embed_texts([text])
        return results[0]
