"""Shared fixtures for integration tests using PostgreSQL."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config


DEFAULT_TEST_DB_URL = "postgresql://appapp:appapp@localhost:55432/appapp_test"


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """Return the Postgres URL for integration testing."""

    return os.getenv("TEST_DATABASE_URL", DEFAULT_TEST_DB_URL)


@pytest.fixture(scope="session")
def apply_migrations(test_db_url: str) -> Iterator[None]:
    """Apply Alembic migrations to the test database."""

    project_root = Path(__file__).resolve().parents[3]
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(project_root / "backend" / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

    command.upgrade(alembic_cfg, "head")
    yield


@pytest.fixture(scope="session")
def postgres_engine(apply_migrations: None, test_db_url: str) -> Iterator[sa.Engine]:
    """Provide a SQLAlchemy engine connected to the Postgres test database."""

    engine = sa.create_engine(test_db_url, future=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def clean_database(postgres_engine: sa.Engine) -> Iterator[None]:
    """Truncate core tables before and after each integration test."""

    with postgres_engine.begin() as connection:
        connection.execute(sa.text("TRUNCATE TABLE project_state_transactions CASCADE"))
        connection.execute(sa.text("TRUNCATE TABLE project_state_snapshots CASCADE"))
        connection.execute(sa.text("TRUNCATE TABLE project_state CASCADE"))
    try:
        yield
    finally:
        with postgres_engine.begin() as connection:
            connection.execute(sa.text("TRUNCATE TABLE project_state_transactions CASCADE"))
            connection.execute(sa.text("TRUNCATE TABLE project_state_snapshots CASCADE"))
            connection.execute(sa.text("TRUNCATE TABLE project_state CASCADE"))
