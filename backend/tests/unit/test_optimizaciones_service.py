"""ST-047 (ECL-96): optimization service without a database.

The repository and the parameter service are replaced by in-memory fakes; the
ST-044 engine runs for real on tiny synthetic data. PostGIS behaviour is
covered by tests/integration/test_optimizaciones.py.
"""

from contextlib import nullcontext
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import OperationalError

from app.core.parametros import REFERENCIA_INICIAL
from app.optimizacion.elegibilidad import PlanRuta
from app.optimizacion.modelo import (
    Descanso,
    EstadoSolucion,
    Metricas,
    MotivoNoAsignado,
    NoAsignado,
    Parada,
    Punto,
    Solucion,
)
from app.optimizacion.modelo import Ruta as RutaVRP
from app.repositories.optimizaciones import ConductorElegible, OptimizacionStorageError
from app.schemas.rutas import OptimizacionSolicitud
from app.services import optimizaciones as modulo
from app.services.optimizaciones import (
    ERROR_CALCULO,
    OptimizacionFallida,
    OptimizacionService,
    OptimizacionUnavailable,
    SeleccionInvalida,
    _ahorro,
    asignar_conductores,
    medianoche,
    trazado,
)
from app.services.parametros import (
    ConjuntoParametros,
    ParametrosNoEncontrados,
    ParametrosUnavailable,
)

FECHA = date(2026, 11, 9)
BASE = medianoche(FECHA)
AHORA = datetime(2026, 11, 8, 15, 0, tzinfo=timezone.utc)
DEPOSITO = Punto(-12.0470, -76.9680)
VALORES = {v.codigo: v.valor for v in REFERENCIA_INICIAL}
ACTOR = uuid4()


def pedido(n, peso="20", lat=-12.045, lon=-76.97, inicio=9, fin=13, **cambios):
    fila = {
        "pedido_id": UUID(int=n),
        "latitud": lat,
        "longitud": lon,
        "peso_kg": Decimal(peso),
        "volumen_m3": Decimal("0.1"),
        "ventana_inicio": BASE + timedelta(hours=inicio),
        "ventana_fin": BASE + timedelta(hours=fin),
        "prioridad": "ESTANDAR",
        "estado": "PENDIENTE",
    }
    return {**fila, **cambios}


def vehiculo(n, estado="ACTIVO"):
    return SimpleNamespace(
        vehiculo_id=UUID(int=1000 + n),
        capacidad_kg=Decimal("800"),
        capacidad_m3=Decimal("4"),
        rendimiento_km_l=Decimal("11"),
        factor_co2_kg_km=Decimal("0.24364"),
        estado=estado,
    )


class FakeRepo:
    def __init__(self):
        self.pedidos = [
            pedido(1, lat=-12.040, lon=-76.975),
            pedido(2, lat=-12.050, lon=-76.960),
            pedido(3, peso="5000"),  # exceeds every vehicle (RN-009)
        ]
        self.flota = [vehiculo(1), vehiculo(2)]
        self.conductores = [
            ConductorElegible(
                uuid4(), BASE + timedelta(hours=7), BASE + timedelta(hours=19), FECHA
            )
        ]
        self.creadas = []
        self.completadas = []
        self.fallidas = []
        self.falla = None

    def _quizas_falla(self):
        if self.falla == "todo":
            raise OptimizacionStorageError("x")

    def pedidos_por_id(self, ids):
        self._quizas_falla()
        return [p for p in self.pedidos if p["pedido_id"] in ids]

    def pedidos_pendientes(self, desde, hasta, limite):
        self._quizas_falla()
        return [
            p
            for p in self.pedidos
            if p["estado"] == "PENDIENTE" and desde <= p["ventana_inicio"] < hasta
        ][:limite]

    def vehiculos(self, ids, limite):
        if ids is None:
            return [v for v in self.flota if v.estado == "ACTIVO"][:limite]
        return [v for v in self.flota if v.vehiculo_id in ids]

    def conductores_candidatos(self):
        return list(self.conductores)

    def crear(self, optimizacion):
        optimizacion.optimizacion_id = uuid4()
        self.creadas.append(optimizacion)

    def completar(self, optimizacion_id, valores, rutas, no_asignados):
        if self.falla == "completar":
            raise OptimizacionStorageError("x")
        self.completadas.append((optimizacion_id, valores, rutas, no_asignados))

    def fallar(self, optimizacion_id, error, cuando):
        if self.falla == "fallar":
            raise OptimizacionStorageError("x")
        self.fallidas.append((optimizacion_id, error))


class FakeParametros:
    falla = None

    def __init__(self, factory):
        pass

    def vigente(self, momento):
        if FakeParametros.falla:
            raise FakeParametros.falla
        return SimpleNamespace(version="REF-TEST")

    def conjunto(self, codigo):
        return ConjuntoParametros(codigo, dict(VALORES))


@pytest.fixture
def repo(monkeypatch):
    fake = FakeRepo()
    monkeypatch.setattr(modulo, "OptimizacionRepository", lambda session: fake)
    monkeypatch.setattr(modulo, "ParametroService", FakeParametros)
    FakeParametros.falla = None
    return fake


def factory():
    fabrica = Mock()
    fabrica.side_effect = lambda: nullcontext(Mock())
    fabrica.begin.side_effect = lambda: nullcontext(Mock())
    return fabrica


def service(**opciones):
    return OptimizacionService(
        factory(), DEPOSITO, tiempo_limite_s=1, reloj=lambda: AHORA, **opciones
    )


def solicitud(**cambios):
    return OptimizacionSolicitud(fecha_operacion=FECHA, **cambios)


# --- pure helpers -------------------------------------------------------------


def test_midnight_is_lima_local():
    assert medianoche(FECHA) == datetime(2026, 11, 9, 5, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("base", "nuevo", "esperado"),
    [(0, 0, None), (10, 7.5, 25.0), (10, 15, -50.0), (3, 1, (3 - 1) / 3 * 100)],
)
def test_savings_are_exact_signed_and_null_with_zero_base(base, nuevo, esperado):
    assert _ahorro(base, nuevo) == esperado


def test_drivers_go_to_the_first_route_they_cover_once_each():
    a = ConductorElegible(
        uuid4(), BASE + timedelta(hours=8), BASE + timedelta(hours=12), FECHA
    )
    b = ConductorElegible(
        uuid4(), BASE + timedelta(hours=7), BASE + timedelta(hours=20), FECHA
    )
    rutas = [
        (BASE + timedelta(hours=9), BASE + timedelta(hours=11)),
        (BASE + timedelta(hours=9), BASE + timedelta(hours=11)),
        (BASE + timedelta(hours=10), BASE + timedelta(hours=18)),
    ]
    rutas = [PlanRuta(inicio, fin, ((inicio, fin),)) for inicio, fin in rutas]
    assert asignar_conductores(rutas, [a, b]) == [a.conductor_id, b.conductor_id, None]
    assert asignar_conductores(rutas, []) == [None, None, None]


def test_trace_closes_at_the_depot_and_skips_missing_points():
    linea = trazado(DEPOSITO, [Punto(-12.04, -76.97), None, Punto(-12.05, -76.96)])
    assert linea == (
        "SRID=4326;LINESTRING(-76.968 -12.047, -76.97 -12.04, -76.96 -12.05, "
        "-76.968 -12.047)"
    )


# --- POST ---------------------------------------------------------------------


def test_run_is_created_solved_priced_and_completed(repo):
    aceptada = service().optimizar(solicitud(), ACTOR)
    assert aceptada.estado.value == "COMPLETADA" and aceptada.simulado is False
    assert aceptada.solicitada_en == AHORA
    assert aceptada.solicitada_en.utcoffset() == timedelta(hours=-5)
    creada = repo.creadas[0]
    assert creada.estado == "EN_PROCESO" and creada.solicitada_por == ACTOR
    assert creada.instantanea["parametros"]["LITROS_POR_GALON"] == "3.785411784"
    assert len(creada.instantanea["pedidos"]) == 3
    assert creada.instantanea["conductores_candidatos"] == 1

    run_id, valores, rutas, no_asignados = repo.completadas[0]
    assert run_id == aceptada.optimizacion_id
    assert (
        valores["estado"] == "COMPLETADA"
        and valores["parametros_version"] == "REF-TEST"
    )
    assert valores["cumplimiento_ventanas_pct"] == 100
    assert [n.motivo for n in no_asignados] == ["EXCEDE_CAPACIDAD"]
    assert no_asignados[0].pedido_id == UUID(int=3)
    servidos = {p.pedido_id for _, paradas in rutas for p in paradas}
    assert servidos == {UUID(int=1), UUID(int=2)}
    for ruta, paradas in rutas:
        assert ruta.optimizacion_id == run_id and ruta.trazado.startswith("SRID=4326;")
        assert ruta.costo_soles == pytest.approx(
            ruta.combustible_l / 3.785411784 * 17.50 + ruta.distancia_km * 1.20
        )
        assert [p.secuencia for p in paradas] == list(range(1, len(paradas) + 1))
    con = [r for r, _ in rutas if r.conductor_id is not None]
    sin = [r for r, _ in rutas if r.conductor_id is None]
    assert len(con) == 1
    assert all(r.motivo_sin_conductor == "SIN_CONDUCTOR_ELEGIBLE" for r in sin)
    assert valores["secuencial_costo_soles"] == pytest.approx(
        valores["secuencial_combustible_l"] / 3.785411784 * 17.50
        + valores["secuencial_distancia_km"] * 1.20
    )


def test_run_with_only_unassigned_orders_is_still_completed(repo):
    repo.pedidos = [pedido(3, peso="5000")]
    service().optimizar(solicitud(), ACTOR)
    _, valores, rutas, no_asignados = repo.completadas[0]
    assert rutas == [] and len(no_asignados) == 1
    assert valores["secuencial_distancia_km"] == 0.0
    assert valores["cumplimiento_ventanas_pct"] == 0.0


def test_breaks_are_stored_as_lima_times(repo):
    ruta = RutaVRP(
        vehiculo_id=str(UUID(int=1001)),
        paradas=(Parada(1, str(UUID(int=1)), 600),),
        salida_min=480,
        regreso_min=900,
        peso_kg=20.0,
        volumen_m3=0.1,
        metricas=Metricas(10.0, 2.4, 0.9),
        descansos=(Descanso(720, 60),),
    )
    solucion = Solucion(EstadoSolucion.COMPLETADA, (ruta,), (), None, 0.5)
    repo.pedidos = [pedido(1)]
    service(resolver=lambda problema: solucion).optimizar(solicitud(), ACTOR)
    guardada = repo.completadas[0][2][0][0]
    assert guardada.descansos == [
        {"inicio": "2026-11-09T12:00:00-05:00", "fin": "2026-11-09T13:00:00-05:00"}
    ]
    assert guardada.tiempo_min == 420


@pytest.mark.parametrize(
    ("preparar", "datos", "campo"),
    [
        (lambda r: setattr(r, "pedidos", []), {}, "pedido_ids"),
        (
            lambda r: setattr(r, "pedidos", [pedido(n) for n in range(1, 152)]),
            {},
            "pedido_ids",
        ),
        (lambda r: None, {"pedido_ids": [uuid4()]}, "pedido_ids"),
        (
            lambda r: r.pedidos.append(pedido(9, estado="ENTREGADO")),
            {"pedido_ids": [UUID(int=9)]},
            "pedido_ids",
        ),
        (
            lambda r: r.pedidos.append(pedido(8, inicio=30, fin=34)),
            {"pedido_ids": [UUID(int=8)]},
            "pedido_ids",
        ),
        (lambda r: setattr(r, "flota", []), {}, "vehiculo_ids"),
        (
            lambda r: setattr(r, "flota", [vehiculo(n) for n in range(16)]),
            {},
            "vehiculo_ids",
        ),
        (lambda r: None, {"vehiculo_ids": [uuid4()]}, "vehiculo_ids"),
        (
            lambda r: r.flota.append(vehiculo(7, "INACTIVO")),
            {"vehiculo_ids": [UUID(int=1007)]},
            "vehiculo_ids",
        ),
    ],
)
def test_invalid_selection_never_creates_a_run(repo, preparar, datos, campo):
    preparar(repo)
    with pytest.raises(SeleccionInvalida) as error:
        service().optimizar(solicitud(**datos), ACTOR)
    assert error.value.campo == campo
    assert str(UUID(int=9)) not in error.value.motivo
    assert repo.creadas == []


def test_explicit_selection_is_accepted(repo):
    service().optimizar(
        solicitud(pedido_ids=[UUID(int=1)], vehiculo_ids=[UUID(int=1001)]), ACTOR
    )
    assert repo.creadas[0].instantanea["pedidos"] == [str(UUID(int=1))]


def test_without_parameters_in_force_it_is_a_selection_error(repo):
    FakeParametros.falla = ParametrosNoEncontrados("x")
    with pytest.raises(SeleccionInvalida) as error:
        service().optimizar(solicitud(), ACTOR)
    assert error.value.campo == "parametros" and repo.creadas == []


def test_parameter_storage_failure_is_unavailable(repo):
    FakeParametros.falla = ParametrosUnavailable("x")
    with pytest.raises(OptimizacionUnavailable):
        service().optimizar(solicitud(), ACTOR)


def test_storage_failure_before_solving_is_unavailable(repo):
    repo.falla = "todo"
    with pytest.raises(OptimizacionUnavailable):
        service().optimizar(solicitud(), ACTOR)
    assert repo.creadas == []


def _sin_solucion(problema):
    return Solucion(
        EstadoSolucion.SIN_SOLUCION,
        (),
        (NoAsignado(str(UUID(int=1)), MotivoNoAsignado.SIN_VEHICULO),),
        None,
        20.0,
    )


def _explota(problema):
    raise RuntimeError("secreto interno")


@pytest.mark.parametrize("resolver", [_sin_solucion, _explota])
def test_engine_failure_marks_the_run_failed(repo, resolver):
    with pytest.raises(OptimizacionFallida) as error:
        service(resolver=resolver).optimizar(solicitud(), ACTOR)
    assert repo.fallidas == [(error.value.optimizacion_id, ERROR_CALCULO)]
    assert repo.completadas == [] and "secreto" not in str(error.value)


def test_storage_failure_after_solving_marks_the_run_failed(repo):
    repo.falla = "completar"
    with pytest.raises(OptimizacionFallida):
        service().optimizar(solicitud(), ACTOR)
    assert len(repo.fallidas) == 1


def test_failure_that_cannot_be_recorded_is_unavailable(repo):
    repo.falla = "fallar"
    with pytest.raises(OptimizacionUnavailable):
        service(resolver=_explota).optimizar(solicitud(), ACTOR)


def test_sqlalchemy_errors_while_creating_are_unavailable(repo, monkeypatch):
    def crear(optimizacion):
        raise OperationalError("x", {}, Exception("y"))

    monkeypatch.setattr(repo, "crear", crear)
    with pytest.raises(OptimizacionUnavailable):
        service().optimizar(solicitud(), ACTOR)


# --- GET detail and list ------------------------------------------------------

RUN = uuid4()
RUTA = uuid4()


def corrida(estado="COMPLETADA", **cambios):
    valores = {
        "optimizacion_id": RUN,
        "estado": estado,
        "fecha_operacion": FECHA,
        "solicitada_en": AHORA,
        "finalizada_en": AHORA + timedelta(seconds=20)
        if estado != "EN_PROCESO"
        else None,
        "duracion_s": 19.5 if estado == "COMPLETADA" else None,
        "parametros_version": "REF-TEST" if estado == "COMPLETADA" else None,
        "simulado": False,
        "error": ERROR_CALCULO if estado == "FALLIDA" else None,
        "secuencial_distancia_km": 20.0,
        "secuencial_co2_kg": 5.0,
        "secuencial_combustible_l": 2.0,
        "secuencial_costo_soles": 33.25,
        "cumplimiento_ventanas_pct": 100.0,
    }
    return SimpleNamespace(**{**valores, **cambios})


def fila_ruta(conductor=True):
    return {
        "ruta_id": RUTA,
        "estado": "PLANIFICADA",
        "salida": BASE + timedelta(hours=8),
        "regreso": BASE + timedelta(hours=12),
        "tiempo_min": 240,
        "peso_kg": Decimal("40.00"),
        "volumen_m3": Decimal("0.200"),
        "distancia_km": 15.0,
        "co2_kg": 3.6,
        "combustible_l": 1.5,
        "costo_soles": 24.9,
        "descansos": [],
        "motivo_sin_conductor": None if conductor else "SIN_CONDUCTOR_ELEGIBLE",
        "trazado": '{"type":"LineString","coordinates":[[-76.968,-12.047],'
        "[-76.97,-12.04],[-76.968,-12.047]]}",
        "vehiculo_id": UUID(int=1001),
        "placa": "ABC-123",
        "tipo": "CAMIONETA",
        "conductor_id": uuid4() if conductor else None,
        "conductor_nombre": "Rosa Sintético" if conductor else None,
    }


def fila_parada(ruta_id=RUTA, pedido_n=1):
    return {
        "parada_id": uuid4(),
        "ruta_id": ruta_id,
        "secuencia": 1,
        "pedido_id": UUID(int=pedido_n),
        "eta": BASE + timedelta(hours=9),
        "estado": "PENDIENTE",
        "latitud": -12.04,
        "longitud": -76.97,
        "ventana_inicio": BASE + timedelta(hours=9),
        "ventana_fin": BASE + timedelta(hours=13),
    }


def test_detail_of_a_completed_run(repo):
    repo.obtener = lambda i: corrida()
    otra = uuid4()
    repo.rutas_de = lambda i: [
        fila_ruta(),
        fila_ruta(conductor=False) | {"ruta_id": otra},
    ]
    repo.paradas_de = lambda i: [fila_parada(), fila_parada(otra, 2)]
    repo.no_asignados_de = lambda i: [
        {"pedido_id": UUID(int=3), "motivo": "EXCEDE_CAPACIDAD"}
    ]
    detalle = service().detalle(RUN)
    assert detalle.estado.value == "COMPLETADA" and detalle.simulado is False
    primera, segunda = detalle.rutas
    assert primera.conductor.nombre == "Rosa Sintético"
    assert segunda.conductor is None
    assert segunda.motivo_sin_conductor.value == "SIN_CONDUCTOR_ELEGIBLE"
    assert primera.paradas[0].eta.utcoffset() == timedelta(hours=-5)
    assert primera.trazado.coordinates[0] == primera.trazado.coordinates[-1]
    resumen = detalle.resumen
    assert resumen.rutas == 2 and resumen.pedidos_asignados == 2
    assert resumen.pedidos_no_asignados == 1
    assert resumen.optimizada.distancia_km == 30.0
    assert resumen.ahorro_pct.distancia == pytest.approx(-50.0)
    assert resumen.ahorro_pct.costo == pytest.approx((33.25 - 49.8) / 33.25 * 100)


@pytest.mark.parametrize("estado", ["EN_PROCESO", "FALLIDA"])
def test_detail_of_an_unfinished_run_has_no_routes(repo, estado):
    repo.obtener = lambda i: corrida(estado)
    detalle = service().detalle(RUN)
    assert detalle.rutas == [] and detalle.resumen is None
    assert (detalle.error is not None) == (estado == "FALLIDA")


def test_detail_of_an_unknown_run_is_none(repo):
    repo.obtener = lambda i: None
    assert service().detalle(RUN) is None


def test_zero_baseline_gives_null_savings(repo):
    repo.obtener = lambda i: corrida(
        secuencial_distancia_km=0.0,
        secuencial_co2_kg=0.0,
        secuencial_combustible_l=0.0,
        secuencial_costo_soles=0.0,
    )
    repo.rutas_de = lambda i: []
    repo.paradas_de = lambda i: []
    repo.no_asignados_de = lambda i: [
        {"pedido_id": UUID(int=3), "motivo": "SIN_UBICACION"}
    ]
    resumen = service().detalle(RUN).resumen
    assert resumen.rutas == 0
    assert resumen.ahorro_pct.model_dump() == {
        "distancia": None,
        "co2": None,
        "combustible": None,
        "costo": None,
    }


def test_listing_summarises_completed_runs_only(repo):
    otra = corrida("FALLIDA", optimizacion_id=uuid4())
    vacia = corrida(
        optimizacion_id=uuid4(),
        secuencial_distancia_km=0.0,
        secuencial_co2_kg=0.0,
        secuencial_combustible_l=0.0,
        secuencial_costo_soles=0.0,
    )
    repo.pagina = lambda fecha, page, size: ([corrida(), otra, vacia], 7)
    repo.totales = lambda ids: {
        RUN: {
            "rutas": 2,
            "distancia_km": 15.0,
            "co2_kg": 4.0,
            "combustible_l": 1.5,
            "costo_soles": 25.0,
        }
    }
    repo.conteos = lambda ids: {i: (5, 1) if i == RUN else (0, 0) for i in ids}
    pagina = service().listar(FECHA, 2, 3)
    assert (pagina.total, pagina.page, pagina.page_size) == (7, 2, 3)
    assert pagina.simulado is False
    completa, fallida, sin_rutas = pagina.items
    assert completa.resumen.rutas == 2 and completa.resumen.pedidos_asignados == 5
    assert completa.resumen.ahorro_pct.distancia == pytest.approx(25.0)
    assert fallida.resumen is None
    assert sin_rutas.resumen.rutas == 0
    assert sin_rutas.resumen.ahorro_pct.costo is None


@pytest.mark.parametrize("operacion", ["detalle", "listar"])
def test_reads_translate_storage_failures(repo, operacion):
    def falla(*args):
        raise OptimizacionStorageError("x")

    repo.obtener = falla
    repo.pagina = falla
    with pytest.raises(OptimizacionUnavailable):
        if operacion == "detalle":
            service().detalle(RUN)
        else:
            service().listar(None, 1, 20)
