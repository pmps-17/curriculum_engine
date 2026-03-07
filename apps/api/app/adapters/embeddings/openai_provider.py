"""OpenAI embedding provider adapter.

Calls the OpenAI ``/v1/embeddings`` endpoint (or any compatible API)
using ``httpx``.  Supports batch embedding and configurable timeouts.

This provider is **disabled by default** — activate it by setting
``EMBEDDING_PROVIDER=openai`` and supplying ``OPENAI_API_KEY``.

Privacy
-------
Raw input texts are sent to the external API but are **never** logged
by this module.  Only metadata (batch size, model name, latency) is
emitted at ``DEBUG`` level.
"""

from __future__ import annotations

import logging
import time

import httpx

from app.adapters.embeddings.base import EmbeddingError

logger = logging.getLogger(__name__)

#: Maximum texts per single API call (OpenAI supports up to 2048).
_MAX_BATCH_SIZE: int = 512

#: Retry configuration for transient failures (429 / 5xx).
_MAX_RETRIES: int = 3
_RETRY_BASE_DELAY: float = 1.0  # seconds, doubles on each retry
_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})


class OpenAIEmbeddingProvider:
    """Embedding provider backed by the OpenAI embeddings API.

    Parameters
    ----------
    api_key:
        OpenAI API key (``sk-…``).
    model:
        Model identifier, e.g. ``"text-embedding-3-small"``.
    base_url:
        Override the API base URL for Azure OpenAI or compatible proxies.
    timeout_seconds:
        Per-request timeout in seconds.

    Example
    -------
    >>> provider = OpenAIEmbeddingProvider(api_key="sk-...", model="text-embedding-3-small")
    >>> vec = provider.embed_text("Students analyse rock formations")
    >>> len(vec)
    1536
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 30.0,
    ) -> None:
        if not api_key:
            raise EmbeddingError(
                "OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai."
            )

        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(self._timeout),
        )

    # ── EmbeddingProvider protocol ───────────────────────────────────

    @property
    def model_name(self) -> str:
        """Canonical model name persisted alongside stored vectors."""
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Encode a batch of texts via the OpenAI embeddings API.

        Large batches are automatically chunked into sub-batches of
        ``_MAX_BATCH_SIZE`` to stay within API limits.

        Parameters
        ----------
        texts:
            Plain-text strings to embed.

        Returns
        -------
        list[list[float]]
            One vector per input text, ordered to match the input.

        Raises
        ------
        EmbeddingError
            If the API returns an error or the request times out.
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = [[] for _ in texts]

        for batch_start in range(0, len(texts), _MAX_BATCH_SIZE):
            batch = texts[batch_start : batch_start + _MAX_BATCH_SIZE]
            vectors = self._call_api(batch)

            for i, vec in enumerate(vectors):
                all_embeddings[batch_start + i] = vec

        return all_embeddings

    def embed_text(self, text: str) -> list[float]:
        """Encode a single text string (convenience wrapper)."""
        results = self.embed_texts([text])
        return results[0]

    # ── Internal ─────────────────────────────────────────────────────

    def _call_api(self, texts: list[str]) -> list[list[float]]:
        """Send one batch to the OpenAI embeddings endpoint.

        Retries up to ``_MAX_RETRIES`` times on 429 (rate-limit) and 5xx
        (server error) responses with exponential backoff.  The response
        ``data`` array is sorted by ``index`` to guarantee output ordering.
        """
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            start = time.perf_counter()
            try:
                response = self._client.post(
                    "/embeddings",
                    json={
                        "input": texts,
                        "model": self._model,
                    },
                )
                response.raise_for_status()

                elapsed = time.perf_counter() - start
                logger.debug(
                    "OpenAI embeddings: %d text(s), model='%s', %.2fs elapsed (attempt %d).",
                    len(texts),
                    self._model,
                    elapsed,
                    attempt + 1,
                )

                body = response.json()
                data = body.get("data", [])
                data.sort(key=lambda d: d["index"])
                return [item["embedding"] for item in data]

            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code in _RETRYABLE_STATUS_CODES and attempt < _MAX_RETRIES:
                    delay = _RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "OpenAI API returned %d, retrying in %.1fs (attempt %d/%d).",
                        status_code,
                        delay,
                        attempt + 1,
                        _MAX_RETRIES + 1,
                    )
                    time.sleep(delay)
                    last_exc = exc
                    continue
                # Non-retryable or retries exhausted — do NOT log request body
                raise EmbeddingError(
                    f"OpenAI API returned {status_code}: "
                    f"{exc.response.text[:500]}"
                ) from exc

            except httpx.TimeoutException as exc:
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "OpenAI API timed out, retrying in %.1fs (attempt %d/%d).",
                        delay,
                        attempt + 1,
                        _MAX_RETRIES + 1,
                    )
                    time.sleep(delay)
                    last_exc = exc
                    continue
                raise EmbeddingError(
                    f"OpenAI API request timed out after {self._timeout}s "
                    f"({_MAX_RETRIES + 1} attempts)."
                ) from exc

            except httpx.HTTPError as exc:
                raise EmbeddingError(
                    f"OpenAI API request failed: {exc}"
                ) from exc

        # Should not reach here, but just in case
        raise EmbeddingError(
            f"OpenAI API failed after {_MAX_RETRIES + 1} attempts."
        ) from last_exc
