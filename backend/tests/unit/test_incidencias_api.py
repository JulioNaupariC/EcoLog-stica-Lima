"""ECL-73 HTTP contracts against the ECL-72 BDD, with real RBAC and a mocked service."""

from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.dependencies import get_authentication_service, get_current_session
from app.api.incidencias import get_incident_service
from app.core.config import Settings
from app.core.incidencias import PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX, EstadoIncidencia
from app.core.rbac import Identidad, Motivo, Permiso, Rol
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
    IncidenciaParadaAjena,
    IncidenciaSinConductor,
    IncidenciaUnavailable,
)

OPERATION = "2d7d7ad5-57e1-4b17-9c8d-5094a6fc7a01"
NOTE = "Llanta pinchada: reporte de prueba"
BODY = {
    "operation_id": OPERATION,
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


# --- POST /conductor/incidencias ------------------------------------------------


def test_I01_conductor_registra_incidencia_201():
    with client_for(Rol.CONDUCTOR) as ctx:
        ctx.service.registrar.return_value = (ACK, True)
        response = ctx.client.post("/conductor/incidencias", json=BODY)
    assert response.status_code == 201
    assert response.json() == {
        "incidencia_id": str(ACK.incidencia_id),
        "operation_id": OPERATION,
        "estado": "PENDIENTE_VALIDACION",
        "registrada_en": "2026-10-27T09:16:02-05:00",
    }
    usuario_id, payload = ctx.service.registrar.call_args.args
    assert usuario_id == ctx.identity.usuario_id
    assert payload.observacion == NOTE
    [decision] = decisions(ctx.audit)
    assert decision.evento is Evento.PERMITIDA
    assert decision.detalle.permiso is Permiso.INCIDENCIAS_CREAR


def test_I13_reenvio_equivalente_devuelve_200_con_la_misma_respuesta():
    with client_for(Rol.CONDUCTOR) as ctx:
        ctx.service.registrar.side_effect = [(ACK, True), (ACK, False)]
        first = ctx.client.post("/conductor/incidencias", json=BODY)
        reordered = dict(reversed(list(BODY.items())))
        second = ctx.client.post("/conductor/incidencias", json=reordered)
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json() == second.json()


@pytest.mark.parametrize("role", [Rol.ADMINISTRADOR, Rol.ANALISTA, Rol.AUDITOR])
def test_I08_rol_sin_permiso_de_crear_recibe_403_y_se_audita(role):
    with client_for(role) as ctx:
        response = ctx.client.post("/conductor/incidencias", json=BODY)
        ctx.service.registrar.assert_not_called()
    assert response.status_code == 403
    assert response.json() == {"detail": "Acceso denegado"}
    [decision] = decisions(ctx.audit)
    assert decision.evento is Evento.DENEGADA


def test_I08_operador_recibe_403_por_rol_sin_llegar_al_servicio():
    """The global matrix grants incidencias.crear to the Operador; this endpoint
    admits only the Conductor role, even if the service could register."""
    with client_for(Rol.OPERADOR) as ctx:
        ctx.service.registrar.return_value = (ACK, True)
        response = ctx.client.post("/conductor/incidencias", json=BODY)
        ctx.service.registrar.assert_not_called()
    assert response.status_code == 403
    assert response.json() == {"detail": "Acceso denegado"}
    [decision] = decisions(ctx.audit)
    assert decision.evento is Evento.DENEGADA
    assert decision.usuario_id == ctx.identity.usuario_id
    assert decision.detalle.permiso is Permiso.INCIDENCIAS_CREAR
    assert decision.detalle.motivo is Motivo.SIN_PERMISO


@pytest.mark.parametrize(
    "failure",
    [IncidenciaSinConductor("private"), IncidenciaParadaAjena("private")],
    ids=["I10-conductor-sin-perfil", "I10-parada-ajena"],
)
def test_I10_403_generico_sin_perfil_o_con_parada_ajena(failure):
    role = Rol.CONDUCTOR
    with client_for(role) as ctx:
        ctx.service.registrar.side_effect = failure
        response = ctx.client.post(
            "/conductor/incidencias", json={**BODY, "parada_id": str(uuid4())}
        )
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
        (IncidenciaUnavailable("private"), 503, "Servicio no disponible"),
    ],
    ids=["I11-409", "503"],
)
def test_errores_del_servicio_en_espanol_y_sin_eco(failure, status, detail):
    with client_for(Rol.CONDUCTOR) as ctx:
        ctx.service.registrar.side_effect = failure
        response = ctx.client.post("/conductor/incidencias", json=BODY)
    assert response.status_code == status
    assert response.json() == {"detail": detail}
    assert "private" not in response.text and NOTE not in response.text


@pytest.mark.parametrize(
    "field,code",
    [
        ("ocurrida_en", "fecha_futura_fuera_de_tolerancia"),
        ("parada_id", "parada_invalida"),
    ],
    ids=["I05-T0+5min+1s", "I07-parada-inexistente"],
)
def test_I05_I07_422_del_servicio_identifica_el_campo_sin_eco(field, code):
    sent = {**BODY, "ocurrida_en": "2026-10-27T09:21:03-05:00"}
    with client_for(Rol.CONDUCTOR) as ctx:
        ctx.service.registrar.side_effect = IncidenciaInvalida(field, code)
        response = ctx.client.post("/conductor/incidencias", json=sent)
    assert response.status_code == 422
    assert response.json() == {
        "detail": [{"loc": ["body", field], "type": code, "msg": "Entrada inválida"}]
    }
    assert "input" not in response.text
    assert "09:21:03" not in response.text and NOTE not in response.text


@pytest.mark.parametrize(
    "changes",
    [
        {"observacion": "ñ" * 501},
        {"latitud": "-12.0464"},
        {"longitud": True},
        {"ocurrida_en": "2026-10-27T09:15:00"},
        {"tipo": "DESVIO-SECRETO"},
        {"operation_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8"},
        {"conductor_id": "11111111-2222-4333-8444-555555555555"},
        {"estado": "VALIDADA-SECRETO"},
    ],
    ids=[
        "I06-observacion",
        "I07-latitud-cadena",
        "I07-longitud-booleano",
        "I05-sin-zona",
        "I07-tipo",
        "I07-uuid-v1",
        "I07-conductor_id",
        "I07-estado",
    ],
)
def test_I05_I06_I07_entrada_invalida_422_sin_eco(changes):
    with client_for(Rol.CONDUCTOR) as ctx:
        response = ctx.client.post("/conductor/incidencias", json={**BODY, **changes})
        ctx.service.registrar.assert_not_called()
    assert response.status_code == 422
    for value in changes.values():
        assert str(value) not in response.text
    assert NOTE not in response.text
    assert {item["msg"] for item in response.json()["detail"]} == {"Entrada inválida"}


def test_I10_sin_sesion_responde_401_en_ambos_endpoints():
    app = create_app(Settings(database_url=None))
    app.dependency_overrides[get_authentication_service] = lambda: Mock()
    with TestClient(app) as client:
        assert client.post("/conductor/incidencias", json=BODY).status_code == 401
        assert client.get("/incidencias").status_code == 401


def test_servicio_ausente_falla_cerrado():
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    with pytest.raises(HTTPException) as error:
        get_incident_service(request)
    assert error.value.status_code == 503


# --- GET /incidencias ------------------------------------------------------------


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
def test_I02_administrador_y_operador_listan_sin_datos_personales(role):
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


def test_I02_parametros_por_defecto():
    with client_for(Rol.OPERADOR) as ctx:
        ctx.service.listar.return_value = IncidenciaPage(
            items=[], page=1, page_size=PAGE_SIZE_DEFAULT, total=0
        )
        assert ctx.client.get("/incidencias").status_code == 200
    ctx.service.listar.assert_called_once_with(
        EstadoIncidencia.PENDIENTE_VALIDACION, 1, PAGE_SIZE_DEFAULT
    )


@pytest.mark.parametrize("role", [Rol.ANALISTA, Rol.AUDITOR, Rol.CONDUCTOR])
def test_I09_analista_auditor_y_conductor_reciben_403_sin_datos(role):
    with client_for(role) as ctx:
        response = ctx.client.get("/incidencias")
        ctx.service.listar.assert_not_called()
    assert response.status_code == 403
    assert response.json() == {"detail": "Acceso denegado"}
    [decision] = decisions(ctx.audit)
    assert decision.evento is Evento.DENEGADA
    assert decision.detalle.permiso is Permiso.INCIDENCIAS_CONSULTAR


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 0},
        {"page_size": PAGE_SIZE_MAX + 1},
        {"page": "uno"},
        {"page_size": "1.5"},
        {"estado": "VALIDADA"},
        {"estado": "DESCARTADA"},
        {"estado": "ABIERTA"},
    ],
)
def test_I15_paginacion_o_estado_invalidos_422_sin_elementos(params):
    with client_for(Rol.OPERADOR) as ctx:
        response = ctx.client.get("/incidencias", params=params)
        ctx.service.listar.assert_not_called()
    assert response.status_code == 422
    assert "items" not in response.text


def test_I15_page_size_maximo_es_valido():
    with client_for(Rol.ADMINISTRADOR) as ctx:
        ctx.service.listar.return_value = IncidenciaPage(
            items=[], page=9, page_size=PAGE_SIZE_MAX, total=3
        )
        response = ctx.client.get(
            "/incidencias", params={"page": 9, "page_size": PAGE_SIZE_MAX}
        )
    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": 9,
        "page_size": PAGE_SIZE_MAX,
        "total": 3,
    }


def test_listado_no_disponible_se_sanea():
    with client_for(Rol.OPERADOR) as ctx:
        ctx.service.listar.side_effect = IncidenciaUnavailable("private")
        response = ctx.client.get("/incidencias")
    assert response.status_code == 503
    assert response.json() == {"detail": "Servicio no disponible"}


def test_openapi_documenta_el_contrato():
    paths = create_app(Settings(database_url=None)).openapi()["paths"]
    post = paths["/conductor/incidencias"]["post"]["responses"]
    get = paths["/incidencias"]["get"]["responses"]
    assert {"200", "201", "401", "403", "409", "422", "503"} <= set(post)
    assert {"200", "401", "403", "422", "503"} <= set(get)
