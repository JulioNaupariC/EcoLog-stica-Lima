"""ECL-93 (ST-044): VRPTW optimizer on small cases checkable by hand."""

from dataclasses import replace

import pytest

from app.optimizacion import vrptw
from app.optimizacion.distancias import haversine_km, matriz_km, minutos_viaje
from app.optimizacion.metricas import metricas_vehiculo, ruta_secuencial, sumar
from app.optimizacion.modelo import (
    Comparacion,
    Configuracion,
    Descanso,
    EstadoSolucion,
    Metricas,
    MotivoNoAsignado,
    NoAsignado,
    Parada,
    PedidoVRP,
    Prioridad,
    Problema,
    Punto,
    Ruta,
    Solucion,
    VehiculoVRP,
)
from app.optimizacion.sinteticos import escenario, flota, inviables
from app.optimizacion.verificacion import violaciones

DEPOSITO = Punto(-12.0470, -76.9680)
RAPIDO = Configuracion(tiempo_limite_s=2, metaheuristica=False)
H = 60


def pedido(
    pid: str,
    dlat: float = 0.01,
    dlon: float = 0.0,
    kg: float = 10.0,
    m3: float = 0.05,
    ventana: tuple[int, int] = (8 * H, 16 * H),
    prioridad: Prioridad = Prioridad.ESTANDAR,
) -> PedidoVRP:
    return PedidoVRP(
        pid,
        Punto(DEPOSITO.latitud + dlat, DEPOSITO.longitud + dlon),
        kg,
        m3,
        ventana[0],
        ventana[1],
        prioridad,
    )


def vehiculo(vid: str = "V1", kg: float = 800.0, m3: float = 4.0) -> VehiculoVRP:
    return VehiculoVRP(vid, kg, m3, 10.0, 0.25)


def problema(pedidos, vehiculos, config: Configuracion = RAPIDO) -> Problema:
    return Problema(DEPOSITO, tuple(pedidos), tuple(vehiculos), config)


def motivos(solucion: Solucion) -> dict[str, MotivoNoAsignado]:
    return {n.pedido_id: n.motivo for n in solucion.no_asignados}


# --- distances and metrics -------------------------------------------------


def test_haversine_one_degree_of_latitude_is_about_111_km():
    assert haversine_km(Punto(0, 0), Punto(1, 0)) == pytest.approx(111.195, abs=0.01)
    assert haversine_km(DEPOSITO, DEPOSITO) == 0


def test_matrix_is_symmetric_and_applies_the_detour_factor():
    a, b = Punto(0, 0), Punto(1, 0)
    km = matriz_km([a, b], 1.5)
    assert km[0][1] == km[1][0] == pytest.approx(haversine_km(a, b) * 1.5)
    assert km[0][0] == 0


@pytest.mark.parametrize(("km", "esperado"), [(0, 0), (10, 30), (10.1, 31), (0.01, 1)])
def test_travel_minutes_round_up(km, esperado):
    assert minutos_viaje(km, 20.0) == esperado


def test_vehicle_metrics_follow_rn011_and_rn013():
    m = metricas_vehiculo(100.0, VehiculoVRP("V", 1, 1, 8.0, 0.3))
    assert m == Metricas(100.0, pytest.approx(30.0), pytest.approx(12.5))
    total = sumar([m, m])
    assert total.distancia_km == 200.0 and total.co2_kg == 60.0


def test_sequential_baseline_by_hand():
    # depot 0, two orders at 10 km and 20 km on a line; one 15-kg vehicle.
    linea = [[0, 10, 20], [10, 0, 10], [20, 10, 0]]
    pedidos = [(1, pedido("A", kg=10)), (2, pedido("B", kg=10))]
    v = VehiculoVRP("V", 15.0, 1.0, 10.0, 0.5)
    # The second order does not fit: two trips 0-1-0 (20 km) and 0-2-0 (40 km).
    m = ruta_secuencial(pedidos, [v], lambda a, b: linea[a][b])
    assert m.distancia_km == 60 and m.co2_kg == 30 and m.combustible_l == 6
    # With room for both: one trip 0-1-2-0 = 40 km.
    grande = replace(v, capacidad_kg=50.0)
    assert (
        ruta_secuencial(pedidos, [grande], lambda a, b: linea[a][b]).distancia_km == 40
    )


def test_sequential_baseline_skips_vehicles_too_small_and_handles_empty():
    linea = [[0, 5], [5, 0]]
    chico = VehiculoVRP("MOTO", 5.0, 1.0, 30.0, 0.07)
    grande = VehiculoVRP("FURGON", 100.0, 5.0, 9.0, 0.3)
    m = ruta_secuencial(
        [(1, pedido("A", kg=50))], [chico, grande], lambda a, b: linea[a][b]
    )
    assert m.distancia_km == 10 and m.co2_kg == pytest.approx(3.0)
    assert ruta_secuencial([], [grande], lambda a, b: 0) == Metricas(0, 0, 0)
    with pytest.raises(ValueError):
        ruta_secuencial([(1, pedido("A", kg=500))], [chico], lambda a, b: linea[a][b])


def test_savings_percentages_and_zero_baseline():
    c = Comparacion(Metricas(80, 20, 8), Metricas(100, 25, 10))
    assert (c.ahorro_distancia_pct, c.ahorro_co2_pct, c.ahorro_combustible_pct) == (
        20.0,
        20.0,
        20.0,
    )
    assert Comparacion(Metricas(0, 0, 0), Metricas(0, 0, 0)).ahorro_distancia_pct == 0


# --- solver: golden, happy, unhappy and edge routes ------------------------


def test_happy_route_serves_every_order_inside_its_window():
    pedidos = [
        pedido("A", 0.01, 0.0, ventana=(9 * H, 10 * H)),
        pedido("B", 0.0, 0.01, ventana=(8 * H, 12 * H)),
        pedido("C", -0.01, 0.0, ventana=(10 * H, 11 * H)),
    ]
    p = problema(pedidos, [vehiculo()])
    s = vrptw.resolver(p)
    assert s.estado is EstadoSolucion.COMPLETADA
    assert s.no_asignados == ()
    assert len(s.rutas) == 1
    ruta = s.rutas[0]
    assert [x.secuencia for x in ruta.paradas] == [1, 2, 3]
    assert ruta.peso_kg == 30 and ruta.metricas.distancia_km > 0
    assert violaciones(p, s) == []
    assert s.comparacion is not None


def test_capacity_splits_orders_between_vehicles():
    pedidos = [pedido("A", kg=600), pedido("B", 0.0, 0.01, kg=600)]
    p = problema(pedidos, [vehiculo("V1"), vehiculo("V2")])
    s = vrptw.resolver(p)
    assert len(s.rutas) == 2
    assert s.no_asignados == ()
    assert violaciones(p, s) == []


def test_unhappy_order_exceeding_the_fleet_is_reported_and_others_kept():
    pedidos = [pedido("A"), pedido("GRANDE", kg=5000)]
    s = vrptw.resolver(problema(pedidos, [vehiculo()]))
    assert motivos(s) == {"GRANDE": MotivoNoAsignado.EXCEDE_CAPACIDAD}
    assert [x.pedido_id for x in s.rutas[0].paradas] == ["A"]


def test_volume_alone_can_exceed_the_fleet():
    s = vrptw.resolver(problema([pedido("A", m3=9.0)], [vehiculo()]))
    assert motivos(s) == {"A": MotivoNoAsignado.EXCEDE_CAPACIDAD}


def test_order_without_location_is_reported():
    sin = replace(pedido("SIN"), ubicacion=None)
    s = vrptw.resolver(problema([sin, pedido("A")], [vehiculo()]))
    assert motivos(s) == {"SIN": MotivoNoAsignado.SIN_UBICACION}


@pytest.mark.parametrize(
    "ventana",
    [
        (5 * H, 6 * H),  # ends before the working day starts
        (12 * H, 11 * H),  # inverted window
        (18 * H, 19 * H),  # cannot return before the end of the day
    ],
)
def test_infeasible_windows_are_reported(ventana):
    s = vrptw.resolver(problema([pedido("X", ventana=ventana)], [vehiculo()]))
    assert motivos(s) == {"X": MotivoNoAsignado.VENTANA_INVIABLE}
    assert s.rutas == () and s.comparacion is None


def test_edge_without_vehicles_or_orders_never_fails():
    sin_vehiculos = vrptw.resolver(problema([pedido("A")], []))
    assert motivos(sin_vehiculos) == {"A": MotivoNoAsignado.SIN_VEHICULO}
    assert sin_vehiculos.rutas == ()
    sin_pedidos = vrptw.resolver(problema([], [vehiculo()]))
    assert sin_pedidos.estado is EstadoSolucion.COMPLETADA
    assert sin_pedidos.rutas == sin_pedidos.no_asignados == ()


def test_priority_decides_which_order_is_left_out():
    pedidos = [
        pedido("ECO", kg=500, prioridad=Prioridad.ECONOMICO),
        pedido("EXP", 0.0, 0.01, kg=500, prioridad=Prioridad.EXPRESS),
    ]
    s = vrptw.resolver(problema(pedidos, [vehiculo(kg=600)]))
    assert [x.pedido_id for x in s.rutas[0].paradas] == ["EXP"]
    assert motivos(s) == {"ECO": MotivoNoAsignado.SIN_VEHICULO}


def test_long_day_includes_the_rn005_break():
    pedidos = [
        pedido("TEMPRANO", ventana=(8 * H + 20, 8 * H + 40)),
        pedido("TARDE", 0.0, 0.01, ventana=(14 * H, 14 * H + 30)),
    ]
    p = problema(pedidos, [vehiculo()])
    s = vrptw.resolver(p)
    ruta = s.rutas[0]
    assert ruta.duracion_min > 4 * H
    assert ruta.descansos and ruta.descansos[0].duracion_min == H
    assert violaciones(p, s) == []


def test_no_solution_from_the_solver_marks_candidates_without_vehicle(monkeypatch):
    monkeypatch.setattr(vrptw._Modelo, "resolver", lambda self: None)
    s = vrptw.resolver(problema([pedido("A")], [vehiculo()]))
    assert s.estado is EstadoSolucion.SIN_SOLUCION
    assert motivos(s) == {"A": MotivoNoAsignado.SIN_VEHICULO}


# --- synthetic scenario and RNF-001 guard ----------------------------------


def test_synthetic_scenario_is_reproducible():
    a = escenario(20, 3, 7, RAPIDO)
    b = escenario(20, 3, 7, RAPIDO)
    assert a == b
    assert len(a.pedidos) == 20 and len(a.vehiculos) == 3
    assert {p.pedido_id for p in inviables()} <= {p.pedido_id for p in a.pedidos}
    assert len(escenario(5, 1, 7, con_inviables=False).pedidos) == 5
    assert [v.vehiculo_id for v in flota(15)][-1] == "V15-MOTO"


def test_golden_150_orders_15_vehicles_meets_rnf001():
    config = Configuracion(tiempo_limite_s=5)
    p = escenario(150, 15, 2026, config)
    s = vrptw.resolver(p)
    assert s.duracion_s <= 45
    assert violaciones(p, s) == []
    assert motivos(s) == {
        "X-CAPACIDAD": MotivoNoAsignado.EXCEDE_CAPACIDAD,
        "X-VENTANA": MotivoNoAsignado.VENTANA_INVIABLE,
    }
    assert s.comparacion is not None
    assert s.comparacion.ahorro_distancia_pct >= 10  # Acta: >= 10 % vs secuencial


# --- the independent checker catches every kind of violation ----------------


def _ruta(paradas, salida=8 * H, regreso=9 * H, descansos=()):
    return Ruta(
        "V1", tuple(paradas), salida, regreso, 0, 0, Metricas(0, 0, 0), descansos
    )


def _sol(*rutas, no_asignados=()):
    return Solucion(EstadoSolucion.COMPLETADA, rutas, no_asignados, None, 0)


def test_checker_reports_capacity_window_order_and_day_violations():
    p = problema(
        [pedido("A", kg=900, m3=5, ventana=(9 * H, 10 * H)), pedido("B")],
        [vehiculo()],
    )
    s = _sol(
        _ruta(
            [Parada(1, "A", 11 * H), Parada(2, "B", 8 * H + 30)],
            salida=7 * H,
            regreso=7 * H + 3 * H,
        )
    )
    errores = violaciones(p, s)
    assert any("kg > capacidad" in e for e in errores)
    assert any("m3 > capacidad" in e for e in errores)
    assert any("fuera de ventana" in e for e in errores)
    assert any("no cronológica" in e for e in errores)
    assert any("antes del inicio" in e for e in errores)


def test_checker_reports_rn005_violations():
    p = problema([pedido("A")], [vehiculo()])
    sin_descanso = _sol(_ruta([Parada(1, "A", 9 * H)], regreso=8 * H + 5 * H))
    assert any("sin descanso" in e for e in violaciones(p, sin_descanso))
    tramo_largo = _sol(
        _ruta(
            [Parada(1, "A", 9 * H)],
            regreso=8 * H + 10 * H,
            descansos=(Descanso(8 * H + 30, H),),
        )
    )
    errores = violaciones(p, tramo_largo)
    assert any("tramo continuo" in e for e in errores)
    assert any("excede la jornada" in e for e in errores)


def test_checker_reports_duplicates_and_missing_orders():
    p = problema([pedido("A"), pedido("B")], [vehiculo()])
    s = _sol(
        _ruta([Parada(1, "A", 9 * H)]),
        _ruta([Parada(1, "A", 9 * H)]),
        no_asignados=(NoAsignado("C", MotivoNoAsignado.SIN_VEHICULO),),
    )
    errores = violaciones(p, s)
    assert "Un pedido aparece en más de una parada" in errores
    assert any("no cuadran" in e for e in errores)
