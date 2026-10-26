"""ECL-73 HTTP contracts with real RBAC and a mocked incident service."""

from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_session
from app.api.incidencias import get_incident_service
from app.core.config import Settings
from app.core.incidencias import PAGE_SIZE_MAX, EstadoIncidencia
from app.core.rbac import Identidad, Permiso, Rol
from app.main import create_app
from app.repositories.auditoria import Evento
from app.schemas.incidencia import (
    ConductorResumen,
    IncidenciaListItem,
    IncidenciaPage,
    IncidenciaRegistrada,
)
from app.services.autenticacion import AuthenticatedSession
from app.services.autorizacion import AutorizacionService
from app.services.incidencias import (
    LIMA,
    IncidenciaConflicto,
    IncidenciaInvalida,
    IncidenciaSinConductor,
    IncidenciaUnavailable,
)

OPERATION = uuid4()
NOTE = "Llanta pinchada en Av. Arequipa"
BODY = {
    "operation_id": str(OPERATION),
    "tipo": "AVERIA",
    "severidad": "ALTA",
    "ocurrida_en": "2026-10-27T09:15:00-05:00",
    "latitud": -12.0464,
    "longitud": -77.0428,
    "observacion": NOTE,
}
ACK = IncidenciaRegistrada(
    incidencia_id=uuid4(),
    operation_id=OPERATION,
    estado=EstadoIncidencia.PENDIENTE_VALIDACION,
    registrada_en=datetime(2026, 10, 27, 9, 16, 2, tzinfo=LIMA),
)


@contextmanager
def client_for(role):
    app = create_app(Settings(database_url=None))
    identity = Identidad(uuid4(), role, "ACTIVO")
    service = Mock()
    audit = Mock()
    app.dependency_overrides[get_current_session] = lambda: AuthenticatedSession(
        uuid4(), identity
    )
    app.dependency_overrides[get_incident_service] = lambda: service
    with TestClient(app) as client:
        app.state.authorization_service = AutorizacionService(audit)
        yield SimpleNamespace(
            client=client, service=service, audit=audit, identity=identity
        )


def decisions(audit):
    return [call.args[0] for call in audit.registrar.mock_calls]


# --- POST /conductor/incidencias -------------------------------------------------


def test_golden_driver_registers_incident_201():
    with client_for(Rol.CONDUCTOR) as ctx:
        ctx.service.registrar.return_value = (ACK, True)
        response = ctx.client.post("/conductor/incidencias", json=BODY)
    assert response.status_code == 201
    assert response.json() == {
        "incidencia_id": str(ACK.incidencia_id),
        "operation_id": str(OPERATION),
        "estado": "PENDIENTE_VALIDACION",
        "registrada_en": "2026-10-27T09:16:02-05:00",
    }
    usuario_id, payload = ctx.service.registrar.call_args.args
    assert usuario_id == ctx.identity.usuario_id
    assert payload.observacion == NOTE
    [decision] = decisions(ctx.audit)
    assert decision.evento is Evento.PERMITIDA
    assert decision.detalle.permiso is Permiso.INCIDENCIAS_CREAR


def test_happy_resend_same_operation_returns_200_with_same_body():
    with client_for(Rol.CONDUCTOR) as ctx:
        ctx.service.registrar.side_effect = [(ACK, True), (ACK, False)]
        first = ctx.client.post("/conductor/incidencias", json=BODY)
        second = ctx.client.post("/conductor/incidencias", json=BODY)
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json() == second.json()


@pytest.mark.parametrize("role", [Rol.ADMINISTRADOR, Rol.ANALISTA, Rol.AUDITOR])
def test_unhappy_roles_without_create_permission_get_403_and_denial_is_audited(role):
    with client_for(role) as ctx:
        response = ctx.client.post("/conductor/incidencias", json=BODY)
        ctx.service.registrar.assert_not_called()
    assert response.status_code == 403
    assert response.json() == {"detail": "Acceso denegado"}
    [decision] = decisions(ctx.audit)
    assert decision.evento is Evento.DENEGADA


def test_unhappy_operator_without_driver_profile_gets_403():
    with client_for(Rol.OPERADOR) as ctx:
        ctx.service.registrar.side_effect = IncidenciaSinConductor("private")
        response = ctx.client.post("/conductor/incidencias", json=BODY)
    assert response.status_code == 403
    assert response.json() == {"detail": "Acceso denegado"}


@pytest.mark.parametrize(
    "failure,status,detail",
    [
        (
            IncidenciaConflicto("private"),
            409,
            "El identificador de operación ya se usó con otros datos",
        ),
        (IncidenciaInvalida("private"), 422, "Datos de la incidencia inválidos"),
        (IncidenciaUnavailable("private"), 503, "Servicio no disponible"),
    ],
)
def test_service_errors_are_spanish_and_sanitized(failure, status, detail):
    with client_for(Rol.CONDUCTOR) as ctx:
        ctx.service.registrar.side_effect = failure
        response = ctx.client.post("/conductor/incidencias", json=BODY)
    assert response.status_code == status
    assert response.json() == {"detail": detail}
    assert "private" not in response.text and NOTE not in response.text


@pytest.mark.parametrize(
    "changes",
    [
        {"observacion": NOTE + "x" * 500},
        {"latitud": -91.5},
        {"ocurrida_en": "2026-10-27T09:15:00"},
        {"tipo": "INCENDIO-SECRETO"},
        {"conductor_id": "11111111-2222-3333-4444-555555555555"},
    ],
)
def test_edge_invalid_payload_422_without_echo(changes):
    body = {**BODY, **changes}
    with client_for(Rol.CONDUCTOR) as ctx:
        response = ctx.client.post("/conductor/incidencias", json=body)
        ctx.service.registrar.assert_not_called()
    assert response.status_code == 422
    for value in changes.values():
        assert str(value) not in response.text
    assert NOTE not in response.text
    assert {item["msg"] for item in response.json()["detail"]} == {"Entrada inválida"}


def test_missing_incident_service_fails_closed():
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    with pytest.raises(HTTPException) as error:
        get_incident_service(request)
    assert error.value.status_code == 503


# --- GET /incidencias ----------------------------------------------------------------


def page():
    return IncidenciaPage(
        items=[
            IncidenciaListItem(
                incidencia_id=uuid4(),
                tipo="AVERIA",
                severidad="ALTA",
                ocurrida_en=datetime(2026, 10, 27, 9, 15, tzinfo=LIMA),
                registrada_en=datetime(2026, 10, 27, 9, 16, 2, tzinfo=LIMA),
                conductor=ConductorResumen(conductor_id=uuid4(), nombre="Demo"),
                latitud=-12.0464,
                longitud=-77.0428,
                observacion=NOTE,
                estado="PENDIENTE_VALIDACION",
            )
        ],
        page=2,
        page_size=10,
        total=11,
    )


@pytest.mark.parametrize("role", [Rol.ADMINISTRADOR, Rol.OPERADOR])
def test_golden_admin_and_operator_list_pending_without_personal_data(role):
    with client_for(role) as ctx:
        ctx.service.listar.return_value = page()
        response = ctx.client.get("/incidencias", params={"page": 2, "page_size": 10})
    assert response.status_code == 200
    body = response.json()
    assert (body["page"], body["page_size"], body["total"]) == (2, 10, 11)
    [item] = body["items"]
    assert set(item) == {
        "incidencia_id",
        "tipo",
        "severidad",
        "ocurrida_en",
        "registrada_en",
        "conductor",
        "latitud",
        "longitud",
        "observacion",
        "estado",
    }
    assert set(item["conductor"]) == {"conductor_id", "nombre"}
    assert item["ocurrida_en"] == "2026-10-27T09:15:00-05:00"
    for private in ("dni", "telefono", "licencia"):
        assert private not in response.text
    ctx.service.listar.assert_called_once_with(
        EstadoIncidencia.PENDIENTE_VALIDACION, 2, 10
    )


@pytest.mark.parametrize("role", [Rol.ANALISTA, Rol.AUDITOR, Rol.CONDUCTOR])
def test_unhappy_other_roles_cannot_list_and_denial_is_audited(role):
    with client_for(role) as ctx:
        response = ctx.client.get("/incidencias")
        ctx.service.listar.assert_not_called()
    assert response.status_code == 403
    [decision] = decisions(ctx.audit)
    assert decision.evento is Evento.DENEGADA
    assert decision.detalle.permiso is Permiso.INCIDENCIAS_CONSULTAR


@pytest.mark.parametrize(
    "params",
    [
        {"page_size": PAGE_SIZE_MAX + 1},
        {"page_size": 0},
        {"page": 0},
        {"estado": "ABIERTA"},
    ],
)
def test_edge_invalid_query_is_422(params):
    with client_for(Rol.OPERADOR) as ctx:
        response = ctx.client.get("/incidencias", params=params)
        ctx.service.listar.assert_not_called()
    assert response.status_code == 422


def test_list_accepts_other_states_and_maximum_page_size():
    with client_for(Rol.ADMINISTRADOR) as ctx:
        ctx.service.listar.return_value = IncidenciaPage(
            items=[], page=1, page_size=PAGE_SIZE_MAX, total=0
        )
        response = ctx.client.get(
            "/incidencias", params={"estado": "VALIDADA", "page_size": PAGE_SIZE_MAX}
        )
    assert response.status_code == 200
    ctx.service.listar.assert_called_once_with(
        EstadoIncidencia.VALIDADA, 1, PAGE_SIZE_MAX
    )


def test_list_unavailable_is_sanitized():
    with client_for(Rol.OPERADOR) as ctx:
        ctx.service.listar.side_effect = IncidenciaUnavailable("private")
        response = ctx.client.get("/incidencias")
    assert response.status_code == 503
    assert response.json() == {"detail": "Servicio no disponible"}


def test_openapi_documents_the_contract():
    paths = create_app(Settings(database_url=None)).openapi()["paths"]
    post = paths["/conductor/incidencias"]["post"]["responses"]
    get = paths["/incidencias"]["get"]["responses"]
    assert {"200", "201", "401", "403", "409", "422", "503"} <= set(post)
    assert {"200", "401", "403", "422", "503"} <= set(get)


def test_created_at_is_reported_in_lima_time():
    assert ACK.registrada_en.astimezone(timezone.utc).hour == 14
