"""Destructive tests require a separate, explicitly named, empty test database."""

import os
from pathlib import Path

import pytest
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from alembic import command
from app.core.config import Settings
from app.db.session import build_engine

BACKEND = Path(__file__).resolve().parents[2]


def validate_test_database_url(
    test_url: str | None, development_url: str | None
) -> str:
    """Return a dedicated test URL or abort before any database operation."""
    if not test_url:
        pytest.fail(
            "TEST_DATABASE_URL is required for destructive tests", pytrace=False
        )
    try:
        target = make_url(test_url)
        development = make_url(development_url) if development_url else None
    except (ArgumentError, ValueError, TypeError):
        pytest.fail("Invalid test database configuration", pytrace=False)
    if (
        target.drivername != "postgresql+psycopg"
        or not target.host
        or not target.database
        or not target.database.endswith("_test")
    ):
        pytest.fail("Invalid test database configuration", pytrace=False)
    if development is not None and (
        target == development or target.database == development.database
    ):
        pytest.fail("Test and development database must be different", pytrace=False)
    return test_url


@pytest.fixture
def migration_database(monkeypatch):
    values = dotenv_values(BACKEND / ".env")
    raw_test_url = os.environ.get("TEST_DATABASE_URL", values.get("TEST_DATABASE_URL"))
    raw_development_url = os.environ.get("DATABASE_URL", values.get("DATABASE_URL"))
    test_url = validate_test_database_url(raw_test_url, raw_development_url)
    try:
        engine = build_engine(Settings(database_url=test_url))
    except (ArgumentError, ValueError, TypeError):
        pytest.fail("Invalid test database configuration", pytrace=False)
    try:
        with engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
            if tables - {"alembic_version", "spatial_ref_sys"}:
                pytest.fail("Migration tests require an empty public schema")
            if "alembic_version" in tables and connection.scalar(
                text("SELECT count(*) FROM alembic_version")
            ):
                pytest.fail("Migration tests require an unversioned test database")
        monkeypatch.setenv("DATABASE_URL", test_url)
        config = Config(str(BACKEND / "alembic.ini"))
        # Alembic env.py prioritizes this validated, pinned test target over env.
        config.attributes["database_url"] = test_url
        # Only arm cleanup after validating the dedicated, empty test database.
        try:
            yield engine, config
        finally:
            # Pin the original test URL even if the test changed the environment.
            # Pytest reports teardown failures separately from the test failure.
            with monkeypatch.context() as cleanup_environment:
                cleanup_environment.setenv("DATABASE_URL", test_url)
                cleanup_failed = False
                try:
                    command.downgrade(config, "base")
                except Exception:
                    cleanup_failed = True
                if cleanup_failed:
                    pytest.fail("Test database cleanup failed", pytrace=False)
    finally:
        engine.dispose()
