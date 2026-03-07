"""Application configuration loaded from environment variables.

Uses pydantic-settings to validate and type-check every config value at
startup.  All secrets and connection strings come from ``.env`` or the
process environment — nothing is hard-coded.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings.

    Values are read from environment variables (case-insensitive) and
    optionally from a ``.env`` file located next to the running process.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────
    APP_NAME: str = "curriculum-engine-api"
    APP_ENV: Literal["local", "dev", "staging", "production"] = "local"

    # ── Database ─────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://appuser:apppass@localhost:5432/curriculum_engine"

    # ── Embeddings / vector search ───────────────────────────────────
    EMBEDDING_PROVIDER: Literal["local", "openai"] = "local"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    MATCH_TOP_K: int = 5
    SEMANTIC_MIN_SIMILARITY: float = 0.25

    # ── OpenAI (only used when EMBEDDING_PROVIDER="openai") ──────────
    OPENAI_API_KEY: str | None = None
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_TIMEOUT_SECONDS: float = 30.0

    @property
    def is_production(self) -> bool:
        """Return ``True`` when running in the production environment."""
        return self.APP_ENV == "production"

    def validate_openai_config(self) -> None:
        """Raise if OpenAI is selected but the API key is missing."""
        if self.EMBEDDING_PROVIDER == "openai" and not self.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is required when EMBEDDING_PROVIDER='openai'. "
                "Set it in the environment or .env file."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of application settings.

    Using ``lru_cache`` ensures the ``.env`` file is read only once and
    the same ``Settings`` instance is reused across the application.
    """
    return Settings()  # type: ignore[call-arg]
