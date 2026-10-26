"""ECL-73 incident catalogues and limits: the single source for the whole backend.

Provisional contract until the ECL-72 BDD is approved. The model, migration
0013, schemas, service and tests import these values; adjusting the BDD means
changing only this module (plus a new migration once 0013 is in ``main``).
"""

from datetime import timedelta
from enum import Enum


class TipoIncidencia(str, Enum):
    TRAFICO = "TRAFICO"
    AVERIA = "AVERIA"
    ACCIDENTE = "ACCIDENTE"
    CLIMA = "CLIMA"
    SEGURIDAD = "SEGURIDAD"
    OTRO = "OTRO"


class SeveridadIncidencia(str, Enum):
    BAJA = "BAJA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"


class EstadoIncidencia(str, Enum):
    PENDIENTE_VALIDACION = "PENDIENTE_VALIDACION"
    VALIDADA = "VALIDADA"
    DESCARTADA = "DESCARTADA"


TIPOS = tuple(item.value for item in TipoIncidencia)
SEVERIDADES = tuple(item.value for item in SeveridadIncidencia)
ESTADOS = tuple(item.value for item in EstadoIncidencia)

OBSERVACION_MAX = 500
# Provisional (agreed with the team on 25/10/2026) until ECL-72 fixes it.
OCURRIDA_MAX_ANTIGUEDAD = timedelta(hours=24)
OCURRIDA_MAX_FUTURO = timedelta(minutes=5)
PAGE_SIZE_MAX = 100


def sql_in(values: tuple[str, ...]) -> str:
    """Quoted, comma-separated list for CHECK constraints (fixed catalogues only)."""
    return ",".join(f"'{value}'" for value in values)
