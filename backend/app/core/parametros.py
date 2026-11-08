"""EN-008 (ECL-26): catalogue of versioned calculation parameters (RNF-011).

Each code has one fixed unit. A version is a complete set of the required
codes plus any optional ones, with a single validity start; a new version
closes the previous one and nothing is deleted, so every optimization and
report can be recalculated with the parameters it used.

Vehicle emission factors and fuel efficiency are not here: RN-013 takes them
from each vehicle, and the optimization snapshot keeps the values used.
"""

from dataclasses import dataclass
from decimal import Decimal

# code -> unit. The unit is part of the contract: a value never changes unit.
UNIDADES = {
    "PRECIO_COMBUSTIBLE_GALON": "PEN/gal",  # RN-011
    "LITROS_POR_GALON": "L/gal",  # BDD US-006 v1.0.0, decision 8
    "COSTO_MANTENIMIENTO_KM": "PEN/km",  # RN-012
    "CAPTURA_CO2_ARBOL_ANIO": "kgCO2/arbol/anio",  # RN-014, optional
}
REQUERIDOS = (
    "PRECIO_COMBUSTIBLE_GALON",
    "LITROS_POR_GALON",
    "COSTO_MANTENIMIENTO_KM",
)
OPCIONALES = ("CAPTURA_CO2_ARBOL_ANIO",)
VERSION_MAX = 40
FUENTE_MAX = 300
NOTA_MAX = 300


@dataclass(frozen=True)
class ValorReferencia:
    codigo: str
    valor: Decimal
    fuente: str


# Initial reference set, only with values that already have a documented
# origin. Market sources are pending (Julio, ECL-26); no factor is invented.
REFERENCIA_INICIAL = (
    ValorReferencia(
        "PRECIO_COMBUSTIBLE_GALON",
        Decimal("17.50"),
        "Reglas de negocio V_1_1_0, RN-011: valor inicial de referencia del "
        "proyecto para diésel; pendiente de fuente de mercado verificable.",
    ),
    ValorReferencia(
        "LITROS_POR_GALON",
        Decimal("3.785411784"),
        "Galón estadounidense = 231 in³ = 3,785411784 L (definición exacta). "
        "NIST Handbook 44, Apéndice C (General Tables of Units of Measurement).",
    ),
    ValorReferencia(
        "COSTO_MANTENIMIENTO_KM",
        Decimal("1.20"),
        "Reglas de negocio V_1_1_0, RN-012: valor inicial de referencia del "
        "proyecto; pendiente de fuente de mercado verificable.",
    ),
)


def sql_in(values: tuple[str, ...]) -> str:
    return ",".join(f"'{value}'" for value in values)


def unidad_valida_sql() -> str:
    """CHECK body tying each code to its only unit."""
    return " OR ".join(
        f"(codigo = '{codigo}' AND unidad = '{unidad}')"
        for codigo, unidad in UNIDADES.items()
    )
