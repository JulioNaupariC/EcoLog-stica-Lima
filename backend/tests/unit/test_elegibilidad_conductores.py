"""ECL-79 D3/F1/F2: driving/availability/licence boundaries at assignment."""

from dataclasses import replace
from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest

from app.optimizacion.elegibilidad import PlanRuta, cumple_rn005, plan_de_ruta
from app.optimizacion.modelo import (
    Configuracion,
    Descanso,
    Metricas,
    Parada,
    PedidoVRP,
    Problema,
    Punto,
    Ruta,
)
from app.repositories.optimizaciones import ConductorElegible
from app.services.optimizaciones import (
    asignar_conductores,
    evaluar_asignaciones,
    medianoche,
)

FECHA = date(2026, 11, 9)
BASE = medianoche(FECHA)


def momento(minutos):
    return BASE + timedelta(minutes=minutos)


def plan(tramos, descansos=(), salida=480, regreso=None):
    regreso = regreso if regreso is not None else max(b for _, b in tramos)
    return PlanRuta(
        momento(salida),
        momento(regreso),
        tuple((momento(a), momento(b)) for a, b in tramos),
        tuple((momento(a), momento(b)) for a, b in descansos),
    )


def conductor(**cambios):
    return replace(
        ConductorElegible(uuid4(), BASE, BASE + timedelta(days=3), FECHA),
        **cambios,
    )


@pytest.mark.parametrize("minutos,esperado", [(239, True), (240, True), (241, False)])
def test_F2_borde_cuatro_horas_sin_descanso(minutos, esperado):
    ruta = plan([(480, 480 + minutos)])
    chofer = conductor()
    assert cumple_rn005(ruta) is esperado
    assert asignar_conductores([ruta], [chofer]) == [
        chofer.conductor_id if esperado else None
    ]


@pytest.mark.parametrize("pausa,esperado", [(59, False), (60, True), (61, True)])
def test_F2_descanso_exacto_reinicia_conduccion(pausa, esperado):
    ruta = plan([(480, 720), (720 + pausa, 721 + pausa)], [(720, 720 + pausa)])
    assert cumple_rn005(ruta) is esperado


@pytest.mark.parametrize("extra,esperado", [(0, True), (1, False)])
def test_F1_ocho_horas_admitidas_ocho_horas_un_minuto_rechazadas(extra, esperado):
    ruta = plan(
        [(480, 720), (780, 1020), (1080, 1080 + extra)]
        if extra
        else [(480, 720), (780, 1020)],
        [(720, 780), (1020, 1080)] if extra else [(720, 780)],
    )
    chofer = conductor()
    assert cumple_rn005(ruta) is esperado
    assert asignar_conductores([ruta], [chofer]) == [
        chofer.conductor_id if esperado else None
    ]


def test_F2_espera_o_servicio_no_se_convierten_en_descanso():
    assert not cumple_rn005(plan([(480, 720), (780, 781)]))
    assert cumple_rn005(plan([(480, 600), (1000, 1100)], regreso=1200))


@pytest.mark.parametrize(
    "tramos,pausas,regreso",
    [
        ([(480, 500), (490, 510)], [], 520),
        ([(480, 500)], [(490, 510)], 520),
        ([(480, 500)], [(400, 460)], 520),
        ([(480, 500)], [(500, 550)], 520),
        ([(480, 500)], [(500, 500)], 520),
        ([(480, 500)], [(500, 515), (510, 520)], 520),
        ([(480, 500)], [], 490),
        ([(480, 480)], [], 480),
    ],
)
def test_cronologia_invalida_no_autoriza_asignacion(tramos, pausas, regreso):
    ruta = plan(tramos, pausas, regreso=regreso)
    assert not cumple_rn005(ruta)
    assert asignar_conductores([ruta], [conductor()]) == [None]


@pytest.mark.parametrize(
    "inicio,fin,esperado",
    [
        ("2026-11-10T04:00:00+00:00", "2026-11-10T04:59:59+00:00", True),
        ("2026-11-10T04:00:00+00:00", "2026-11-10T05:00:00+00:00", True),
        ("2026-11-10T04:00:00+00:00", "2026-11-10T05:00:01+00:00", False),
        ("2026-11-10T05:00:00+00:00", "2026-11-10T06:00:00+00:00", False),
        ("2026-11-09T23:00:00-05:00", "2026-11-10T00:30:00-05:00", False),
    ],
)
def test_D3_licencia_ultimo_dia_lima_y_cruce_medianoche(inicio, fin, esperado):
    a, b = datetime.fromisoformat(inicio), datetime.fromisoformat(fin)
    ruta = PlanRuta(a, b, ((a, b),))
    chofer = conductor()
    assert asignar_conductores([ruta], [chofer]) == [
        chofer.conductor_id if esperado else None
    ]


def test_D3_se_evalua_conduccion_y_no_fecha_de_consulta_o_espera_final():
    ruta = plan([(23 * 60, 24 * 60)], salida=23 * 60, regreso=25 * 60)
    chofer = conductor()
    assert asignar_conductores([ruta], [chofer]) == [chofer.conductor_id]
    assert asignar_conductores(
        [ruta], [conductor(licencia_vigente_hasta=FECHA - timedelta(days=1))]
    ) == [None]
    assert asignar_conductores(
        [ruta], [conductor(licencia_vigente_hasta=date.max)]
    ) != [None]


@pytest.mark.parametrize(
    "inicio,fin,esperado", [(480, 600, True), (481, 600, False), (480, 599, False)]
)
def test_disponibilidad_cubre_toda_ruta_con_bordes_exactos(inicio, fin, esperado):
    ruta = plan([(480, 600)])
    chofer = conductor(disponible_desde=momento(inicio), disponible_hasta=momento(fin))
    assert asignar_conductores([ruta], [chofer]) == [
        chofer.conductor_id if esperado else None
    ]


def test_ruta_invalida_no_consume_conductor_y_cada_conductor_se_usa_una_vez():
    chofer = conductor()
    valida = plan([(480, 600)])
    invalida = plan([(480, 721)])
    assert asignar_conductores([None, invalida, valida, valida], [chofer]) == [
        None,
        None,
        chofer.conductor_id,
        None,
    ]
    assert asignar_conductores([valida], []) == [None]


def escenario(*, eta=600, regreso=720, descansos=(), ubicacion=Punto(0, 0.1)):
    problema = Problema(
        Punto(0, 0),
        (PedidoVRP("p", ubicacion, 1, 1, 0, 2000),),
        (),
        Configuracion(velocidad_kmh=60, factor_desvio=1, servicio_min=5),
    )
    ruta = Ruta(
        "v", (Parada(1, "p", eta),), 480, regreso, 1, 1, Metricas(1, 1, 1), descansos
    )
    return problema, ruta


def test_plan_separa_conduccion_servicio_y_espera_con_tiempos_de_matriz():
    problema, ruta = escenario(eta=1000, regreso=1100)
    prevista = plan_de_ruta(problema, ruta, BASE)
    # 11.12 km at 60 km/h, rounded up: 12 min in each direction, not 620 min.
    assert prevista.conduccion == (
        (momento(480), momento(492)),
        (momento(1005), momento(1017)),
    )
    assert cumple_rn005(prevista)


def test_plan_interrumpe_conduccion_con_descanso_y_conserva_servicio():
    problema, ruta = escenario(descansos=(Descanso(485, 60),))
    prevista = plan_de_ruta(problema, ruta, BASE)
    assert prevista.conduccion[:2] == (
        (momento(480), momento(485)),
        (momento(545), momento(552)),
    )
    assert cumple_rn005(prevista)


@pytest.mark.parametrize(
    "cambios",
    [
        {"eta": 481},
        {"regreso": 605},
        {"eta": 470},
        {"descansos": (Descanso(600, 60),)},
        {"descansos": (Descanso(479, 60),)},
        {"descansos": (Descanso(710, 60),)},
        {"descansos": (Descanso(500, 0),)},
        {"descansos": (Descanso(500, 60), Descanso(550, 60))},
        {"ubicacion": None},
    ],
)
def test_plan_no_asigna_si_eta_servicio_o_descanso_son_incompatibles(cambios):
    problema, ruta = escenario(**cambios)
    assert plan_de_ruta(problema, ruta, BASE) is None


def test_plan_no_confia_en_pedidos_desconocidos():
    problema, ruta = escenario()
    ruta = replace(ruta, paradas=(Parada(1, "desconocido", 600),))
    assert plan_de_ruta(problema, ruta, BASE) is None


@pytest.mark.parametrize(
    "caso,motivo",
    [
        ("licencia", "LICENCIA_VENCIDA"),
        ("disponibilidad", "DISPONIBILIDAD_INSUFICIENTE"),
        ("sin-disponibilidad", "DISPONIBILIDAD_INSUFICIENTE"),
        ("jornada", "JORNADA_INVIABLE"),
        ("sin-plan", "JORNADA_INVIABLE"),
        ("sin-candidatos", "SIN_CONDUCTOR_ELEGIBLE"),
    ],
)
def test_motivo_publico_refleja_causa_verificada(caso, motivo):
    ruta = plan([(480, 600)])
    chofer = conductor()
    if caso == "licencia":
        chofer = replace(chofer, licencia_vigente_hasta=FECHA - timedelta(days=1))
    elif caso == "disponibilidad":
        chofer = replace(chofer, disponible_hasta=momento(590))
    elif caso == "sin-disponibilidad":
        chofer = replace(chofer, disponible_desde=None, disponible_hasta=None)
    elif caso == "jornada":
        ruta = plan([(480, 721)])
    elif caso == "sin-plan":
        ruta = None
    resultado = evaluar_asignaciones(
        [ruta], [] if caso == "sin-candidatos" else [chofer]
    )[0]
    assert resultado.conductor_id is None
    assert resultado.motivo.value == motivo
