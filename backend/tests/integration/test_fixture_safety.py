"""Exercise the real fixture through isolated pytest runs, including failures."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import dotenv_values

pytestmark = pytest.mark.integration
BACKEND = Path(__file__).resolve().parents[2]


def load_safety_fixture():
    fixture_path = Path(__file__).with_name("conftest.py")
    spec = importlib.util.spec_from_file_location("safety_validation", fixture_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_fixture_tests(tmp_path: Path, source: str, **environment: str) -> str:
    fixture_path = str(Path(__file__).with_name("conftest.py"))
    (tmp_path / "conftest.py").write_text(
        "import importlib.util\n"
        "spec = importlib.util.spec_from_file_location(\n"
        f"    'safety_fixture', {fixture_path!r})\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "migration_database = module.migration_database\n"
        "validate_test_database_url = module.validate_test_database_url\n",
        encoding="utf-8",
    )
    test_file = tmp_path / "test_scenario.py"
    test_file.write_text(source, encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "-q",
            "--tb=short",
            "-p",
            "no:cacheprovider",
        ],
        cwd=BACKEND,
        env={**os.environ, **environment},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 1, "Expected the deliberately failing nested test"
    return result.stdout + result.stderr


def run_fixture_tests_success(tmp_path: Path, source: str, **environment: str) -> str:
    fixture_path = str(Path(__file__).with_name("conftest.py"))
    (tmp_path / "conftest.py").write_text(
        "import importlib.util\n"
        "spec = importlib.util.spec_from_file_location(\n"
        f"    'safety_fixture', {fixture_path!r})\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "migration_database = module.migration_database\n",
        encoding="utf-8",
    )
    test_file = tmp_path / "test_scenario.py"
    test_file.write_text(source, encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=BACKEND,
        env={**os.environ, **environment},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout + result.stderr


@pytest.mark.parametrize(
    "test_url,development_url,expected",
    [
        (None, "postgresql+psycopg://u:p@localhost/app", "is required"),
        (
            "postgresql+psycopg://u:p@localhost/app_test",
            "postgresql+psycopg://u:p@localhost/app_test",
            "must be different",
        ),
        (
            "postgresql+psycopg://u:p@localhost/app",
            "postgresql+psycopg://u:p@localhost/development",
            "Invalid test database configuration",
        ),
    ],
)
def test_test_database_validation_fails_closed(test_url, development_url, expected):
    validator = load_safety_fixture().validate_test_database_url
    with pytest.raises(pytest.fail.Exception, match=expected):
        validator(test_url, development_url)


def test_alembic_target_stays_pinned_when_database_url_changes(tmp_path):
    source = """
from alembic import command
from sqlalchemy import inspect

def test_pinned_target(migration_database, monkeypatch):
    engine, config = migration_database
    pinned = config.attributes['database_url']
    assert pinned.endswith('_test')
    monkeypatch.setenv(
        'DATABASE_URL',
        'postgresql+psycopg://blocked:blocked@127.0.0.1/development',
    )
    command.upgrade(config, 'head')
    assert inspect(engine).has_table('usuario')
    command.downgrade(config, 'base')
    assert not inspect(engine).has_table('usuario')
    assert config.attributes['database_url'] == pinned
"""
    output = run_fixture_tests_success(tmp_path, source)
    assert "1 passed" in output


def test_malformed_url_is_sanitized(tmp_path):
    secret = "malformed-url-with-private-value"
    output = run_fixture_tests(
        tmp_path,
        "def test_invalid(migration_database):\n    pass\n",
        TEST_DATABASE_URL=secret,
    )
    assert "Invalid test database configuration" in output
    assert secret not in output
    assert "ArgumentError" not in output
    assert "Traceback" not in output


@pytest.mark.parametrize("failure", ["assertion", "upgrade", "cleanup"])
def test_teardown_restores_base_and_preserves_failure(tmp_path, failure):
    values = dotenv_values(BACKEND / ".env")
    if not os.environ.get("TEST_DATABASE_URL", values.get("TEST_DATABASE_URL")):
        pytest.skip("TEST_DATABASE_URL absent: cleanup validation pending")
    source = """
from alembic import command
from sqlalchemy import inspect, text

def test_original_failure(migration_database, monkeypatch):
    engine, config = migration_database
    if FAILURE == 'upgrade':
        original_upgrade = command.upgrade
        def failed_upgrade(*args, **kwargs):
            original_upgrade(*args, **kwargs)
            raise RuntimeError('original-upgrade-failure')
        monkeypatch.setattr(command, 'upgrade', failed_upgrade)
    if FAILURE == 'cleanup':
        original_downgrade = command.downgrade
        def failed_cleanup(*args, **kwargs):
            original_downgrade(*args, **kwargs)
            raise RuntimeError('private-cleanup-details')
        monkeypatch.setattr(command, 'downgrade', failed_cleanup)
    command.upgrade(config, 'head')
    raise AssertionError('original-assertion-failure')

def test_next_run_starts_clean(migration_database):
    engine, config = migration_database
    with engine.connect() as connection:
        assert not inspect(connection).has_table('usuario')
        assert connection.scalar(text('SELECT count(*) FROM alembic_version')) == 0
    command.upgrade(config, 'head')
"""
    output = run_fixture_tests(tmp_path, f"FAILURE = {failure!r}\n" + source)
    original = "upgrade" if failure == "upgrade" else "assertion"
    assert f"original-{original}-failure" in output
    assert "1 failed, 1 passed" in output
    if failure == "cleanup":
        assert "Test database cleanup failed" in output
        assert "private-cleanup-details" not in output
        assert "1 error" in output
