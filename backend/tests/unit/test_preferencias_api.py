from contextlib import contextmanager
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_authenticated_session, get_authentication_service
from app.api.preferencias import get_preferencias_service
from app.core.config import Settings
from app.core.rbac import Identidad, Rol
from app.main import create_app
from app.schemas.preferencias import PreferenciasResponse
from app.services.autenticacion import AuthenticatedSession
from app.services.autorizacion import AutorizacionService
from app.services.preferencias import PreferenciasNotFound, PreferenciasUnavailable


@contextmanager
def client_for(role=Rol.OPERADOR):
    app = create_app(Settings(database_url=None))
    service = Mock()
    identity = Identidad(uuid4(), role, "ACTIVO")
    app.dependency_overrides[get_authenticated_session] = lambda: AuthenticatedSession(
        uuid4(), identity
    )
    app.dependency_overrides[get_preferencias_service] = lambda: service
    with TestClient(app) as client:
        app.state.authorization_service = AutorizacionService(Mock())
        yield client, service


@pytest.mark.parametrize("role", list(Rol))
@pytest.mark.parametrize("method", ["get", "patch"])
def test_permissions_and_target_binding(role, method):
    identifier = uuid4()
    response = PreferenciasResponse(
        cliente_id=identifier,
        horario_preferido=None,
        referencia="Entrada",
        restriccion_acceso=None,
    )
    with client_for(role) as (client, service):
        service.get.return_value = response
        service.update.return_value = response
        kwargs = {"json": {"referencia": "Entrada"}} if method == "patch" else {}
        result = getattr(client, method)(
            f"/clientes/{identifier}/preferencias", **kwargs
        )
        if role in {Rol.ADMINISTRADOR, Rol.OPERADOR}:
            assert result.status_code == 200 and result.json()["cliente_id"] == str(
                identifier
            )
            assert result.headers["cache-control"] == "no-store"
            action = service.update if method == "patch" else service.get
            assert action.call_args.args[0] == identifier
        else:
            assert result.status_code == 403
            service.get.assert_not_called()
            service.update.assert_not_called()


@pytest.mark.parametrize(
    "error,status",
    [(PreferenciasNotFound("private"), 404), (PreferenciasUnavailable("private"), 503)],
)
@pytest.mark.parametrize("method", ["get", "patch"])
def test_safe_service_errors(error, status, method):
    with client_for() as (client, service):
        service.get.side_effect = error
        service.update.side_effect = error
        kwargs = {"json": {"referencia": "Entrada"}} if method == "patch" else {}
        result = getattr(client, method)(f"/clientes/{uuid4()}/preferencias", **kwargs)
        assert result.status_code == status and "private" not in result.text


def test_invalid_inputs_do_not_reach_service_or_echo_data():
    with client_for() as (client, service):
        url = f"/clientes/{uuid4()}/preferencias"
        for data in (
            {},
            {"referencia": " "},
            {"referencia": "sensitive" * 40},
            {"referencia": "Entrada", "password": "private-password"},
        ):
            result = client.patch(url, json=data)
            assert result.status_code == 422
            assert "input" not in result.text and "private-password" not in result.text
        assert client.get("/clientes/invalid-id/preferencias").status_code == 422
        service.update.assert_not_called()
        service.get.assert_not_called()


@pytest.mark.parametrize("method", ["get", "patch"])
def test_unauthenticated_rejected(method):
    app = create_app(Settings(database_url=None))
    app.dependency_overrides[get_authentication_service] = lambda: Mock()
    with TestClient(app) as client:
        kwargs = {"json": {"referencia": "Entrada"}} if method == "patch" else {}
        assert (
            getattr(client, method)(
                f"/clientes/{uuid4()}/preferencias", **kwargs
            ).status_code
            == 401
        )


def test_service_unconfigured_and_openapi():
    app = create_app(Settings(database_url=None))
    identity = Identidad(uuid4(), Rol.OPERADOR, "ACTIVO")
    app.dependency_overrides[get_authenticated_session] = lambda: AuthenticatedSession(
        uuid4(), identity
    )
    with TestClient(app) as client:
        app.state.authorization_service = AutorizacionService(Mock())
        assert client.get(f"/clientes/{uuid4()}/preferencias").status_code == 503
        path = client.get("/openapi.json").json()["paths"][
            "/clientes/{cliente_id}/preferencias"
        ]
        assert {"get", "patch"} <= set(path)
