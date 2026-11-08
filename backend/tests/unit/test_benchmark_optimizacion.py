"""EN-003 (ECL-21): pure parts of the RNF-001 benchmark, without a database."""

import pytest

from scripts._guard import TargetRefused
from scripts.benchmark_optimizacion import (
    CORRIDAS_RNF001,
    ejecutar,
    percentil,
    resumir,
    violaciones,
)

V1 = "00000000-0000-0000-0000-000000000001"


def parada(pedido, eta="2026-11-16T10:00:00-05:00"):
    return {
        "pedido_id": pedido,
        "eta": eta,
        "ventana_inicio": "2026-11-16T09:00:00-05:00",
        "ventana_fin": "2026-11-16T11:00:00-05:00",
    }


def detalle(paradas, peso=100.0, omitidos=()):
    return {
        "rutas": [{"vehiculo": {"vehiculo_id": V1}, "peso_kg": peso, "paradas": paradas}],
        "no_asignados": [{"pedido_id": p} for p in omitidos],
    }


def fila(post_s, estado=201, violaciones=""):
    return {
        "estado_http": estado,
        "post_s": post_s,
        "total_s": post_s + 0.05,
        "motor_s": post_s - 0.2,
        "servidos": 148,
        "no_asignados": 2,
        "violaciones": violaciones,
    }


@pytest.mark.parametrize(
    ("valores", "p", "esperado"),
    [([3, 1, 2], 50, 2), (list(range(1, 31)), 95, 29), ([7.5], 95, 7.5)],
)
def test_nearest_rank_percentile(valores, p, esperado):
    assert percentil(valores, p) == esperado


def test_percentile_needs_values():
    with pytest.raises(ValueError):
        percentil([], 95)


def test_feasible_answer_has_no_violations():
    assert violaciones(detalle([parada("a"), parada("b")]), {V1: 800.0}) == []


def test_violations_are_reported_by_kind():
    respuesta = detalle(
        [parada("a", eta="2026-11-16T12:00:00-05:00"), parada("b"), parada("b")],
        peso=900.0,
        omitidos=["b"],
    )
    assert violaciones(respuesta, {V1: 800.0}) == [
        f"capacidad:{V1}",
        "ventana:a",
        "duplicado:b",
        "servido_y_omitido:b",
    ]


def test_thirty_clean_runs_under_45_s_meet_rnf001():
    resumen = resumir([fila(20.0 + i / 10) for i in range(CORRIDAS_RNF001)])
    assert resumen["cumple_rnf001"] is True
    assert resumen["post_s"]["p95"] == pytest.approx(22.8)
    assert resumen["servidos_min"] == 148 and resumen["fallidas"] == 0


@pytest.mark.parametrize(
    "filas",
    [
        [fila(20.0)] * (CORRIDAS_RNF001 - 1),  # too few runs
        [fila(20.0)] * 29 + [fila(1.0, estado=503)],  # a failure counts
        [fila(20.0)] * 29 + [fila(20.0, violaciones="ventana:a")],
        [fila(20.0)] * 28 + [fila(46.0)] * 2,  # p95 over the limit
    ],
)
def test_rnf001_is_not_met_otherwise(filas):
    assert resumir(filas)["cumple_rnf001"] is False


def test_only_failures_have_no_timings():
    assert resumir([fila(1.0, estado=503)]) == {
        "corridas": 1,
        "exitosas": 0,
        "fallidas": 1,
        "con_violaciones": 0,
        "cumple_rnf001": False,
    }


def test_refuses_non_disposable_databases(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/ecologistica"
    )
    monkeypatch.delenv("APP_ENV", raising=False)
    with pytest.raises(TargetRefused):
        ejecutar(["--salida", str(tmp_path)])
