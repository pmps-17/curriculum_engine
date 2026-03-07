"""Database engine, session factory, and base model.

All SQLAlchemy ORM models inherit from ``Base`` defined here.  The
``get_db`` dependency yields one session per request and guarantees
cleanup on exit.
"""

import logging
from collections.abc import Generator
from typing import Any

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ── Naming convention for Alembic auto-generated constraints ─────────
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for all ORM models.

    A consistent ``MetaData`` naming convention is attached so that
    Alembic migrations produce deterministic constraint names.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _build_engine() -> Any:
    """Create and return the SQLAlchemy engine from settings."""
    settings = get_settings()
    return create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        echo=False,
        future=True,
    )


engine = _build_engine()

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, Any, None]:
    """FastAPI dependency that provides a database session per request.

    The session is **not** auto-committed — services must call
    ``db.commit()`` explicitly when a transaction succeeds.  The session
    is always closed when the request finishes, even on error.

    Usage::

        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Verify that the database is reachable.

    Executes a lightweight ``SELECT 1`` query.  Returns ``True`` on
    success or ``False`` on failure (logging the exception).  Useful
    for health-check endpoints and startup diagnostics.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection check passed.")
        return True
    except Exception:
        logger.exception("Database connection check failed.")
        return False
