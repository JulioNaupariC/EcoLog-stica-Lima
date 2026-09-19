from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_and_documentation():
    with TestClient(create_app()) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert client.get("/docs").status_code == 200
        schema = client.get("/openapi.json").json()
        assert "/health" in schema["paths"]
        assert client.app.state.engine is None


def test_engine_disposed_on_shutdown(monkeypatch):
    engine = MagicMock()
    audit_engine = MagicMock()
    business_builder = Mock(return_value=engine)
    audit_builder = Mock(return_value=audit_engine)
    monkeypatch.setattr("app.main.build_engine", business_builder)
    monkeypatch.setattr("app.main.build_audit_engine", audit_builder)
    settings = Settings(database_url="postgresql+psycopg://localhost/db")
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health").status_code == 200
        engine.connect.assert_not_called()
        business_builder.assert_called_once_with(settings)
        audit_builder.assert_called_once_with(settings)
    engine.dispose.assert_called_once()
    audit_engine.dispose.assert_called_once()


def test_business_engine_creation_failure_propagates_without_cleanup(monkeypatch):
    original = RuntimeError("business-engine-failure")
    audit_builder = Mock()
    monkeypatch.setattr("app.main.build_engine", Mock(side_effect=original))
    monkeypatch.setattr("app.main.build_audit_engine", audit_builder)
    settings = Settings(database_url="postgresql+psycopg://localhost/db")

    with pytest.raises(RuntimeError, match="^business-engine-failure$"):
        with TestClient(create_app(settings)):
            pass

    audit_builder.assert_not_called()


def test_audit_engine_creation_failure_disposes_business_engine(monkeypatch):
    engine = MagicMock()
    original = RuntimeError("audit-engine-failure")
    monkeypatch.setattr("app.main.build_engine", Mock(return_value=engine))
    monkeypatch.setattr("app.main.build_audit_engine", Mock(side_effect=original))
    settings = Settings(database_url="postgresql+psycopg://localhost/db")

    with pytest.raises(RuntimeError, match="^audit-engine-failure$"):
        with TestClient(create_app(settings)):
            pass

    engine.dispose.assert_called_once()


def test_later_initialization_failure_disposes_both_engines(monkeypatch):
    engine = MagicMock()
    audit_engine = MagicMock()
    original = RuntimeError("factory-failure")
    factory_builder = Mock(side_effect=[MagicMock(), original])
    monkeypatch.setattr("app.main.build_engine", Mock(return_value=engine))
    monkeypatch.setattr("app.main.build_audit_engine", Mock(return_value=audit_engine))
    monkeypatch.setattr("app.main.session_factory", factory_builder)
    settings = Settings(database_url="postgresql+psycopg://localhost/db")

    with pytest.raises(RuntimeError, match="^factory-failure$"):
        with TestClient(create_app(settings)):
            pass

    engine.dispose.assert_called_once()
    audit_engine.dispose.assert_called_once()
