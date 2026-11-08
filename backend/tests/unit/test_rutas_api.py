"""ECL-94 (ST-045) / ECL-96 (ST-047): route API contract and real RBAC.

The optimization service is replaced by a fake that serves the published
fixtures, so these tests pin the HTTP contract; the real service is covered by
test_optimizaciones_service.py and the PostGIS integration tests.
"""

import json
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_session
from app.api.rutas import get_closure_service, get_optimization_service
from app.core.config import Settings
from app.core.rbac import Identidad, Rol
from app.main import create_app
from app.schemas.rutas import (
    EstadoOptimizacion,
    IndicadoresSostenibilidad,
    OptimizacionDetalle,
    OptimizacionSolicitud,
    ParadaActualizada,
    RutaCerrada,
)
from app.services import rutas_simuladas
from app.services.autenticacion import AuthenticatedSession
from app.services.autorizacion import AutorizacionService
from app.services.cierre_rutas import (
    CierreConflicto,
    CierreUnavailable,
    IndicadoresIncompletos,
    ResultadoInvalido,
    RutaNoEncontrada,
)
from app.services.optimizaciones import (
    OptimizacionFallida,
    OptimizacionUnavailable,
    SeleccionInvalida,
)

FIXTURES = rutas_simuladas.FIXTURES
FRONTEND = Path(__file__).resolve().parents[3] / "frontend/src/test/fixtures/rutas"
FECHA = "2026-11-20"


class FakeOptimizador(rutas_simuladas.RutasSimuladasService):
    """Serves the fixtures; ``optimizar`` answers like a completed real run."""

    def __init__(self):
        self.error = None
        self.llamadas = []

    def optimizar(self, solicitud, actor):
        self.llamadas.append((solicitud, actor))
        if self.error is not None:
            raise self.error
        aceptada = self.solicitar(solicitud)
        return aceptada.model_copy(
            update={"estado": EstadoOptimizacion.COMPLETADA, "simulado": False}
        )


@contextmanager
def client_for(role, servicio=None):
    app = create_app(Settings(database_url=None))
    identity = Identidad(uuid4(), role, "ACTIVO")
    app.dependency_overrides[get_current_session] = lambda: AuthenticatedSession(
        uuid4(), identity
    )
    optimizador = servicio or FakeOptimizador()
    app.dependency_overrides[get_optimization_service] = lambda: optimizador
    # ECL-119: closures and the dashboard; the fake serves the ST-045 fixtures.
    cierres = Mock()
    cierres.indicadores.side_effect = (
        rutas_simuladas.RutasSimuladasService().sostenibilidad
    )
    app.dependency_overrides[get_closure_service] = lambda: cierres
    with TestClient(app) as client:
        app.state.authorization_service = AutorizacionService(Mock())
        yield SimpleNamespace(
            client=client, servicio=optimizador, identity=identity, cierres=cierres
        )


def ids() -> dict[EstadoOptimizacion, str]:
    return {
        d.estado: str(d.optimizacion_id) for d in rutas_simuladas.detalles().values()
    }


# --- fixtures ------------------------------------------------------------------


def test_fixtures_validate_against_the_published_schemas():
    detalles = rutas_simuladas.detalles()
    assert {d.estado for d in detalles.values()} == set(EstadoOptimizacion)
    completada = rutas_simuladas.completada()
    assert len(completada.rutas) == 3 and len(completada.no_asignados) == 2
    assert completada.resumen is not None
    assert completada.resumen.rutas == len(completada.rutas)
    asignados = sum(len(r.paradas) for r in completada.rutas)
    assert completada.resumen.pedidos_asignados == asignados
    for ruta in completada.rutas:
        assert [p.secuencia for p in ruta.paradas] == list(
            range(1, len(ruta.paradas) + 1)
        )
        for parada in ruta.paradas:
            assert parada.ventana_inicio <= parada.eta <= parada.ventana_fin
        assert ruta.trazado.coordinates[0] == ruta.trazado.coordinates[-1]  # depósito
    sin_datos = IndicadoresSostenibilidad.model_validate_json(
        (FIXTURES / "sostenibilidad-sin-datos.json").read_text(encoding="utf-8")
    )
    assert sin_datos.con_datos is False and sin_datos.distancia_km is None


def test_service_outputs_match_the_published_examples():
    servicio = rutas_simuladas.RutasSimuladasService()
    aceptada = json.loads(
        (FIXTURES / "optimizacion-aceptada.json").read_text(encoding="utf-8")
    )
    pagina = json.loads(
        (FIXTURES / "optimizaciones-pagina.json").read_text(encoding="utf-8")
    )
    solicitud = OptimizacionSolicitud(fecha_operacion=FECHA)
    assert servicio.solicitar(solicitud).model_dump(mode="json") == aceptada
    assert servicio.listar(None, 1, 20).model_dump(mode="json") == pagina


@pytest.mark.skipif(not FRONTEND.is_dir(), reason="frontend no disponible")
def test_frontend_fixtures_are_identical_to_the_backend_ones():
    backend = {p.name: p.read_bytes() for p in FIXTURES.glob("*.json")}
    frontend = {p.name: p.read_bytes() for p in FRONTEND.glob("*.json")}
    assert frontend == backend


# --- POST /optimizaciones ------------------------------------------------------


def test_operator_requests_an_optimization():
    with client_for(Rol.OPERADOR) as ctx:
        response = ctx.client.post("/optimizaciones", json={"fecha_operacion": FECHA})
    assert response.status_code == 201
    body = response.json()
    assert body["estado"] == "COMPLETADA" and body["simulado"] is False
    assert body["optimizacion_id"] == ids()[EstadoOptimizacion.COMPLETADA]
    assert "X-Datos-Simulados" not in response.headers
    assert response.headers["Cache-Control"] == "no-store"
    solicitud, actor = ctx.servicio.llamadas[0]
    assert actor == ctx.identity.usuario_id  # never taken from the payload
    assert str(solicitud.fecha_operacion) == FECHA


def test_unusable_selection_is_422_with_field_and_reason_only():
    servicio = FakeOptimizador()
    servicio.error = SeleccionInvalida("vehiculo_ids", "No hay vehículos ACTIVO")
    secreto = str(uuid4())
    with client_for(Rol.OPERADOR, servicio) as ctx:
        response = ctx.client.post(
            "/optimizaciones",
            json={"fecha_operacion": FECHA, "vehiculo_ids": [secreto]},
        )
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "campo": "vehiculo_ids",
        "motivo": "No hay vehículos ACTIVO",
    }
    assert secreto not in response.text


def test_failed_calculation_is_503_with_the_run_to_consult():
    servicio = FakeOptimizador()
    run = uuid4()
    servicio.error = OptimizacionFallida(run)
    with client_for(Rol.OPERADOR, servicio) as ctx:
        response = ctx.client.post("/optimizaciones", json={"fecha_operacion": FECHA})
    assert response.status_code == 503
    assert response.json()["detail"] == {
        "optimizacion_id": str(run),
        "estado": "FALLIDA",
        "motivo": "No se pudo calcular la solución de rutas",
    }


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("post", "/optimizaciones"),
        ("get", "/optimizaciones"),
        ("get", f"/optimizaciones/{uuid4()}"),
    ],
)
def test_storage_outage_is_a_sanitized_503(metodo, ruta):
    class Caido(FakeOptimizador):
        def optimizar(self, solicitud, actor):
            raise OptimizacionUnavailable("private detail")

        def listar(self, *args):
            raise OptimizacionUnavailable("private detail")

        def detalle(self, *args):
            raise OptimizacionUnavailable("private detail")

    with client_for(Rol.OPERADOR, Caido()) as ctx:
        response = getattr(ctx.client, metodo)(
            ruta, **({"json": {"fecha_operacion": FECHA}} if metodo == "post" else {})
        )
    assert response.status_code == 503
    assert response.json() == {"detail": "Servicio no disponible"}


def test_without_database_the_optimizer_is_unavailable():
    app = create_app(Settings(database_url=None))
    identity = Identidad(uuid4(), Rol.OPERADOR, "ACTIVO")
    app.dependency_overrides[get_current_session] = lambda: AuthenticatedSession(
        uuid4(), identity
    )
    with TestClient(app) as client:
        app.state.authorization_service = AutorizacionService(Mock())
        response = client.get("/optimizaciones")
    assert response.status_code == 503


def test_real_service_is_built_from_the_app_settings():
    from app.api.rutas import get_optimization_service as construir

    settings = Settings(
        database_url=None, deposito_latitud=-12.05, optimizacion_tiempo_limite_s=7
    )
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(session_factory=Mock(), settings=settings)
        )
    )
    service = construir(request)
    assert service._deposito.latitud == -12.05
    assert service._configuracion.tiempo_limite_s == 7


@pytest.mark.parametrize(
    "role", [Rol.ADMINISTRADOR, Rol.ANALISTA, Rol.AUDITOR, Rol.CONDUCTOR]
)
def test_only_the_operator_can_request_an_optimization(role):
    with client_for(role) as ctx:
        response = ctx.client.post("/optimizaciones", json={"fecha_operacion": FECHA})
    assert response.status_code == 403


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"fecha_operacion": "no-es-fecha"},
        {"fecha_operacion": FECHA, "estado": "COMPLETADA"},
        {"fecha_operacion": FECHA, "pedido_ids": []},
        {"fecha_operacion": FECHA, "pedido_ids": [str(uuid4())] * 2},
        {"fecha_operacion": FECHA, "vehiculo_ids": [str(uuid4()) for _ in range(16)]},
    ],
)
def test_invalid_requests_are_422_without_echoing_input(body):
    with client_for(Rol.OPERADOR) as ctx:
        response = ctx.client.post("/optimizaciones", json=body)
    assert response.status_code == 422
    assert "no-es-fecha" not in response.text and "input" not in response.text


def test_request_limits_follow_rnf001():
    OptimizacionSolicitud(
        fecha_operacion=FECHA,
        pedido_ids=[uuid4() for _ in range(150)],
        vehiculo_ids=[uuid4() for _ in range(15)],
    )
    with pytest.raises(ValueError):
        OptimizacionSolicitud(
            fecha_operacion=FECHA, pedido_ids=[uuid4() for _ in range(151)]
        )


# --- GET /optimizaciones -------------------------------------------------------


@pytest.mark.parametrize(
    "role", [Rol.ADMINISTRADOR, Rol.OPERADOR, Rol.ANALISTA, Rol.AUDITOR]
)
def test_list_is_available_to_general_consultation_roles(role):
    with client_for(role) as ctx:
        response = ctx.client.get("/optimizaciones")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3 and body["simulado"] is True
    fechas = [item["solicitada_en"] for item in body["items"]]
    assert fechas == sorted(fechas, reverse=True)
    assert "rutas" not in body["items"][0]  # no stops nor driver names


def test_list_filters_by_date_and_paginates():
    with client_for(Rol.OPERADOR) as ctx:
        vacia = ctx.client.get("/optimizaciones", params={"fecha": "2020-01-01"})
        pagina = ctx.client.get("/optimizaciones", params={"page": 2, "page_size": 2})
        invalida = ctx.client.get("/optimizaciones", params={"page_size": 101})
    assert vacia.json()["items"] == [] and vacia.json()["total"] == 0
    assert len(pagina.json()["items"]) == 1 and pagina.json()["page"] == 2
    assert invalida.status_code == 422


def test_driver_cannot_list_optimizations():
    with client_for(Rol.CONDUCTOR) as ctx:
        assert ctx.client.get("/optimizaciones").status_code == 403


# --- GET /optimizaciones/{id} --------------------------------------------------


@pytest.mark.parametrize("role", [Rol.ADMINISTRADOR, Rol.OPERADOR])
def test_detail_returns_routes_stops_and_unassigned(role):
    with client_for(role) as ctx:
        response = ctx.client.get(
            f"/optimizaciones/{ids()[EstadoOptimizacion.COMPLETADA]}"
        )
    assert response.status_code == 200
    detalle = OptimizacionDetalle.model_validate(response.json())
    assert detalle.simulado is True and detalle.resumen is not None
    assert {n.motivo.value for n in detalle.no_asignados} == {
        "EXCEDE_CAPACIDAD",
        "VENTANA_INVIABLE",
    }
    assert "dni" not in response.text.lower() and "telefono" not in response.text


def test_in_progress_and_failed_examples():
    with client_for(Rol.OPERADOR) as ctx:
        proceso = ctx.client.get(
            f"/optimizaciones/{ids()[EstadoOptimizacion.EN_PROCESO]}"
        ).json()
        fallida = ctx.client.get(
            f"/optimizaciones/{ids()[EstadoOptimizacion.FALLIDA]}"
        ).json()
    assert proceso["rutas"] == [] and proceso["resumen"] is None
    assert fallida["error"] and fallida["rutas"] == []


@pytest.mark.parametrize("role", [Rol.ANALISTA, Rol.AUDITOR, Rol.CONDUCTOR])
def test_detail_with_personal_data_is_403_for_other_roles(role):
    with client_for(role) as ctx:
        response = ctx.client.get(
            f"/optimizaciones/{ids()[EstadoOptimizacion.COMPLETADA]}"
        )
    assert response.status_code == 403


def test_unknown_or_malformed_id():
    with client_for(Rol.OPERADOR) as ctx:
        assert ctx.client.get(f"/optimizaciones/{uuid4()}").status_code == 404
        malformado = ctx.client.get("/optimizaciones/no-es-uuid")
    assert malformado.status_code == 422 and "no-es-uuid" not in malformado.text


# --- GET /indicadores/sostenibilidad -------------------------------------------


@pytest.mark.parametrize(
    "role", [Rol.ADMINISTRADOR, Rol.OPERADOR, Rol.ANALISTA, Rol.AUDITOR]
)
def test_dashboard_with_data_keeps_the_requested_period(role):
    with client_for(role) as ctx:
        response = ctx.client.get(
            "/indicadores/sostenibilidad",
            params={"desde": "2026-11-01", "hasta": "2026-11-30"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["con_datos"] is True and body["simulado"] is True
    assert body["periodo"] == {"desde": "2026-11-01", "hasta": "2026-11-30"}
    assert body["co2_kg"] > 0 and body["parametros_versiones"]


def test_dashboard_without_closed_routes_returns_nulls_not_zeros():
    with client_for(Rol.ANALISTA) as ctx:
        body = ctx.client.get(
            "/indicadores/sostenibilidad",
            params={"desde": "2025-01-01", "hasta": "2025-01-31"},
        ).json()
    assert body["con_datos"] is False and body["rutas_cerradas"] == 0
    assert body["distancia_km"] is None and body["ahorro_vs_secuencial"] is None


def test_dashboard_rejects_an_inverted_or_missing_period():
    with client_for(Rol.ANALISTA) as ctx:
        invertido = ctx.client.get(
            "/indicadores/sostenibilidad",
            params={"desde": "2026-11-30", "hasta": "2026-11-01"},
        )
        faltante = ctx.client.get("/indicadores/sostenibilidad")
    assert invertido.status_code == 422 and faltante.status_code == 422


def test_driver_cannot_open_the_dashboard():
    with client_for(Rol.CONDUCTOR) as ctx:
        response = ctx.client.get(
            "/indicadores/sostenibilidad",
            params={"desde": "2026-11-01", "hasta": "2026-11-30"},
        )
    assert response.status_code == 403


def test_without_data_the_schema_rejects_values_and_vice_versa():
    base = json.loads(
        (FIXTURES / "sostenibilidad-con-datos.json").read_text(encoding="utf-8")
    )
    with pytest.raises(ValueError):
        IndicadoresSostenibilidad.model_validate({**base, "co2_kg": None})
    with pytest.raises(ValueError):
        IndicadoresSostenibilidad.model_validate({**base, "con_datos": False})


# --- OpenAPI -------------------------------------------------------------------


def test_openapi_documents_the_contract():
    app = create_app(Settings(database_url=None))
    paths = app.openapi()["paths"]
    assert {"post", "get"} <= set(paths["/optimizaciones"])
    detalle = paths["/optimizaciones/{optimizacion_id}"]["get"]["responses"]
    assert {"200", "401", "403", "404", "422"} <= set(detalle)
    assert "/indicadores/sostenibilidad" in paths


def _resumen_completado() -> dict:
    data = json.loads((FIXTURES / "optimizacion-completada.json").read_text("utf-8"))
    return data["resumen"]


def test_zero_baseline_savings_are_null_not_zero():
    """BDD US-006 v1.0.0 (R10, decisión 4): base 0 -> null, nunca 0 %."""
    from app.schemas.rutas import Resumen

    resumen = _resumen_completado()
    resumen["secuencial"]["costo_soles"] = 0
    resumen["optimizada"]["costo_soles"] = 0
    resumen["ahorro_pct"]["costo"] = None
    assert Resumen.model_validate(resumen).ahorro_pct.costo is None
    resumen["ahorro_pct"]["costo"] = 0.0
    with pytest.raises(ValueError, match="ahorro_pct.costo"):
        Resumen.model_validate(resumen)


def test_null_savings_require_a_zero_baseline():
    from app.schemas.rutas import Resumen

    resumen = _resumen_completado()
    resumen["ahorro_pct"]["distancia"] = None
    with pytest.raises(ValueError, match="ahorro_pct.distancia"):
        Resumen.model_validate(resumen)


def test_negative_savings_have_no_artificial_floor():
    from app.schemas.rutas import Ahorro

    ahorro = Ahorro(distancia=-150.0, co2=-250.5, combustible=None, costo=100)
    assert (ahorro.distancia, ahorro.co2) == (-150.0, -250.5)
    with pytest.raises(ValueError):
        Ahorro(distancia=100.01, co2=0, combustible=0, costo=0)


# --- ECL-119: stop outcomes, closure and dashboard errors ---------------------

RUTA = uuid4()
PARADA = uuid4()
HORA = "2026-11-16T10:30:00-05:00"


def actualizada(estado="ATENDIDA", ruta_estado="EN_CURSO"):
    return ParadaActualizada(
        parada_id=PARADA,
        ruta_id=RUTA,
        estado=estado,
        atendida_en=HORA if estado == "ATENDIDA" else None,
        ruta_estado=ruta_estado,
    )


def test_operator_records_a_stop_outcome():
    with client_for(Rol.OPERADOR) as ctx:
        ctx.cierres.registrar_parada.return_value = actualizada()
        response = ctx.client.patch(
            f"/rutas/{RUTA}/paradas/{PARADA}",
            json={"estado": "ATENDIDA", "atendida_en": HORA},
        )
    assert response.status_code == 200
    assert response.json()["ruta_estado"] == "EN_CURSO"
    assert response.headers["Cache-Control"] == "no-store"
    assert "X-Datos-Simulados" not in response.headers
    ruta, parada, solicitud = ctx.cierres.registrar_parada.call_args.args
    assert (ruta, parada) == (RUTA, PARADA) and solicitud.estado.value == "ATENDIDA"


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"estado": "ATENDIDA"},  # served needs the real time
        {"estado": "PENDIENTE"},  # only final outcomes
        {"estado": "NO_ATENDIDA", "nota": "x"},  # no extra fields
        {"estado": "ATENDIDA", "atendida_en": "2026-11-16T10:30:00"},  # naive
    ],
)
def test_invalid_outcomes_are_422_without_echo(cuerpo):
    with client_for(Rol.OPERADOR) as ctx:
        response = ctx.client.patch(f"/rutas/{RUTA}/paradas/{PARADA}", json=cuerpo)
    assert response.status_code == 422
    assert (
        "2026-11-16T10:30:00" not in response.text and 'PENDIENTE"' not in response.text
    )
    ctx.cierres.registrar_parada.assert_not_called()


@pytest.mark.parametrize(
    ("error", "codigo"),
    [
        (RutaNoEncontrada("Parada no encontrada en la ruta"), 404),
        (CierreConflicto("La parada ya tiene un resultado final"), 409),
        (CierreUnavailable("private"), 503),
    ],
)
def test_stop_outcome_errors(error, codigo):
    with client_for(Rol.OPERADOR) as ctx:
        ctx.cierres.registrar_parada.side_effect = error
        response = ctx.client.patch(
            f"/rutas/{RUTA}/paradas/{PARADA}", json={"estado": "NO_ATENDIDA"}
        )
    assert response.status_code == codigo
    assert "private" not in response.text


def test_service_time_rules_are_422_with_field_and_reason():
    with client_for(Rol.OPERADOR) as ctx:
        ctx.cierres.registrar_parada.side_effect = ResultadoInvalido(
            "atendida_en", "La hora de atención no puede ser futura"
        )
        response = ctx.client.patch(
            f"/rutas/{RUTA}/paradas/{PARADA}",
            json={"estado": "ATENDIDA", "atendida_en": HORA},
        )
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "campo": "atendida_en",
        "motivo": "La hora de atención no puede ser futura",
    }


def test_operator_closes_a_route_as_the_session_user():
    with client_for(Rol.OPERADOR) as ctx:
        ctx.cierres.cerrar.return_value = RutaCerrada(
            ruta_id=RUTA,
            estado="CERRADA",
            cerrada_en="2026-11-16T18:00:00-05:00",
            paradas_atendidas=3,
            paradas_no_atendidas=1,
        )
        response = ctx.client.post(f"/rutas/{RUTA}/cierre")
    assert response.status_code == 200
    assert response.json()["estado"] == "CERRADA"
    assert ctx.cierres.cerrar.call_args.args == (RUTA, ctx.identity.usuario_id)


@pytest.mark.parametrize(
    ("error", "codigo"),
    [
        (RutaNoEncontrada("Ruta no encontrada"), 404),
        (CierreConflicto("Faltan 2 paradas por registrar"), 409),
        (CierreUnavailable("private"), 503),
    ],
)
def test_closure_errors(error, codigo):
    with client_for(Rol.OPERADOR) as ctx:
        ctx.cierres.cerrar.side_effect = error
        response = ctx.client.post(f"/rutas/{RUTA}/cierre")
    assert response.status_code == codigo
    assert "private" not in response.text


@pytest.mark.parametrize(
    "rol", [Rol.ADMINISTRADOR, Rol.ANALISTA, Rol.AUDITOR, Rol.CONDUCTOR]
)
def test_only_the_operator_records_and_closes(rol):
    with client_for(rol) as ctx:
        cierre = ctx.client.post(f"/rutas/{RUTA}/cierre")
        parada = ctx.client.patch(
            f"/rutas/{RUTA}/paradas/{PARADA}", json={"estado": "NO_ATENDIDA"}
        )
    assert cierre.status_code == parada.status_code == 403
    ctx.cierres.cerrar.assert_not_called()


@pytest.mark.parametrize("error", [IndicadoresIncompletos("x"), CierreUnavailable("x")])
def test_dashboard_never_publishes_partial_or_failed_aggregates(error):
    with client_for(Rol.ANALISTA) as ctx:
        ctx.cierres.indicadores.side_effect = error
        response = ctx.client.get(
            "/indicadores/sostenibilidad",
            params={"desde": "2026-11-01", "hasta": "2026-11-30"},
        )
    assert response.status_code == 503
    assert response.json() == {"detail": "Servicio no disponible"}


def test_real_dashboard_has_no_simulated_header():
    with client_for(Rol.ANALISTA) as ctx:
        ctx.cierres.indicadores.side_effect = None
        ctx.cierres.indicadores.return_value = (
            rutas_simuladas.RutasSimuladasService()
            .sostenibilidad(date(2025, 1, 1), date(2025, 1, 31))
            .model_copy(update={"simulado": False})
        )
        response = ctx.client.get(
            "/indicadores/sostenibilidad",
            params={"desde": "2025-01-01", "hasta": "2025-01-31"},
        )
    assert response.status_code == 200 and response.json()["simulado"] is False
    assert "X-Datos-Simulados" not in response.headers


def test_closure_service_needs_a_database():
    app = create_app(Settings(database_url=None))
    identity = Identidad(uuid4(), Rol.OPERADOR, "ACTIVO")
    app.dependency_overrides[get_current_session] = lambda: AuthenticatedSession(
        uuid4(), identity
    )
    with TestClient(app) as client:
        app.state.authorization_service = AutorizacionService(Mock())
        response = client.post(f"/rutas/{RUTA}/cierre")
    assert response.status_code == 503
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(session_factory=Mock()))
    )
    assert get_closure_service(request) is not None
