"""Alembic environment configuration.

This file configures Alembic's context for running migrations. It loads
settings from ``alembic.ini`` and prepares the migration context for
online (direct database) and offline (script only) modes.

Currently no SQLAlchemy metadata exists in the project. Once ORM models
are introduced, set ``target_metadata`` to the metadata object so that
`alembic revision --autogenerate` can detect schema changes.
"""

from __future__ import annotations

from logging.config import fileConfig
from typing import Optional

from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv
import os

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

# Import application metadata here when available, e.g.:
# from backend import models
# target_metadata = models.Base.metadata

# For now, no SQLAlchemy metadata exists.
target_metadata: Optional[object] = None

# Interpret the config file for Python logging.
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    url = config.get_main_option("sqlalchemy.url")
    if not url or url.startswith("sqlite:///:memory:"):
        url = _database_url_from_env(default=url)

    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    configuration = config.get_section(config.config_ini_section)
    if configuration is None:
        raise RuntimeError("Alembic configuration section missing")

    # Always check for DATABASE_URL environment variable first
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        configuration["sqlalchemy.url"] = env_url
    elif not configuration.get("sqlalchemy.url"):
        configuration["sqlalchemy.url"] = _database_url_from_env()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


def _database_url_from_env(default: Optional[str] = None) -> str:
    """Read the database URL from the ALEMBIC_DATABASE_URL or DATABASE_URL env var."""

    import os

    env_url = os.getenv("ALEMBIC_DATABASE_URL") or os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    if default:
        return default

    raise RuntimeError(
        "Database URL not configured. Set ALEMBIC_DATABASE_URL or DATABASE_URL environment variable."
    )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
