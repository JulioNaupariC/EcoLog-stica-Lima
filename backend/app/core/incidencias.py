"""ECL-73 incident catalogues and limits: the single source for the whole backend.

Aligned with the ECL-72 BDD approved by Julio in PR #63 (I01–I16). The model,
migration 0013, schemas, service and tests import these values; a later change
means editing only this module (plus a new migration once 0013 is in ``main``).
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

# Unicode code points, inclusive; never stripped or truncated (I06, I14).
OBSERVACION_MAX = 500
# Inclusive phone-clock skew (I05, I14). No maximum age: the offline queue
# may deliver old reports (ratified by Julio in PR #63).
OCURRIDA_MAX_FUTURO = timedelta(minutes=5)
PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100
# The only state the operational list accepts (I15).
ESTADO_LISTADO = EstadoIncidencia.PENDIENTE_VALIDACION


def sql_in(values: tuple[str, ...]) -> str:
    """Quoted, comma-separated list for CHECK constraints (fixed catalogues only)."""
    return ",".join(f"'{value}'" for value in values)
