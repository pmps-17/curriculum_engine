"""Alembic environment configuration.

This file is executed every time Alembic runs (migrate, autogenerate,
etc.).  It wires together:

- ``DATABASE_URL`` from ``app.core.config`` (single source of truth).
- ``Base.metadata`` from the models package so that ``--autogenerate``
  can diff the ORM definitions against the live database.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ── Project imports ──────────────────────────────────────────────────
from app.core.config import get_settings

# Importing the models package forces every model module to be loaded,
# which registers all tables on Base.metadata.
from app.models import *  # noqa: F401, F403
from app.core.db import Base

# ── Alembic config object ───────────────────────────────────────────
config = context.config

# Inject the real DATABASE_URL so we never hard-code credentials in
# alembic.ini.
config.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL)

# Python logging from the ini file.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is what --autogenerate diffs against.
target_metadata = Base.metadata


# ── Offline mode (generate SQL script without a live DB) ─────────────

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Emits SQL statements to stdout / a script file without connecting
    to the database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (connect to a live DB) ───────────────────────────────

def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an engine, connects, and runs migrations inside a
    transaction.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
