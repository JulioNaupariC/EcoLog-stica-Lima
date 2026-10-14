"""ECL-25: indicadores agregados del Inicio (servicio, repositorio y API)."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, Mock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import OperationalError

from app.api.dependencies import (
    get_authenticated_session,
    get_authentication_service,
)
from app.api.indicadores import get_indicator_service
from app.core.config import Settings
from app.core.rbac import Identidad, Rol
from app.main import create_app
from app.repositories.indicadores import (
    IndicadoresRepository,
    IndicatorStorageError,
    OperationalCounts,
    aggregate_statements,
)
from app.services.autenticacion import AuthenticatedSession
from app.services.autorizacion import AutorizacionService
from app.services.indicadores import (
    VIGENCIA_SEGUNDOS,
    IndicadoresService,
    IndicatorsUnavailable,
)

LIMA = ZoneInfo("America/Lima")
NOW = datetime(2026, 10, 14, 9, 30, tzinfo=LIMA)


def counts(**changes):
    values = {
        "vehiculos_total": 50,
        "vehiculos_activos": 45,
        "capacidad_kg_activa": Decimal("76500.00"),
        "conductores_total": 200,
        "conductores_habilitados": 145,
        "pedidos": [
            ("PENDIENTE", "ECONOMICO", 9000),
            ("PENDIENTE", "ESTANDAR", 15000),
            ("PENDIENTE", "EXPRESS", 6000),
        ],
    }
    return OperationalCounts(**{**values, **changes})


def service_with(result=None, error=None, monkeypatch=None):
    repository = Mock()
    if error is not None:
        repository.operational_counts.side_effect = error
    else:
        repository.operational_counts.return_value = result
    monkeypatch.setattr(
        "app.services.indicadores.IndicadoresRepository", lambda _session: repository
    )
    return IndicadoresService(MagicMock(), clock=lambda: NOW), repository


def test_ruta_dorada_servicio_compone_agregados_sin_datos_personales(monkeypatch):
    service, repository = service_with(counts(), monkeypatch=monkeypatch)
    result = service.operational()
    repository.operational_counts.assert_called_once_with(NOW)
    assert result.generado_en == NOW
    assert result.vigencia_segundos == VIGENCIA_SEGUNDOS == 30
    assert result.vehiculos.model_dump() == {
        "total": 50,
        "activos": 45,
        "capacidad_kg_activa": Decimal("76500.00"),
    }
    assert result.conductores.model_dump() == {
        "total": 200,
        "habilitados_asignacion": 145,
        "no_habilitados": 55,
    }
    assert result.pedidos.total == 30000
    assert result.pedidos.por_estado == {"PENDIENTE": 30000}
    assert result.pedidos.por_prioridad == {
        "EXPRESS": 6000,
        "ESTANDAR": 15000,
        "ECONOMICO": 9000,
    }


def test_ruta_feliz_varios_estados_se_suman_por_estado_y_prioridad(monkeypatch):
    rows = [("ENTREGADO", "EXPRESS", 2), ("PENDIENTE", "EXPRESS", 3)]
    service, _ = service_with(counts(pedidos=rows), monkeypatch=monkeypatch)
    result = service.operational().pedidos
    assert result.total == 5
    assert result.por_estado == {"ENTREGADO": 2, "PENDIENTE": 3}
    assert result.por_prioridad == {"EXPRESS": 5, "ESTANDAR": 0, "ECONOMICO": 0}


@pytest.mark.parametrize(
    "error", [IndicatorStorageError("x"), OperationalError("sql", {}, Exception())]
)
def test_ruta_infeliz_fallo_de_almacenamiento_se_sanea(monkeypatch, error):
    service, _ = service_with(error=error, monkeypatch=monkeypatch)
    with pytest.raises(IndicatorsUnavailable) as raised:
        service.operational()
    assert raised.value.__cause__ is None and "sql" not in str(raised.value)


def test_ruta_de_borde_base_vacia_devuelve_ceros(monkeypatch):
    empty = counts(
        vehiculos_total=0,
        vehiculos_activos=0,
        capacidad_kg_activa=Decimal("0"),
        conductores_total=0,
        conductores_habilitados=0,
        pedidos=[],
    )
    service, _ = service_with(empty, monkeypatch=monkeypatch)
    result = service.operational()
    assert result.conductores.no_habilitados == 0
    assert result.pedidos.total == 0 and result.pedidos.por_estado == {}
    assert set(result.pedidos.por_prioridad.values()) == {0}


def test_repositorio_traduce_errores_sql():
    session = Mock()
    session.execute.side_effect = OperationalError("SELECT secreto", {}, Exception())
    with pytest.raises(IndicatorStorageError) as raised:
        IndicadoresRepository(session).operational_counts(NOW)
    assert "secreto" not in str(raised.value)


def test_consultas_agregadas_usan_filter_y_la_regla_de_elegibilidad():
    statements = aggregate_statements(NOW)
    assert set(statements) == {"vehiculos", "conductores", "pedidos"}
    compiled = {
        name: str(statement.compile(dialect=postgresql.dialect()))
        for name, statement in statements.items()
    }
    assert compiled["vehiculos"].count("FILTER (WHERE") == 2
    drivers = compiled["conductores"]
    for fragment in (
        "LEFT OUTER JOIN usuario",
        "usuario.rol",
        "usuario.estado",
        "conductor.licencia_vigente_hasta >=",
        "conductor.disponible_desde IS NOT NULL",
        "conductor.disponible_hasta >",
    ):
        assert fragment in drivers
    assert "GROUP BY pedido.estado, pedido.prioridad" in compiled["pedidos"]
    params = statements["conductores"].compile(dialect=postgresql.dialect()).params
    assert NOW.date() in params.values() and NOW in params.values()


def client_for(role=Rol.ADMINISTRADOR, service=None):
    app = create_app(Settings(database_url=None))
    authenticated = AuthenticatedSession(uuid4(), Identidad(uuid4(), role, "ACTIVO"))
    app.dependency_overrides[get_authenticated_session] = lambda: authenticated
    if service is not None:
        app.dependency_overrides[get_indicator_service] = lambda: service
    with TestClient(app) as client:
        app.state.authorization_service = AutorizacionService(Mock())
        yield client


@pytest.mark.parametrize(
    "role", [Rol.ADMINISTRADOR, Rol.OPERADOR, Rol.ANALISTA, Rol.AUDITOR]
)
def test_api_ruta_feliz_roles_con_alcance_general_y_cache_privada(role, monkeypatch):
    service, _ = service_with(counts(), monkeypatch=monkeypatch)
    for client in client_for(role, service):
        response = client.get("/indicadores/operacion")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "private, max-age=30"
        body = response.json()
        assert body["conductores"]["habilitados_asignacion"] == 145
        assert body["vehiculos"]["capacidad_kg_activa"] == "76500.00"


def test_api_ruta_infeliz_conductor_con_alcance_propio_recibe_403():
    service = Mock()
    for client in client_for(Rol.CONDUCTOR, service):
        response = client.get("/indicadores/operacion")
        assert response.status_code == 403
        assert response.json() == {"detail": "Acceso denegado"}
        service.operational.assert_not_called()


def test_api_ruta_infeliz_servicio_no_disponible_503_sin_cache():
    service = Mock()
    service.operational.side_effect = IndicatorsUnavailable("detalle interno")
    for client in client_for(service=service):
        response = client.get("/indicadores/operacion")
        assert response.status_code == 503
        assert response.json() == {"detail": "Servicio no disponible"}
        assert "private" not in response.headers.get("cache-control", "")


def test_api_ruta_infeliz_sin_base_configurada_503():
    for client in client_for():
        response = client.get("/indicadores/operacion")
        assert response.status_code == 503
        assert response.json() == {"detail": "Servicio no disponible"}


def test_api_ruta_infeliz_sin_sesion_401():
    app = create_app(Settings(database_url=None))
    service = Mock()
    app.dependency_overrides[get_authentication_service] = lambda: Mock()
    app.dependency_overrides[get_indicator_service] = lambda: service
    with TestClient(app) as client:
        response = client.get("/indicadores/operacion")
    assert response.status_code == 401
    assert response.json() == {"detail": "No autenticado"}
    service.operational.assert_not_called()


def test_openapi_documenta_el_endpoint_y_sus_respuestas():
    schema = create_app(Settings(database_url=None)).openapi()
    operation = schema["paths"]["/indicadores/operacion"]["get"]
    assert set(operation["responses"]) >= {"200", "401", "403", "503"}
    assert "30 s" in operation["description"]
    assert "IndicadoresOperacionResponse" in schema["components"]["schemas"]
