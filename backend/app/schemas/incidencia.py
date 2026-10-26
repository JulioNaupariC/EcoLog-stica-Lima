"""ECL-73 incident contracts, aligned with the approved ECL-72 BDD (PR #63)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    UUID4,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.core.incidencias import (
    OBSERVACION_MAX,
    PAGE_SIZE_MAX,
    EstadoIncidencia,
    SeveridadIncidencia,
    TipoIncidencia,
)

# I07: finite numbers only; integers are accepted, strings and booleans are not.
Latitud = Annotated[float, Field(strict=True, ge=-90, le=90, allow_inf_nan=False)]
Longitud = Annotated[float, Field(strict=True, ge=-180, le=180, allow_inf_nan=False)]


class IncidenciaCreate(BaseModel):
    # Extra fields (conductor_id, usuario_id, reportada_por, ruta_id, estado) → 422.
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    operation_id: UUID4
    tipo: TipoIncidencia
    severidad: SeveridadIncidencia
    # Timezone required; the future tolerance is checked against the server clock.
    ocurrida_en: AwareDatetime
    latitud: Latitud
    longitud: Longitud
    parada_id: UUID | None = None
    # Code points, never stripped or truncated; omitted or null means "" (I06, I14).
    observacion: str = Field(default="", max_length=OBSERVACION_MAX)

    @field_validator("observacion", mode="before")
    @classmethod
    def null_is_empty(cls, value: object) -> object:
        return "" if value is None else value


class IncidenciaRegistrada(BaseModel):
    incidencia_id: UUID
    operation_id: UUID
    estado: EstadoIncidencia
    registrada_en: datetime


class ConductorResumen(BaseModel):
    """Only the identifier and name: no DNI, phone or licence."""

    conductor_id: UUID
    nombre: str


class IncidenciaListItem(BaseModel):
    incidencia_id: UUID
    tipo: TipoIncidencia
    severidad: SeveridadIncidencia
    ocurrida_en: datetime
    registrada_en: datetime
    conductor: ConductorResumen
    latitud: float
    longitud: float
    observacion: str
    estado: EstadoIncidencia


class IncidenciaPage(BaseModel):
    items: list[IncidenciaListItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=PAGE_SIZE_MAX)
    total: int = Field(ge=0)
