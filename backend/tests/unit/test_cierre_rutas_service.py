"""ECL-119: stop outcomes, closure and the US-009 aggregate without a database.

The repositories are in-memory fakes; PostGIS behaviour (locks, SQL sums,
period limits) is covered by tests/integration/test_cierre_rutas.py.
"""

from contextlib import nullcontext
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

from app.repositories.auditoria import AuditStorageError, Evento
from app.repositories.cierre_rutas import CierreStorageError
from app.schemas.rutas import ResultadoParadaSolicitud
from app.services import cierre_rutas as modulo
from app.services.cierre_rutas import (
    CierreConflicto,
    CierreRutaService,
    CierreUnavailable,
    IndicadoresIncompletos,
    ResultadoInvalido,
    RutaNoEncontrada,
)
from app.services.optimizaciones import medianoche

FECHA = date(2026, 11, 16)
AHORA = medianoche(FECHA) + timedelta(hours=19)
ACTOR = uuid4()


def ruta(estado="PLANIFICADA", **cambios):
    valores = {
        "ruta_id": uuid4(),
        "estado": estado,
        "fecha_operacion": FECHA,
        "cerrada_en": AHORA - timedelta(hours=1) if estado == "CERRADA" else None,
        "secuencial_distancia_km": 120.0,
    }
    return SimpleNamespace(**{**valores, **cambios})


def parada(r, estado="PENDIENTE", atendida_en=None):
    return SimpleNamespace(
        parada_id=uuid4(), ruta_id=r.ruta_id, estado=estado, atendida_en=atendida_en
    )


class FakeRepo:
    def __init__(self):
        self.ruta_actual = ruta()
        self.parada_actual = parada(self.ruta_actual)
        self.conteo = {"ATENDIDA": 3, "NO_ATENDIDA": 1}
        self.totales_actuales = {"rutas": 0}
        self.versiones_actuales = []
        self.cumple = (0, 0)
        self.guardados = 0
        self.falla = False

    def ruta(self, ruta_id):
        if self.falla:
            raise CierreStorageError("x")
        return self.ruta_actual

    def parada(self, ruta_id, parada_id):
        return self.parada_actual

    def conteo_paradas(self, ruta_id):
        return dict(self.conteo)

    def guardar(self):
        self.guardados += 1

    def totales(self, desde, hasta):
        if self.falla:
            raise CierreStorageError("x")
        self.periodo = (desde, hasta)
        return self.totales_actuales

    def versiones(self, desde, hasta):
        return self.versiones_actuales

    def cumplimiento(self, desde, hasta):
        return self.cumple


@pytest.fixture
def repo(monkeypatch):
    fake = FakeRepo()
    auditoria = Mock()
    monkeypatch.setattr(modulo, "CierreRutaRepository", lambda session: fake)
    monkeypatch.setattr(modulo, "AuditoriaRepository", lambda session: auditoria)
    fake.auditoria = auditoria
    return fake


def service():
    fabrica = Mock()
    fabrica.side_effect = lambda: nullcontext(Mock())
    fabrica.begin.side_effect = lambda: nullcontext(Mock())
    return CierreRutaService(fabrica, reloj=lambda: AHORA)


def atendida(hora=AHORA - timedelta(hours=3)):
    return ResultadoParadaSolicitud(estado="ATENDIDA", atendida_en=hora)


def no_atendida():
    return ResultadoParadaSolicitud(estado="NO_ATENDIDA")


# --- stop outcomes -------------------------------------------------------------


def test_first_outcome_starts_the_route(repo):
    resultado = service().registrar_parada(uuid4(), uuid4(), atendida())
    assert resultado.estado.value == "ATENDIDA"
    assert resultado.ruta_estado.value == "EN_CURSO"
    assert resultado.atendida_en.utcoffset() == timedelta(hours=-5)
    assert repo.parada_actual.estado == "ATENDIDA" and repo.guardados == 1


def test_not_served_needs_no_time_and_keeps_an_open_route(repo):
    repo.ruta_actual.estado = "EN_CURSO"
    resultado = service().registrar_parada(uuid4(), uuid4(), no_atendida())
    assert resultado.estado.value == "NO_ATENDIDA" and resultado.atendida_en is None
    assert resultado.ruta_estado.value == "EN_CURSO"


def test_repeating_the_same_outcome_changes_nothing(repo):
    hora = AHORA - timedelta(hours=2)
    repo.parada_actual.estado, repo.parada_actual.atendida_en = "ATENDIDA", hora
    repo.ruta_actual.estado = "EN_CURSO"
    resultado = service().registrar_parada(uuid4(), uuid4(), atendida(hora))
    assert resultado.estado.value == "ATENDIDA" and repo.guardados == 0


def test_a_final_outcome_is_never_overwritten(repo):
    repo.parada_actual.estado = "NO_ATENDIDA"
    with pytest.raises(CierreConflicto, match="resultado final"):
        service().registrar_parada(uuid4(), uuid4(), atendida())


@pytest.mark.parametrize(
    ("preparar", "error"),
    [
        (lambda r: setattr(r, "ruta_actual", None), RutaNoEncontrada),
        (lambda r: setattr(r, "parada_actual", None), RutaNoEncontrada),
        (lambda r: setattr(r.ruta_actual, "estado", "CERRADA"), CierreConflicto),
    ],
)
def test_unknown_or_closed_routes_are_refused(repo, preparar, error):
    preparar(repo)
    with pytest.raises(error):
        service().registrar_parada(uuid4(), uuid4(), no_atendida())
    assert repo.guardados == 0


@pytest.mark.parametrize(
    "hora",
    [AHORA + timedelta(minutes=1), medianoche(FECHA) - timedelta(minutes=1)],
)
def test_service_time_must_be_inside_the_day_and_not_future(repo, hora):
    with pytest.raises(ResultadoInvalido) as error:
        service().registrar_parada(uuid4(), uuid4(), atendida(hora))
    assert error.value.campo == "atendida_en" and repo.guardados == 0


def test_outcome_storage_failure_is_unavailable(repo):
    repo.falla = True
    with pytest.raises(CierreUnavailable):
        service().registrar_parada(uuid4(), uuid4(), no_atendida())


# --- closure -------------------------------------------------------------------


def test_closing_records_the_instant_and_audits_once(repo):
    repo.ruta_actual.estado = "EN_CURSO"
    cierre = service().cerrar(repo.ruta_actual.ruta_id, ACTOR)
    assert cierre.estado.value == "CERRADA" and cierre.cerrada_en == AHORA
    assert (cierre.paradas_atendidas, cierre.paradas_no_atendidas) == (3, 1)
    registro = repo.auditoria.insert.call_args.args[0]
    assert registro.evento is Evento.RUTA_CERRADA and registro.usuario_id == ACTOR
    assert registro.entidad_id == repo.ruta_actual.ruta_id
    assert registro.detalle.paradas_atendidas == 3


def test_repeating_a_closure_returns_the_stored_one(repo):
    repo.ruta_actual = ruta("CERRADA")
    cierre = service().cerrar(repo.ruta_actual.ruta_id, ACTOR)
    assert cierre.cerrada_en == repo.ruta_actual.cerrada_en
    repo.auditoria.insert.assert_not_called()
    assert repo.guardados == 0


def test_pending_stops_block_the_closure(repo):
    repo.conteo = {"ATENDIDA": 2, "PENDIENTE": 2}
    with pytest.raises(CierreConflicto, match="Faltan 2 paradas"):
        service().cerrar(uuid4(), ACTOR)
    assert repo.ruta_actual.estado == "PLANIFICADA"


def test_routes_without_sequential_reference_cannot_close(repo):
    repo.ruta_actual.secuencial_distancia_km = None
    with pytest.raises(CierreConflicto, match="referencia secuencial"):
        service().cerrar(uuid4(), ACTOR)


def test_closing_an_unknown_route_is_not_found(repo):
    repo.ruta_actual = None
    with pytest.raises(RutaNoEncontrada):
        service().cerrar(uuid4(), ACTOR)


@pytest.mark.parametrize(
    "error", [AuditStorageError("x"), OperationalError("x", {}, Exception("y"))]
)
def test_closure_storage_failures_are_unavailable(repo, error):
    repo.auditoria.insert.side_effect = error
    with pytest.raises(CierreUnavailable):
        service().cerrar(uuid4(), ACTOR)


# --- US-009 aggregate ----------------------------------------------------------


def totales(**cambios):
    """BDD D01: two closed routes (100+50 km planned, 120+80 km sequential)."""
    base = {
        "rutas": 2,
        "con_referencia": 2,
        "distancia_km": 150.0,
        "co2_kg": 30.0,
        "combustible_l": 15.0,
        "costo_soles": 240.0,
        "sec_distancia_km": 200.0,
        "sec_co2_kg": 40.0,
        "sec_combustible_l": 20.0,
        "sec_costo_soles": 320.0,
    }
    return {**base, **cambios}


def test_bdd_d01_reference_aggregate(repo):
    repo.totales_actuales = totales()
    repo.versiones_actuales = ["REF-A", "REF-B"]
    repo.cumple = (3, 4)
    datos = service().indicadores(date(2026, 11, 1), date(2026, 11, 30))
    assert datos.con_datos and datos.rutas_cerradas == 2 and not datos.simulado
    assert (datos.distancia_km, datos.co2_kg, datos.costo_soles) == (150, 30, 240)
    ahorro = datos.ahorro_vs_secuencial
    assert (ahorro.distancia_km, ahorro.co2_kg, ahorro.combustible_l) == (50, 10, 5)
    assert ahorro.costo_soles == 80 and ahorro.pct == 25
    assert datos.cumplimiento_ventanas_pct == 75
    assert datos.parametros_versiones == ["REF-A", "REF-B"]
    # Lima days, inclusive: [01/11 00:00, 01/12 00:00) at UTC-5.
    assert repo.periodo == (
        datetime(2026, 11, 1, 5, tzinfo=timezone.utc),
        datetime(2026, 12, 1, 5, tzinfo=timezone.utc),
    )


def test_without_closed_routes_everything_is_null(repo):
    datos = service().indicadores(date(2025, 1, 1), date(2025, 1, 31))
    assert not datos.con_datos and datos.rutas_cerradas == 0
    assert datos.distancia_km is None and datos.ahorro_vs_secuencial is None
    assert datos.cumplimiento_ventanas_pct is None and datos.parametros_versiones == []
    assert datos.simulado is False


def test_zero_base_gives_null_pct_and_negative_savings_are_kept(repo):
    repo.totales_actuales = totales(
        distancia_km=0.0,
        sec_distancia_km=0.0,
        co2_kg=50.0,
        sec_co2_kg=40.0,
    )
    repo.cumple = (0, 2)
    datos = service().indicadores(FECHA, FECHA)
    assert datos.distancia_km == 0 and datos.ahorro_vs_secuencial.pct is None
    assert datos.ahorro_vs_secuencial.co2_kg == -10
    assert datos.cumplimiento_ventanas_pct == 0


@pytest.mark.parametrize(
    ("preparar"),
    [
        lambda r: setattr(r, "totales_actuales", totales(con_referencia=1)),
        lambda r: setattr(r, "totales_actuales", totales()),  # no terminal stops
    ],
)
def test_incomplete_closed_routes_are_never_published(repo, preparar):
    preparar(repo)
    with pytest.raises(IndicadoresIncompletos):
        service().indicadores(FECHA, FECHA)


def test_aggregate_storage_failure_is_unavailable(repo):
    repo.falla = True
    with pytest.raises(CierreUnavailable):
        service().indicadores(FECHA, FECHA)
