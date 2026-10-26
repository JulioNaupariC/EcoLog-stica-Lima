"""ECL-73 incident contracts (provisional until the ECL-72 BDD is approved)."""

from datetime import datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.core.incidencias import (
    OBSERVACION_MAX,
    PAGE_SIZE_MAX,
    EstadoIncidencia,
    SeveridadIncidencia,
    TipoIncidencia,
)


class IncidenciaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    operation_id: UUID
    tipo: TipoIncidencia
    severidad: SeveridadIncidencia
    # Timezone required; the time window is checked by the service against "now".
    ocurrida_en: AwareDatetime
    latitud: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitud: float = Field(ge=-180, le=180, allow_inf_nan=False)
    parada_id: UUID | None = None
    observacion: str | None = Field(default=None, max_length=OBSERVACION_MAX)

    @field_validator("observacion")
    @classmethod
    def blank_is_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


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
    observacion: str | None
    estado: EstadoIncidencia


class IncidenciaPage(BaseModel):
    items: list[IncidenciaListItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=PAGE_SIZE_MAX)
    total: int = Field(ge=0)
