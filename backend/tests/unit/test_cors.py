"""Browser-facing CORS contract without database access."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_authentication_service
from app.core.config import Settings
from app.core.rbac import Identidad, Rol
from app.main import create_app
from app.services.autenticacion import LoginResult

FRONTEND_ORIGIN = "http://127.0.0.1:5173"
PREFLIGHT_HEADERS = {
    "Origin": FRONTEND_ORIGIN,
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type",
}


@pytest.mark.parametrize("path", ["/login", "/pedidos"])
def test_json_post_preflight_from_allowed_origin(path):
    app = create_app(
        Settings(database_url=None, cors_allowed_origins=[FRONTEND_ORIGIN])
    )
    with TestClient(app) as client:
        response = client.options(path, headers=PREFLIGHT_HEADERS)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "POST" in response.headers["access-control-allow-methods"].split(", ")
    assert "content-type" in response.headers["access-control-allow-headers"].lower()
    assert response.headers["vary"] == "Origin"
    assert "set-cookie" not in response.headers


def test_unlisted_origin_is_not_authorized_by_preflight():
    app = create_app(
        Settings(database_url=None, cors_allowed_origins=[FRONTEND_ORIGIN])
    )
    with TestClient(app) as client:
        response = client.options(
            "/pedidos",
            headers={**PREFLIGHT_HEADERS, "Origin": "http://localhost:5173"},
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_driver_itinerary_get_preflight_from_allowed_origin():
    app = create_app(
        Settings(database_url=None, cors_allowed_origins=[FRONTEND_ORIGIN])
    )
    headers = {
        **PREFLIGHT_HEADERS,
        "Access-Control-Request-Method": "GET",
    }
    with TestClient(app) as client:
        response = client.options("/conductor/itinerario", headers=headers)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN
    assert "GET" in response.headers["access-control-allow-methods"].split(", ")


def test_empty_origin_list_denies_cors_but_keeps_http_available():
    app = create_app(Settings(database_url=None))
    with TestClient(app) as client:
        preflight = client.options("/login", headers=PREFLIGHT_HEADERS)
        health = client.get("/health")

    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers
    assert health.status_code == 200


def test_login_post_preserves_cookie_and_credentialed_cors_headers():
    app = create_app(
        Settings(database_url=None, cors_allowed_origins=[FRONTEND_ORIGIN])
    )
    service = Mock()
    identity = Identidad(uuid4(), Rol.OPERADOR, "ACTIVO")
    service.login.return_value = LoginResult(
        "clear-session-token",
        uuid4(),
        identity,
        datetime.now(timezone.utc) + timedelta(minutes=60),
    )
    app.dependency_overrides[get_authentication_service] = lambda: service

    with TestClient(app) as client:
        response = client.post(
            "/login",
            json={"email": "user@example.test", "password": "secret"},
            headers={"Origin": FRONTEND_ORIGIN},
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    assert "Path=/" in response.headers["set-cookie"]
    service.login.assert_called_once_with("user@example.test", "secret")
