from unittest.mock import MagicMock

from fastapi.testclient import TestClient

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
    from app.core.config import Settings

    engine = MagicMock()
    monkeypatch.setattr("app.main.build_engine", lambda settings: engine)
    settings = Settings(database_url="postgresql+psycopg://localhost/db")
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").status_code == 200
        engine.connect.assert_not_called()
    engine.dispose.assert_called_once()
