from unittest.mock import MagicMock

import pytest

from app.db.check import check_database, main


def probe(values):
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value.scalar.side_effect = values
    return engine


def test_successful_probe():
    check_database(probe([1, "160001", "3.x", 4326]))


@pytest.mark.parametrize(
    "values",
    [
        [0],
        [1, "150000"],
        [1, "160001", None],
        [1, "160001", "3.x", 0],
    ],
)
def test_failed_probe(values):
    with pytest.raises(RuntimeError):
        check_database(probe(values))


def test_missing_configuration_returns_failure(capsys):
    assert main() == 1
    assert "failed" in capsys.readouterr().out


@pytest.mark.parametrize("failure", [False, True])
def test_command_disposes_engine_and_hides_errors(monkeypatch, capsys, failure):
    engine = probe([1, "160001", "3.x", 4326])
    if failure:
        engine.connect.side_effect = RuntimeError("secret password")
    monkeypatch.setattr("app.db.check.build_engine", lambda settings: engine)
    assert main() == int(failure)
    assert "secret password" not in capsys.readouterr().out
    engine.dispose.assert_called_once()
