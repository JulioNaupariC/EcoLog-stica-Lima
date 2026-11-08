"""EN-008 (ECL-26): pure fuel, emission, cost and offset calculations.

Units are explicit and nothing is rounded (RNF-011, BDD US-006 decision 7):
rounding is only for presentation. Fuel price is per gallon (RN-011), so
litres are converted with the versioned ``LITROS_POR_GALON`` factor (decision
8). The 20 reference cases that validate these functions are calculated by
hand, independently of this code.
"""

from collections.abc import Mapping
from decimal import Decimal


def _positivo(nombre: str, valor: float | Decimal) -> float:
    numero = float(valor)
    if not numero > 0:
        raise ValueError(f"{nombre} debe ser mayor que 0")
    return numero


def _no_negativo(nombre: str, valor: float | Decimal) -> float:
    numero = float(valor)
    if not numero >= 0:
        raise ValueError(f"{nombre} no puede ser negativo")
    return numero


def combustible_l(distancia_km: float, rendimiento_km_l: float | Decimal) -> float:
    """RN-011: litres = km / vehicle efficiency (km/L)."""
    return _no_negativo("distancia_km", distancia_km) / _positivo(
        "rendimiento_km_l", rendimiento_km_l
    )


def co2_kg(distancia_km: float, factor_co2_kg_km: float | Decimal) -> float:
    """RN-013: kg CO2 = km x vehicle emission factor (kg CO2/km)."""
    return _no_negativo("distancia_km", distancia_km) * _no_negativo(
        "factor_co2_kg_km", factor_co2_kg_km
    )


def costo_combustible_soles(
    litros: float,
    precio_galon: float | Decimal,
    litros_por_galon: float | Decimal,
) -> float:
    """RN-011: litres -> gallons with the versioned factor, times PEN/gal."""
    galones = _no_negativo("litros", litros) / _positivo(
        "litros_por_galon", litros_por_galon
    )
    return galones * _no_negativo("precio_galon", precio_galon)


def costo_mantenimiento_soles(distancia_km: float, costo_km: float | Decimal) -> float:
    """RN-012: km x PEN/km."""
    return _no_negativo("distancia_km", distancia_km) * _no_negativo(
        "costo_km", costo_km
    )


def costo_ruta_soles(
    distancia_km: float,
    rendimiento_km_l: float | Decimal,
    parametros: Mapping[str, Decimal],
) -> float:
    """BDD US-006: fuel + maintenance with one parameter version."""
    litros = combustible_l(distancia_km, rendimiento_km_l)
    return costo_combustible_soles(
        litros,
        parametros["PRECIO_COMBUSTIBLE_GALON"],
        parametros["LITROS_POR_GALON"],
    ) + costo_mantenimiento_soles(distancia_km, parametros["COSTO_MANTENIMIENTO_KM"])


def arboles_equivalentes(
    co2_total_kg: float, parametros: Mapping[str, Decimal]
) -> float | None:
    """RN-014: trees per year that capture the CO2; None without a factor.

    It is an equivalence for display, never a certified credit.
    """
    factor = parametros.get("CAPTURA_CO2_ARBOL_ANIO")
    if factor is None:
        return None
    return _no_negativo("co2_total_kg", co2_total_kg) / _positivo(
        "CAPTURA_CO2_ARBOL_ANIO", factor
    )
