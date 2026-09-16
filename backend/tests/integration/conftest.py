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


@pytest.fixture
def migration_database(monkeypatch):
    values = dotenv_values(BACKEND / ".env")
    test_url = os.environ.get("TEST_DATABASE_URL", values.get("TEST_DATABASE_URL"))
    if not test_url:
        pytest.skip(
            "TEST_DATABASE_URL absent: destructive migration validation pending"
        )
    engine = None
    try:
        target = make_url(test_url)
        development = Settings().database_url
        if (
            development
            and target.database == make_url(development.get_secret_value()).database
        ):
            pytest.fail("Test and development database names must differ")
        if not target.database or not target.database.endswith("_test"):
            pytest.fail("Disposable test database name must end with _test")
        engine = build_engine(Settings(database_url=test_url))
    except (ArgumentError, ValueError, TypeError):
        pass
    # Report outside the exception handler so pytest cannot render its context.
    if engine is None:
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
