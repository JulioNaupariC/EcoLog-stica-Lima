from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_authenticated_session, get_authentication_service
from app.core.config import Settings
from app.core.rbac import Identidad, Rol
from app.main import create_app
from app.services.autenticacion import (
    AuthenticatedSession,
    AuthenticationUnavailable,
    InvalidCredentials,
    LoginResult,
)


@pytest.mark.parametrize(
    "environment,secure", [("development", False), ("production", True)]
)
def test_login_contract_and_cookie(environment, secure):
    settings = Settings(app_env=environment, database_url=None)
    app = create_app(settings)
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
            "/login", json={"email": "user@example.test", "password": "secret"}
        )
    assert response.status_code == 200
    assert response.json() == {
        "usuario_id": str(identity.usuario_id),
        "rol": "OPERADOR",
    }
    assert "clear-session-token" not in response.text
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert ("Secure" in cookie) is secure


def test_login_rejects_client_identity_fields():
    app = create_app(Settings(database_url=None))
    service = Mock()
    app.dependency_overrides[get_authentication_service] = lambda: service
    with TestClient(app) as client:
        response = client.post(
            "/login",
            json={"email": "a", "password": "p", "rol": "ADMINISTRADOR"},
        )
    assert response.status_code == 422
    service.login.assert_not_called()


@pytest.mark.parametrize(
    "private_detail", ["existing-user-argon-secret", "dummy-argon-secret"]
)
def test_operational_login_failure_has_no_cookie_or_secret(private_detail):
    app = create_app(Settings(database_url=None))
    service = Mock()
    service.login.side_effect = AuthenticationUnavailable(private_detail)
    app.dependency_overrides[get_authentication_service] = lambda: service
    with TestClient(app) as client:
        response = client.post("/login", json={"email": "a", "password": "p"})
    assert response.status_code == 503
    assert response.json() == {"detail": "Servicio no disponible"}
    assert "set-cookie" not in response.headers
    assert private_detail not in response.text


def test_credential_denials_share_one_response():
    app = create_app(Settings(database_url=None))
    service = Mock()
    service.login.side_effect = InvalidCredentials("private account state")
    app.dependency_overrides[get_authentication_service] = lambda: service
    with TestClient(app) as client:
        response = client.post("/login", json={"email": "a", "password": "p"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Credenciales inválidas"}
    assert "private" not in response.text
    assert "set-cookie" not in response.headers


def test_logout_revokes_current_session_and_clears_cookie():
    app = create_app(Settings(database_url=None))
    service = Mock()
    authenticated = AuthenticatedSession(
        uuid4(), Identidad(uuid4(), Rol.OPERADOR, "ACTIVO")
    )
    service.login.return_value = LoginResult(
        "current-token",
        authenticated.sesion_id,
        authenticated.identidad,
        datetime.now(timezone.utc) + timedelta(minutes=60),
    )
    app.dependency_overrides[get_authentication_service] = lambda: service
    app.dependency_overrides[get_authenticated_session] = lambda: authenticated
    with TestClient(app) as client:
        login_response = client.post(
            "/login", json={"email": "user@example.test", "password": "secret"}
        )
        assert login_response.status_code == 200
        assert client.cookies.get("ecologistica_session") == "current-token"
        response = client.post("/logout")
        assert client.cookies.get("ecologistica_session") is None
    assert response.status_code == 204
    service.logout.assert_called_once_with(authenticated)
    deletion = response.headers["set-cookie"]
    assert "ecologistica_session=" in deletion
    assert "Path=/" in deletion
    assert "HttpOnly" in deletion
    assert "SameSite=strict" in deletion
