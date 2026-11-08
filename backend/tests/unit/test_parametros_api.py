"""EN-008 (ECL-26): versioned parameter API contract and RBAC."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_authenticated_session
from app.api.parametros import get_parameter_service
from app.core.config import Settings
from app.core.rbac import Identidad, Rol
from app.main import create_app
from app.repositories.auditoria import (
    DetalleParametrosVersionados,
    Evento,
    Registro,
)
from app.schemas.parametro import ValorParametro, VersionResponse
from app.services.autenticacion import AuthenticatedSession
from app.services.autorizacion import AutorizacionService
from app.services.parametros import (
    ParametrosConflicto,
    ParametrosNoEncontrados,
    ParametrosUnavailable,
)

DESDE = datetime(2026, 11, 1, 5, tzinfo=timezone.utc)


def respuesta():
    return VersionResponse(
        version="REFERENCIA-RN-2026-11",
        vigente_desde=DESDE,
        vigente_hasta=None,
        nota=None,
        valores=[
            ValorParametro(
                codigo="PRECIO_COMBUSTIBLE_GALON",
                valor=Decimal("17.50"),
                unidad="PEN/gal",
                fuente="RN-011",
            )
        ],
    )


def payload(**cambios):
    valores = [
        {
            "codigo": "PRECIO_COMBUSTIBLE_GALON",
            "valor": "17.50",
            "unidad": "PEN/gal",
            "fuente": "RN-011",
        },
        {
            "codigo": "LITROS_POR_GALON",
            "valor": "3.785411784",
            "unidad": "L/gal",
            "fuente": "NIST HB44",
        },
        {
            "codigo": "COSTO_MANTENIMIENTO_KM",
            "valor": "1.20",
            "unidad": "PEN/km",
            "fuente": "RN-012",
        },
    ]
    return {
        "version": "V2026-11-08",
        "vigente_desde": "2026-11-08T00:00:00-05:00",
        "valores": valores,
        **cambios,
    }


def client_for(role):
    app = create_app(Settings(database_url=None))
    identity = Identidad(uuid4(), role, "ACTIVO")
    service = Mock()
    service.vigente.return_value = respuesta()
    service.por_version.return_value = respuesta()
    service.registrar.return_value = respuesta()
    app.dependency_overrides[get_authenticated_session] = lambda: AuthenticatedSession(
        uuid4(), identity
    )
    app.dependency_overrides[get_parameter_service] = lambda: service
    with TestClient(app) as client:
        app.state.authorization_service = AutorizacionService(Mock())
        yield client, service, identity


@pytest.mark.parametrize(
    "role", [Rol.ADMINISTRADOR, Rol.OPERADOR, Rol.ANALISTA, Rol.AUDITOR]
)
def test_roles_with_the_permission_consult(role):
    for client, service, _ in client_for(role):
        assert client.get("/parametros").status_code == 200
        service.vigente.assert_called_once_with(None)
        body = client.get("/parametros/REFERENCIA-RN-2026-11").json()
        assert body["version"] == "REFERENCIA-RN-2026-11"
        assert body["valores"][0]["unidad"] == "PEN/gal"


@pytest.mark.parametrize("role", [Rol.CONDUCTOR])
def test_driver_cannot_consult(role):
    """Current matrix: the driver has no parameters.consultar."""
    for client, service, _ in client_for(role):
        assert client.get("/parametros").status_code == 403
        service.vigente.assert_not_called()


def test_consult_at_a_date_requires_an_offset():
    for client, service, _ in client_for(Rol.OPERADOR):
        response = client.get("/parametros?fecha=2026-11-05T10:00:00-05:00")
        assert response.status_code == 200
        assert service.vigente.call_args.args[0].utcoffset() is not None
        assert client.get("/parametros?fecha=2026-11-05T10:00:00").status_code == 422


def test_only_admin_registers_a_version():
    for client, service, identity in client_for(Rol.ADMINISTRADOR):
        response = client.post("/parametros", json=payload())
        assert response.status_code == 201
        creado, actor = service.registrar.call_args.args
        assert actor == identity.usuario_id
        assert {v.codigo for v in creado.valores} == {
            "PRECIO_COMBUSTIBLE_GALON",
            "LITROS_POR_GALON",
            "COSTO_MANTENIMIENTO_KM",
        }
    for role in (Rol.OPERADOR, Rol.ANALISTA, Rol.AUDITOR, Rol.CONDUCTOR):
        for client, service, _ in client_for(role):
            assert client.post("/parametros", json=payload()).status_code == 403
            service.registrar.assert_not_called()


def _sin(codigo):
    datos = payload()
    datos["valores"] = [v for v in datos["valores"] if v["codigo"] != codigo]
    return datos


def _cambiar(indice, **campos):
    datos = payload()
    datos["valores"][indice] = {**datos["valores"][indice], **campos}
    return datos


@pytest.mark.parametrize(
    "cuerpo",
    [
        _sin("LITROS_POR_GALON"),
        _cambiar(0, unidad="PEN/L"),
        _cambiar(1, valor="0"),
        _cambiar(1, valor="-3.78"),
        _cambiar(2, fuente="   "),
        _cambiar(2, codigo="PRECIO_COMBUSTIBLE_GALON", unidad="PEN/gal"),
        _cambiar(0, codigo="FACTOR_INVENTADO"),
        payload(version="v minúscula"),
        payload(vigente_desde="2026-11-08T00:00:00"),
        payload(extra=True),
    ],
)
def test_incomplete_or_inconsistent_sets_are_rejected(cuerpo):
    for client, service, _ in client_for(Rol.ADMINISTRADOR):
        assert client.post("/parametros", json=cuerpo).status_code == 422
        service.registrar.assert_not_called()


@pytest.mark.parametrize(
    "error,status",
    [
        (ParametrosNoEncontrados(), 404),
        (ParametrosConflicto(), 409),
        (ParametrosUnavailable("private SQL"), 503),
    ],
)
def test_service_errors_are_translated_and_sanitized(error, status):
    for client, service, _ in client_for(Rol.ADMINISTRADOR):
        service.vigente.side_effect = error
        service.registrar.side_effect = error
        assert client.get("/parametros").status_code == status
        response = client.post("/parametros", json=payload())
        assert response.status_code == status
        assert "private SQL" not in response.text


def test_parameter_audit_event_is_strict():
    detalle = DetalleParametrosVersionados(
        codigos=("COSTO_MANTENIMIENTO_KM",), cierra_version_anterior=False
    )
    Registro(
        usuario_id=uuid4(),
        entidad_id=uuid4(),
        evento=Evento.PARAMETROS_VERSIONADOS,
        detalle=detalle,
    )
    with pytest.raises(ValueError):
        Registro(
            usuario_id=None,
            entidad_id=uuid4(),
            evento=Evento.PARAMETROS_VERSIONADOS,
            detalle=detalle,
        )
    with pytest.raises(ValueError):
        DetalleParametrosVersionados(
            codigos=("LITROS_POR_GALON", "LITROS_POR_GALON"),
            cierra_version_anterior=True,
        )
