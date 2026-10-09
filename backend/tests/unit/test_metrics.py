from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError

from app.api.dependencies import get_authenticated_session, get_authentication_service
from app.core.config import Settings
from app.core.rbac import Identidad, Rol
from app.main import create_app
from app.monitoring.database import instrument_engine
from app.monitoring.metrics import BUCKETS, Metrics, labels
from app.monitoring.probe import build_probe_engine, probe_database
from app.services.autenticacion import AuthenticatedSession
from app.services.autorizacion import AutorizacionService


def test_histogram_cumulative_buckets_and_safe_labels():
    metrics = Metrics()
    metrics.observe(
        "ecolog_http_request_duration_seconds", ("POST", "/pedidos", "201"), 2
    )
    output = metrics.render()
    assert 'le="1.0"} 0' in output
    assert 'le="2.0"} 1' in output
    assert 'le="+Inf"} 1' in output
    assert '_sum{method="POST",route="/pedidos",status="201"} 2.0' in output
    assert output.endswith("\n")
    assert len(BUCKETS) == 11
    assert labels(("a",), ('"\\\n',)) == '{a="\\"\\\\\\n"}'
    assert not any(row.startswith("ecolog_database_up ") for row in output.splitlines())


def test_metrics_are_thread_safe_and_isolated():
    metrics = Metrics()

    def record(_):
        metrics.increment("ecolog_http_requests_total", ("GET", "/health", "200"))
        metrics.observe("ecolog_database_probe_duration_seconds", (), 0.01)

    with ThreadPoolExecutor(max_workers=10) as executor:
        list(executor.map(record, range(500)))
    assert (
        metrics.counters["ecolog_http_requests_total", ("GET", "/health", "200")] == 500
    )
    assert metrics.histograms["ecolog_database_probe_duration_seconds", ()][2] == 500
    assert not Metrics().counters


def test_request_counts_5xx_and_no_private_labels():
    app = create_app(Settings(database_url=None))

    @app.get("/example/{identifier}")
    def example(identifier: str):
        raise HTTPException(503, "unavailable")

    @app.get("/crash")
    def crash():
        raise RuntimeError("private-error")

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/example/private-DNI?token=secret").status_code == 503
        assert client.get("/crash").status_code == 500
        for unknown in ("/unknown-private-1", "/unknown-private-2"):
            assert client.get(unknown).status_code == 404
        output = app.state.metrics.render()
        assert 'route="/example/{identifier}",status="503"} 1' in output
        assert 'ecolog_http_5xx_total{method="GET",route="/crash"} 1' in output
        assert 'route="unmatched",status="404"} 2' in output
        assert all(word not in output for word in ("private", "secret", "token="))
        assert all(count == 0 for count in app.state.metrics.active.values())


@pytest.mark.parametrize("role", list(Rol))
def test_metrics_authorization_uses_existing_rbac(role):
    app = create_app(Settings(database_url=None))
    identity = Identidad(uuid4(), role, "ACTIVO")
    app.dependency_overrides[get_authenticated_session] = lambda: AuthenticatedSession(
        uuid4(), identity
    )
    with TestClient(app) as client:
        app.state.authorization_service = AutorizacionService(Mock())
        response = client.get("/metrics")
        expected = 403 if role == Rol.CONDUCTOR else 200
        assert response.status_code == expected
        if expected == 200:
            assert response.headers["content-type"].startswith(
                "text/plain; version=0.0.4"
            )
            assert response.headers["cache-control"] == "no-store"
        assert ("GET", "/metrics") not in app.state.metrics.active


def test_metrics_unauthenticated_rejected():
    app = create_app(Settings(database_url=None))
    app.dependency_overrides[get_authentication_service] = lambda: Mock()
    with TestClient(app) as client:
        assert client.get("/metrics").status_code == 401


def test_real_sql_execution_success_failure_and_no_payloads():
    engine = create_engine("sqlite://")
    metrics = Metrics()
    instrument_engine(engine, metrics, "business")
    with engine.connect() as connection:
        assert connection.scalar(select(1)) == 1
        assert (
            connection.scalar(text("SELECT :value"), {"value": "private-DNI"})
            == "private-DNI"
        )
        with pytest.raises(DBAPIError):
            connection.execute(text("SELECT * FROM private_missing_table"))
    output = metrics.render()
    assert 'engine="business",operation="SELECT",outcome="success"} 1' in output
    assert 'engine="business",operation="OTHER",outcome="success"} 1' in output
    assert 'engine="business",operation="OTHER",outcome="error"} 1' in output
    assert "private" not in output
    engine.dispose()


@pytest.mark.parametrize("value,expected", [(1, True), (0, False), (None, False)])
def test_database_readiness_values(value, expected):
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value.scalar.return_value = value
    metrics = Metrics()
    ok, elapsed = probe_database(engine, metrics)
    assert ok == expected and elapsed >= 0
    assert metrics.db_up == int(expected)
    assert metrics.db_checked > 0


def test_database_unavailable_safe_and_liveness_independent():
    app = create_app(Settings(database_url=None))
    with TestClient(app) as client:
        failed = MagicMock()
        failed.connect.side_effect = RuntimeError("password=private")
        app.state.probe_engine = failed
        assert client.get("/health").json() == {"status": "ok"}
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["database"] == "down"
        assert "private" not in response.text
        assert app.state.metrics.db_up == 0


def test_unconfigured_database_is_not_available():
    assert build_probe_engine(Settings(database_url=None)) is None
    assert probe_database(None, Metrics())[0] is False


def test_probe_connection_limits(monkeypatch):
    builder = Mock()
    monkeypatch.setattr("app.monitoring.probe.create_engine", builder)
    build_probe_engine(Settings(database_url="postgresql+psycopg://localhost/test"))
    assert builder.call_args.kwargs["pool_size"] == 1
    assert builder.call_args.kwargs["max_overflow"] == 0
    assert builder.call_args.kwargs["connect_args"]["connect_timeout"] == 2


def test_slow_probe_cannot_report_available(monkeypatch):
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value.scalar.return_value = 1
    monkeypatch.setattr("app.monitoring.probe.perf_counter", Mock(side_effect=[0, 6]))
    assert probe_database(engine, Metrics())[0] is False


def test_readiness_success(monkeypatch):
    app = create_app(Settings(database_url=None))
    with TestClient(app) as client:
        engine = MagicMock()
        engine.connect.return_value.__enter__.return_value.scalar.return_value = 1
        app.state.probe_engine = engine
        result = client.get("/health/ready")
        assert result.status_code == 200 and result.json()["database"] == "up"
        assert result.headers["cache-control"] == "no-store"


def test_error_hook_without_execution_is_ignored(monkeypatch):
    callbacks = {}
    monkeypatch.setattr(
        "app.monitoring.database.event.listen",
        lambda engine, name, callback: callbacks.update({name: callback}),
    )
    metrics = Metrics()
    instrument_engine(Mock(), metrics, "audit")
    callbacks["handle_error"](SimpleNamespace(execution_context=None))
    assert not metrics.counters


def test_inflight_observed_during_request_and_returns_to_zero():
    app = create_app(Settings(database_url=None))

    @app.get("/blocking")
    def blocking():
        assert app.state.metrics.active["GET", "/blocking"] == 1
        return {"ok": True}

    with TestClient(app) as client:
        assert client.get("/blocking").status_code == 200
        assert app.state.metrics.active["GET", "/blocking"] == 0


def test_cors_preflight_and_unsupported_method_are_counted():
    app = create_app(Settings(database_url=None, cors_allowed_origins=["http://test"]))
    with TestClient(app) as client:
        result = client.options(
            "/conductores",
            headers={"Origin": "http://test", "Access-Control-Request-Method": "POST"},
        )
        assert result.status_code == 200
        assert (
            app.state.metrics.counters[
                "ecolog_http_requests_total", ("OPTIONS", "/conductores", "200")
            ]
            == 1
        )
        assert client.request("CUSTOM", "/health").status_code == 405
        assert (
            app.state.metrics.counters[
                "ecolog_http_requests_total", ("OTHER", "/health", "405")
            ]
            == 1
        )


def test_probe_engine_disposed_on_lifespan_failure(monkeypatch):
    business, audit, probe = MagicMock(), MagicMock(), MagicMock()
    monkeypatch.setattr("app.main.build_engine", Mock(return_value=business))
    monkeypatch.setattr("app.main.build_audit_engine", Mock(return_value=audit))
    monkeypatch.setattr("app.main.build_probe_engine", Mock(return_value=probe))
    monkeypatch.setattr("app.main.instrument_engine", Mock(side_effect=RuntimeError()))
    app = create_app(Settings(database_url="postgresql+psycopg://localhost/test"))
    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass
    for engine in (business, audit, probe):
        engine.dispose.assert_called_once()


def test_request_cancellation_not_counted_as_http_5xx():
    import asyncio

    from app.monitoring.http import MetricsMiddleware

    app = create_app(Settings(database_url=None))

    async def cancelled(scope, receive, send):
        raise asyncio.CancelledError()

    async def noop(*args):
        pass

    metrics = Metrics()
    middleware = MetricsMiddleware(cancelled, metrics)
    scope = {"type": "http", "path": "/health", "method": "GET", "app": app}
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(middleware(scope, noop, noop))
    assert metrics.counters["ecolog_http_5xx_total", ("GET", "/health")] == 0
    assert (
        metrics.counters[
            "ecolog_http_requests_total", ("GET", "/health", "no_response")
        ]
        == 1
    )
    assert metrics.active["GET", "/health"] == 0
