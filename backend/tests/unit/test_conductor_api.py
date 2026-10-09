from contextlib import contextmanager
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from test_conductor_schemas import payload

from app.api.conductores import get_conductor_service
from app.api.dependencies import get_authenticated_session, get_authentication_service
from app.core.config import Settings
from app.core.rbac import Identidad, Rol
from app.main import create_app
from app.schemas.conductor import ConductorPage, ConductorResponse, ConductorSummary
from app.services.autenticacion import AuthenticatedSession
from app.services.autorizacion import AutorizacionService
from app.services.conductores import (
    ConductorConflict,
    ConductorInvalid,
    ConductorNotFound,
    ConductorUnavailable,
)


def row(owner):
    data = payload()
    data.pop("email")
    data.pop("password")
    data.update(
        conductor_id=uuid4(),
        usuario_id=owner,
        estado="ACTIVO",
        habilitado_asignacion=True,
    )
    return ConductorResponse.model_validate(data)


@contextmanager
def client_for(role=Rol.ADMINISTRADOR):
    app = create_app(
        Settings(database_url=None, cors_allowed_origins=["http://127.0.0.1:5173"])
    )
    identity = Identidad(uuid4(), role, "ACTIVO")
    service = Mock()
    audit = Mock()
    app.dependency_overrides[get_authenticated_session] = lambda: AuthenticatedSession(
        uuid4(), identity
    )
    app.dependency_overrides[get_conductor_service] = lambda: service
    with TestClient(app) as client:
        app.state.authorization_service = AutorizacionService(audit)
        yield client, service, identity, audit


@pytest.mark.parametrize("role", [Rol.ADMINISTRADOR, Rol.OPERADOR])
def test_authorized_contracts(role):
    with client_for(role) as (client, service, identity, _):
        driver = row(uuid4())
        service.create.return_value = ConductorSummary.model_validate(
            driver.model_dump()
        )
        service.get.return_value = driver
        service.update.return_value = driver
        service.list_page.return_value = ConductorPage(
            items=[], page=1, page_size=20, total=0
        )
        response = client.post("/conductores", json=payload())
        assert response.status_code == 201
        assert (
            not {"dni", "telefono", "licencia_numero", "password", "password_hash"}
            & response.json().keys()
        )
        assert client.get("/conductores").status_code == 200
        assert (
            client.get(f"/conductores/{driver.conductor_id}").json()["dni"]
            == driver.dni
        )
        assert (
            client.patch(
                f"/conductores/{driver.conductor_id}", json={"nombre": "Nuevo"}
            ).status_code
            == 200
        )
        assert service.create.call_args.args[0].nombre == "Rosa Prueba"
        assert service.create.call_args.args[0].email != str(identity.usuario_id)


@pytest.mark.parametrize("role", [Rol.CONDUCTOR, Rol.AUDITOR, Rol.ANALISTA])
@pytest.mark.parametrize("operation", ["post", "list", "patch"])
def test_forbidden_roles_do_not_reach_persistence(role, operation):
    with client_for(role) as (client, service, _, _):
        if operation == "post":
            response = client.post("/conductores", json=payload())
        elif operation == "list":
            response = client.get("/conductores")
        else:
            response = client.patch(f"/conductores/{uuid4()}", json={"nombre": "Nuevo"})
        assert response.status_code == 403
        assert not service.mock_calls


def test_driver_own_projection_and_foreign_denial_are_audited():
    with client_for(Rol.CONDUCTOR) as (client, service, identity, audit):
        own = row(identity.usuario_id)
        service.get.return_value = own
        response = client.get(f"/conductores/{own.conductor_id}")
        assert response.status_code == 200
        assert (
            not {"dni", "telefono", "licencia_numero", "punto_partida"}
            & response.json().keys()
        )
        other = row(uuid4())
        service.get.return_value = other
        response = client.get(f"/conductores/{other.conductor_id}")
        assert response.status_code == 403
        assert other.dni not in response.text
        assert audit.registrar.call_args.args[0].evento.value == "AUTORIZACION_DENEGADA"


@pytest.mark.parametrize("role", [Rol.AUDITOR, Rol.ANALISTA])
def test_detail_denies_unsupported_projections(role):
    with client_for(role) as (client, service, _, _):
        assert client.get(f"/conductores/{uuid4()}").status_code == 403
        service.get.assert_not_called()


@pytest.mark.parametrize(
    "error,code",
    [
        (ConductorNotFound(), 404),
        (ConductorConflict(), 409),
        (ConductorInvalid(), 422),
        (ConductorUnavailable("private SQL"), 503),
    ],
)
def test_sanitized_service_errors(error, code):
    with client_for() as (client, service, _, _):
        service.update.side_effect = error
        response = client.patch(f"/conductores/{uuid4()}", json={"nombre": "Nuevo"})
        assert response.status_code == code
        assert "private SQL" not in response.text


@pytest.mark.parametrize(
    "data",
    [
        payload(dni="invalid"),
        payload(disponible_desde=None),
        payload(password_hash="invalid-extra"),
        payload(disponible_hasta="2000-01-01T00:00:00Z"),
    ],
)
def test_validation_never_echoes_password_or_personal_data(data):
    with client_for() as (client, service, _, _):
        response = client.post("/conductores", json=data)
        assert response.status_code == 422
        assert data["password"] not in response.text
        assert data["telefono"] not in response.text
        assert "input" not in response.text
        service.create.assert_not_called()


@pytest.mark.parametrize("query", ["page=0", "page_size=101", "page_size=0"])
def test_invalid_pagination(query):
    with client_for() as (client, service, _, _):
        assert client.get("/conductores?" + query).status_code == 422
        service.list_page.assert_not_called()


def test_session_required_and_missing_database():
    app = create_app(Settings(database_url=None))
    app.dependency_overrides[get_authentication_service] = lambda: Mock()
    app.dependency_overrides[get_conductor_service] = lambda: Mock()
    with TestClient(app) as client:
        assert client.get("/conductores").status_code == 401
        with pytest.raises(HTTPException) as error:
            get_conductor_service(Mock(app=app))
        assert error.value.status_code == 503


def test_patch_preflight():
    with client_for() as (client, _, _, _):
        response = client.options(
            "/conductores/" + str(uuid4()),
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "PATCH",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-credentials"] == "true"


def test_openapi_documents_write_only_credentials_and_driver_routes():
    schema = create_app(Settings(database_url=None)).openapi()
    assert set(schema["paths"]["/conductores"]) == {"get", "post"}
    assert set(schema["paths"]["/conductores/{conductor_id}"]) == {"get", "patch"}
    properties = schema["components"]["schemas"]["ConductorCreate"]["properties"]
    assert properties["password"]["writeOnly"] is True
    assert "password_hash" not in properties
