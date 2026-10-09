import json
from unittest.mock import MagicMock, Mock
from urllib.error import HTTPError, URLError

import pytest

from app.monitoring import poll


def response(body=b'{"status":"ok","database":"up"}', status=200):
    result = MagicMock()
    result.__enter__.return_value.status = status
    result.__enter__.return_value.read.return_value = body
    return result


@pytest.mark.parametrize("url", ["http://local/health", "http://local/health/ready"])
def test_probe_success(monkeypatch, url):
    monkeypatch.setattr(poll, "urlopen", Mock(return_value=response()))
    assert poll.check(url)["available"] is True


@pytest.mark.parametrize(
    "body",
    [
        b"not-json",
        b"[]",
        b'{"status":"unavailable"}',
        b'{"status":"ok","database":"down"}',
    ],
)
def test_bad_probe_response(monkeypatch, body):
    monkeypatch.setattr(poll, "urlopen", Mock(return_value=response(body)))
    assert not poll.check("http://local/health/ready")["available"]


@pytest.mark.parametrize(
    "error",
    [
        URLError("private"),
        TimeoutError(),
        OSError(),
        HTTPError("http://local", 503, "private", {}, None),
    ],
)
def test_http_and_transport_errors(monkeypatch, error):
    monkeypatch.setattr(poll, "urlopen", Mock(side_effect=error))
    result = poll.check("http://local/health")
    assert not result["available"]
    assert "private" not in str(result)


def test_slow_response_not_available(monkeypatch):
    monkeypatch.setattr(poll, "urlopen", Mock(return_value=response()))
    monkeypatch.setattr(poll, "monotonic", Mock(side_effect=[0, 6]))
    assert not poll.check("http://local/health")["available"]


def test_sample_requires_api_and_database(monkeypatch):
    monkeypatch.setattr(
        poll, "check", Mock(side_effect=[{"available": True}, {"available": False}])
    )
    result = poll.sample("http://local")
    assert result["state"] == "UNAVAILABLE"
    assert result["timestamp"].endswith("+00:00")


def test_finite_poll_and_default_interval(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["poll", "--samples", "2"])
    monkeypatch.setattr(poll, "sample", lambda url: {"state": "AVAILABLE"})
    sleep = Mock()
    monkeypatch.setattr(poll, "sleep", sleep)
    assert poll.main() == 0
    assert [
        json.loads(row)["state"] for row in capsys.readouterr().out.splitlines()
    ] == ["AVAILABLE", "AVAILABLE"]
    assert sleep.call_count == 1


@pytest.mark.parametrize(
    "args",
    [
        ["--url", "ftp://host"],
        ["--url", "http://secret:pwd@host"],
        ["--url", "http://host/path"],
        ["--interval", "0"],
        ["--samples", "-1"],
        ["--url", "http://host?token=secret"],
    ],
)
def test_invalid_options_rejected(monkeypatch, args):
    monkeypatch.setattr("sys.argv", ["poll"] + args)
    with pytest.raises(SystemExit):
        poll.main()


def test_keyboard_interrupt_exits(monkeypatch):
    monkeypatch.setattr("sys.argv", ["poll"])
    monkeypatch.setattr(poll, "sample", Mock(side_effect=KeyboardInterrupt))
    assert poll.main() == 0
