"""ECL-77 HTTP contracts: user list, reset, mandatory change and secrecy."""

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.conductores import get_conductor_service
from app.api.dependencies import (
    PASSWORD_CHANGE_REQUIRED,
    get_authenticated_session,
    get_authentication_service,
    get_current_session,
)
from app.api.usuarios import get_password_reset_service
from app.api.vehiculos import get_vehicle_service
from app.core.config import Settings
from app.core.rbac import Identidad, Rol
from app.main import create_app
from app.repositories.auditoria import Evento
from app.repositories.usuarios import UserSummary
from app.services.autenticacion import AuthenticatedSession, LoginResult
from app.services.autorizacion import AuthorizationDenied, AutorizacionService
from app.services.restablecimiento import (
    AutoRestablecimiento,
    ContrasenaActualInvalida,
    ContrasenaNuevaInvalida,
    ContrasenaTemporal,
    PaginaUsuarios,
    RestablecimientoService,
    RestablecimientoUnavailable,
    UsuarioInactivo,
    UsuarioNoEncontrado,
)

TEMPORARY = "Synthetic16Chars"
EXPIRES = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def build(role=Rol.ADMINISTRADOR, *, must_change=False, service=None):
    app = create_app(Settings(database_url=None))
    authenticated = AuthenticatedSession(
        uuid4(), Identidad(uuid4(), role, "ACTIVO"), must_change
    )
    service = service or Mock()
    app.dependency_overrides[get_current_session] = lambda: authenticated
    app.dependency_overrides[get_password_reset_service] = lambda: service
    return app, authenticated, service


@contextmanager
def run(app):
    audit = Mock()
    with TestClient(app) as client:
        app.state.authorization_service = AutorizacionService(audit)
        yield client, audit


def test_list_users_is_paginated_and_never_exposes_credentials():
    app, _, service = build()
    summary = UserSummary(
        uuid4(), "operador.demo@example.test", "OPERADOR", "ACTIVO", True
    )
    service.listar.return_value = PaginaUsuarios([summary], 2, 10, 11)
    with run(app) as (client, _):
        response = client.get("/usuarios", params={"page": 2, "page_size": 10})
        assert response.status_code == 200
        assert response.json() == {
            "items": [
                {
                    "usuario_id": str(summary.usuario_id),
                    "email": "operador.demo@example.test",
                    "rol": "OPERADOR",
                    "estado": "ACTIVO",
                    "debe_cambiar_contrasena": True,
                }
            ],
            "page": 2,
            "page_size": 10,
            "total": 11,
        }
        assert "hash" not in response.text
        service.listar.assert_called_once_with(2, 10)
        assert client.get("/usuarios", params={"page_size": 101}).status_code == 422


@pytest.mark.parametrize("role,status", [(Rol.CONDUCTOR, 403), (Rol.ANALISTA, 403)])
def test_list_users_requires_consult_permission(role, status):
    app, _, service = build(role)
    with run(app) as (client, audit):
        assert client.get("/usuarios").status_code == status
        service.listar.assert_not_called()
        assert audit.registrar.call_args.args[0].evento is Evento.DENEGADA


def test_list_users_unavailable_is_sanitized():
    app, _, service = build()
    service.listar.side_effect = RestablecimientoUnavailable("private")
    with run(app) as (client, _):
        response = client.get("/usuarios")
        assert response.status_code == 503
        assert response.json() == {"detail": "Servicio no disponible"}


def test_golden_reset_returns_temporary_once_without_caching():
    app, authenticated, service = build()
    target = uuid4()
    service.restablecer.return_value = ContrasenaTemporal(TEMPORARY, EXPIRES)
    with run(app) as (client, _):
        response = client.post(f"/usuarios/{target}/restablecer-contrasena")
        assert response.status_code == 200
        assert response.json() == {
            "contrasena_temporal": TEMPORARY,
            "expira_en": "2026-10-26T12:00:00Z",
        }
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["pragma"] == "no-cache"
        service.restablecer.assert_called_once_with(authenticated.identidad, target)


@pytest.mark.parametrize(
    "failure,status,detail",
    [
        (AuthorizationDenied("private"), 403, "Acceso denegado"),
        (UsuarioNoEncontrado("private"), 404, "Usuario no encontrado"),
        (UsuarioInactivo("private"), 409, "El usuario está inactivo"),
        (
            AutoRestablecimiento("private"),
            409,
            "Usa el cambio de contraseña para tu propia cuenta",
        ),
        (RestablecimientoUnavailable("private"), 503, "Servicio no disponible"),
    ],
)
def test_reset_errors_are_spanish_and_sanitized(failure, status, detail):
    app, _, service = build()
    service.restablecer.side_effect = failure
    with run(app) as (client, _):
        response = client.post(f"/usuarios/{uuid4()}/restablecer-contrasena")
        assert response.status_code == status
        assert response.json() == {"detail": detail}
        assert "private" not in response.text


@pytest.mark.parametrize(
    "role", [Rol.OPERADOR, Rol.CONDUCTOR, Rol.ANALISTA, Rol.AUDITOR]
)
def test_unhappy_non_admin_reset_is_forbidden_and_audited(role):
    factory = MagicMock()
    app = create_app(Settings(database_url=None))
    authenticated = AuthenticatedSession(uuid4(), Identidad(uuid4(), role, "ACTIVO"))
    app.dependency_overrides[get_current_session] = lambda: authenticated
    audit = Mock()
    service = RestablecimientoService(factory, AutorizacionService(audit), Mock())
    app.dependency_overrides[get_password_reset_service] = lambda: service
    target = uuid4()
    with TestClient(app) as client:
        response = client.post(f"/usuarios/{target}/restablecer-contrasena")
    assert response.status_code == 403
    assert response.json() == {"detail": "Acceso denegado"}
    [registro] = [c.args[0] for c in audit.registrar.mock_calls]
    assert registro.evento is Evento.DENEGADA
    assert registro.usuario_id == authenticated.identidad.usuario_id
    assert registro.entidad_id == target
    factory.begin.assert_not_called()


def test_pending_change_blocks_every_other_authenticated_endpoint():
    app, _, service = build(must_change=True)
    other_services = {get_vehicle_service: Mock(), get_conductor_service: Mock()}
    for dependency, fake in other_services.items():
        app.dependency_overrides[dependency] = lambda fake=fake: fake
    with run(app) as (client, _):
        for method, path in (
            ("get", "/usuarios"),
            ("post", f"/usuarios/{uuid4()}/restablecer-contrasena"),
            ("get", "/vehiculos"),
            ("get", "/conductores"),
        ):
            response = getattr(client, method)(path)
            assert response.status_code == 403, path
            assert response.json() == {"detail": "Cambio de contraseña requerido"}
        service.listar.assert_not_called()
        service.restablecer.assert_not_called()
        for fake in other_services.values():
            assert fake.mock_calls == []


def test_pending_change_allows_change_and_logout():
    app, authenticated, service = build(Rol.OPERADOR, must_change=True)
    auth_service = Mock()
    app.dependency_overrides[get_authentication_service] = lambda: auth_service
    with run(app) as (client, _):
        response = client.post(
            "/cambiar-contrasena",
            json={
                "contrasena_actual": TEMPORARY,
                "contrasena_nueva": "definitive-pass-1",
            },
        )
        assert response.status_code == 204
        service.cambiar.assert_called_once_with(
            authenticated, TEMPORARY, "definitive-pass-1"
        )
        assert client.post("/logout").status_code == 204
        auth_service.logout.assert_called_once_with(authenticated)


@pytest.mark.parametrize(
    "body",
    [
        {"contrasena_actual": TEMPORARY, "contrasena_nueva": "short-11ch"},
        {"contrasena_actual": "", "contrasena_nueva": "definitive-pass-1"},
        {"contrasena_actual": TEMPORARY, "contrasena_nueva": "x" * 129},
        {
            "contrasena_actual": TEMPORARY,
            "contrasena_nueva": "definitive-pass-1",
            "rol": "ADMINISTRADOR",
        },
    ],
)
def test_change_validation_never_echoes_passwords(body, caplog):
    app, _, service = build()
    with run(app) as (client, _):
        caplog.set_level(logging.DEBUG)
        response = client.post("/cambiar-contrasena", json=body)
        assert response.status_code == 422
        for value in body.values():
            if value:
                assert value not in response.text
                assert value not in caplog.text
        assert {item["msg"] for item in response.json()["detail"]} == {
            "Entrada inválida"
        }
        service.cambiar.assert_not_called()


@pytest.mark.parametrize(
    "failure,status",
    [
        (ContrasenaNuevaInvalida("same"), 422),
        (ContrasenaActualInvalida("wrong"), 400),
        (RestablecimientoUnavailable("private"), 503),
    ],
)
def test_change_service_errors_are_sanitized(failure, status, caplog):
    app, _, service = build()
    service.cambiar.side_effect = failure
    with run(app) as (client, _):
        caplog.set_level(logging.DEBUG)
        body = {
            "contrasena_actual": "current-pass-1",
            "contrasena_nueva": "current-pass-1",
        }
        response = client.post("/cambiar-contrasena", json=body)
        assert response.status_code == status
        assert "current-pass-1" not in response.text
        assert "current-pass-1" not in caplog.text
        assert "private" not in response.text


def test_login_reports_pending_change():
    app = create_app(Settings(database_url=None))
    auth_service = Mock()
    auth_service.login.return_value = LoginResult(
        "private-token",
        uuid4(),
        Identidad(uuid4(), Rol.OPERADOR, "ACTIVO"),
        EXPIRES,
        True,
    )
    app.dependency_overrides[get_authentication_service] = lambda: auth_service
    with TestClient(app) as client:
        response = client.post(
            "/login", json={"email": "a@example.test", "password": TEMPORARY}
        )
    assert response.status_code == 200
    assert response.json()["debe_cambiar_contrasena"] is True
    assert TEMPORARY not in response.text


def test_session_gate_dependency():
    pending = AuthenticatedSession(
        uuid4(), Identidad(uuid4(), Rol.OPERADOR, "ACTIVO"), True
    )
    with pytest.raises(HTTPException) as error:
        get_authenticated_session(pending)
    assert error.value.status_code == 403
    assert error.value.detail == PASSWORD_CHANGE_REQUIRED
    normal = AuthenticatedSession(uuid4(), Identidad(uuid4(), Rol.OPERADOR, "ACTIVO"))
    assert get_authenticated_session(normal) is normal


def test_missing_reset_service_fails_closed():
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    with pytest.raises(HTTPException) as error:
        get_password_reset_service(request)
    assert error.value.status_code == 503


def test_lifespan_wires_reset_service_when_database_is_configured():
    app = create_app(
        Settings(database_url="postgresql+psycopg://user:pw@127.0.0.1:1/x_test")
    )
    with TestClient(app):
        assert isinstance(app.state.password_reset_service, RestablecimientoService)
