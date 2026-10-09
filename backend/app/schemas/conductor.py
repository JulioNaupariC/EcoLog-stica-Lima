"""Validated driver contracts; credentials are write-only."""

from datetime import date, datetime, timezone
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

Name = Annotated[str, Field(min_length=1, max_length=160)]
Dni = Annotated[str, Field(pattern=r"^[0-9]{8}$")]
License = Annotated[str, Field(min_length=1, max_length=20)]
Phone = Annotated[str, Field(pattern=r"^\+[1-9][0-9]{7,14}$")]
Experience = Annotated[int, Field(strict=True, ge=0, le=2147483647)]
StartingPoint = Annotated[str, Field(min_length=1, max_length=255)]


class _DriverInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    @field_validator(
        "nombre",
        "dni",
        "licencia_numero",
        "telefono",
        "punto_partida",
        "email",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("licencia_numero", check_fields=False)
    @classmethod
    def normalize_license(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @field_validator("disponible_desde", "disponible_hasta", check_fields=False)
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("La disponibilidad requiere zona horaria")
            return value.astimezone(timezone.utc)
        return None


class ConductorData(_DriverInput):
    nombre: Name
    dni: Dni
    licencia_numero: License
    licencia_vigente_hasta: date
    experiencia_anios: Experience
    telefono: Phone
    punto_partida: StartingPoint
    disponible_desde: datetime | None
    disponible_hasta: datetime | None

    @model_validator(mode="after")
    def validate_interval(self) -> "ConductorData":
        start, end = self.disponible_desde, self.disponible_hasta
        if (start is None) != (end is None):
            raise ValueError("La disponibilidad requiere ambos extremos")
        if start is not None and end is not None and end <= start:
            raise ValueError("El final debe ser posterior al inicio")
        return self


class ConductorCreate(ConductorData):
    email: str = Field(
        min_length=3, max_length=255, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )
    password: SecretStr = Field(min_length=1, max_length=1024)

    @model_validator(mode="after")
    def require_initial_interval(self) -> "ConductorCreate":
        if self.disponible_desde is None:
            raise ValueError("El alta requiere disponibilidad completa")
        return self


class ConductorUpdate(_DriverInput):
    nombre: Name | None = None
    dni: Dni | None = None
    licencia_numero: License | None = None
    licencia_vigente_hasta: date | None = None
    experiencia_anios: Experience | None = None
    telefono: Phone | None = None
    punto_partida: StartingPoint | None = None
    disponible_desde: datetime | None = None
    disponible_hasta: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_patch(cls, value: object) -> object:
        if isinstance(value, dict):
            if not value:
                raise ValueError("La actualización requiere campos")
            interval = {"disponible_desde", "disponible_hasta"}
            if len(interval.intersection(value)) == 1:
                raise ValueError("Actualizar ambos extremos de disponibilidad")
            if any(item is None for key, item in value.items() if key not in interval):
                raise ValueError("Los campos del perfil no admiten null")
        return value


class ConductorSummary(BaseModel):
    conductor_id: UUID
    usuario_id: UUID
    nombre: str
    disponible_desde: datetime | None
    disponible_hasta: datetime | None
    estado: str
    habilitado_asignacion: bool


class ConductorResponse(ConductorSummary):
    dni: str
    licencia_numero: str
    licencia_vigente_hasta: date
    experiencia_anios: int
    telefono: str
    punto_partida: str


class ConductorListItem(BaseModel):
    conductor_id: UUID
    nombre: str
    disponible_desde: datetime | None
    disponible_hasta: datetime | None
    estado: str
    habilitado_asignacion: bool


class ConductorPage(BaseModel):
    items: list[ConductorListItem]
    page: int
    page_size: int
    total: int
