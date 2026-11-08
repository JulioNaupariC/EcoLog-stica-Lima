"""RNF-011 / EN-008: |calculated - reference| <= 0.01 on 20 reference cases.

The cases are written by hand (Julio, ECL-26), independently of the code, in
``docs/03 Implementación/Sprint 04/ECL-26 casos de referencia RNF-011.csv``.
While fewer than 20 exist, completeness is reported as skipped, never passed.
"""

import csv
from decimal import Decimal
from pathlib import Path

import pytest

from app.core import calculos

CASOS = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "03 Implementación"
    / "Sprint 04"
    / "ECL-26 casos de referencia RNF-011.csv"
)
TOLERANCIA = 0.01
COLUMNAS = (
    "caso",
    "descripcion",
    "distancia_km",
    "rendimiento_km_l",
    "factor_co2_kg_km",
    "precio_combustible_galon",
    "litros_por_galon",
    "costo_mantenimiento_km",
    "captura_co2_arbol_anio",
    "esperado_combustible_l",
    "esperado_co2_kg",
    "esperado_costo_soles",
    "esperado_arboles",
    "calculado_por",
    "herramienta",
)


def _filas() -> list[dict[str, str]]:
    with CASOS.open(encoding="utf-8", newline="") as archivo:
        lector = csv.DictReader(archivo)
        assert tuple(lector.fieldnames or ()) == COLUMNAS
        return list(lector)


FILAS = _filas()


def test_reference_file_has_the_agreed_columns():
    assert CASOS.exists()


def test_rnf011_has_twenty_reference_cases():
    if len(FILAS) < 20:
        pytest.skip(f"Pendiente (ECL-26, Julio): {len(FILAS)}/20 casos de referencia")
    assert len({fila["caso"] for fila in FILAS}) == len(FILAS)


@pytest.mark.parametrize("fila", FILAS, ids=[fila["caso"] for fila in FILAS])
def test_reference_case_within_tolerance(fila):
    km = float(fila["distancia_km"])
    parametros = {
        "PRECIO_COMBUSTIBLE_GALON": Decimal(fila["precio_combustible_galon"]),
        "LITROS_POR_GALON": Decimal(fila["litros_por_galon"]),
        "COSTO_MANTENIMIENTO_KM": Decimal(fila["costo_mantenimiento_km"]),
    }
    if fila["captura_co2_arbol_anio"]:
        parametros["CAPTURA_CO2_ARBOL_ANIO"] = Decimal(fila["captura_co2_arbol_anio"])
    litros = calculos.combustible_l(km, Decimal(fila["rendimiento_km_l"]))
    co2 = calculos.co2_kg(km, Decimal(fila["factor_co2_kg_km"]))
    costo = calculos.costo_ruta_soles(km, Decimal(fila["rendimiento_km_l"]), parametros)
    assert abs(litros - float(fila["esperado_combustible_l"])) <= TOLERANCIA
    assert abs(co2 - float(fila["esperado_co2_kg"])) <= TOLERANCIA
    assert abs(costo - float(fila["esperado_costo_soles"])) <= TOLERANCIA
    arboles = calculos.arboles_equivalentes(co2, parametros)
    if fila["esperado_arboles"]:
        assert arboles is not None
        assert abs(arboles - float(fila["esperado_arboles"])) <= TOLERANCIA
    else:
        assert arboles is None
