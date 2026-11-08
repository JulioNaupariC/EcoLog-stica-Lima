"""EN-008 (ECL-26): pure calculations, with values worked out by hand.

These are unit checks of the formulas. The 20 independent reference cases of
RNF-011 live in ``tests/unit/test_casos_referencia_rnf011.py``.
"""

from decimal import Decimal

import pytest

from app.core import calculos
from app.core.parametros import REFERENCIA_INICIAL, REQUERIDOS, UNIDADES

PARAMETROS = {
    "PRECIO_COMBUSTIBLE_GALON": Decimal("17.50"),
    "LITROS_POR_GALON": Decimal("3.785411784"),
    "COSTO_MANTENIMIENTO_KM": Decimal("1.20"),
}


def test_fuel_and_emissions_follow_rn011_and_rn013():
    # 120 km / 10 km/L = 12 L; 120 km x 0.3 kg/km = 36 kg CO2.
    assert calculos.combustible_l(120, Decimal("10")) == pytest.approx(12.0)
    assert calculos.co2_kg(120, Decimal("0.3")) == pytest.approx(36.0)


def test_fuel_cost_converts_litres_to_gallons_before_the_price():
    # 37.85411784 L = 10 gal exactly; 10 gal x S/ 17.50 = S/ 175.00.
    costo = calculos.costo_combustible_soles(
        37.85411784, Decimal("17.50"), Decimal("3.785411784")
    )
    assert abs(costo - 175.0) <= 1e-9
    # Multiplying litres by the gallon price would give 662.45: never that.
    assert abs(costo - 37.85411784 * 17.5) > 400


def test_route_cost_is_fuel_plus_maintenance():
    # 100 km, 10 km/L -> 10 L -> 2.641720524 gal -> S/ 46.230109...
    # maintenance 100 km x 1.20 = S/ 120.00; total S/ 166.230109...
    costo = calculos.costo_ruta_soles(100, Decimal("10"), PARAMETROS)
    assert abs(costo - (10 / 3.785411784 * 17.5 + 120)) <= 1e-9
    assert abs(costo - 166.23) <= 0.01


def test_offset_needs_a_capture_factor_rn014():
    assert calculos.arboles_equivalentes(100, PARAMETROS) is None
    con_factor = {**PARAMETROS, "CAPTURA_CO2_ARBOL_ANIO": Decimal("20")}
    assert calculos.arboles_equivalentes(100, con_factor) == pytest.approx(5.0)


def test_zero_distance_is_valid_and_gives_zero():
    assert calculos.combustible_l(0, 10) == 0
    assert calculos.co2_kg(0, 0.3) == 0
    assert calculos.costo_ruta_soles(0, Decimal("10"), PARAMETROS) == 0


@pytest.mark.parametrize(
    "funcion,args",
    [
        (calculos.combustible_l, (-1, 10)),
        (calculos.combustible_l, (10, 0)),
        (calculos.co2_kg, (10, -0.1)),
        (calculos.costo_combustible_soles, (10, 17.5, 0)),
        (calculos.costo_combustible_soles, (-1, 17.5, 3.78)),
        (calculos.costo_mantenimiento_soles, (10, -1)),
        (calculos.combustible_l, (float("nan"), 10)),
    ],
)
def test_invalid_inputs_are_rejected(funcion, args):
    with pytest.raises(ValueError):
        funcion(*args)


def test_reference_set_is_complete_and_sourced():
    codigos = [valor.codigo for valor in REFERENCIA_INICIAL]
    assert set(REQUERIDOS) <= set(codigos)
    assert all(valor.fuente.strip() for valor in REFERENCIA_INICIAL)
    assert set(codigos) <= set(UNIDADES)
    galon = next(v for v in REFERENCIA_INICIAL if v.codigo == "LITROS_POR_GALON")
    assert galon.valor == Decimal("3.785411784")
