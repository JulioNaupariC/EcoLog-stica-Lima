"""Vehicle request and response contracts."""

from decimal import Decimal
from enum import Enum
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TipoVehiculo(str, Enum):
    CAMIONETA = "CAMIONETA"
    FURGON = "FURGON"
    MOTO = "MOTO"


Positive2 = Annotated[
    Decimal, Field(gt=0, allow_inf_nan=False, max_digits=10, decimal_places=2)
]
Positive3 = Annotated[
    Decimal, Field(gt=0, allow_inf_nan=False, max_digits=10, decimal_places=3)
]
NonNegative5 = Annotated[
    Decimal, Field(ge=0, allow_inf_nan=False, max_digits=10, decimal_places=5)
]
Year = Annotated[int, Field(ge=1980, le=2100)]


class _VehicleInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    @field_validator("placa", mode="before", check_fields=False)
    @classmethod
    def normalize_plate(cls, value: Any) -> Any:
        return value.strip().upper() if isinstance(value, str) else value


class VehicleCreate(_VehicleInput):
    placa: str = Field(min_length=1, max_length=10)
    tipo: TipoVehiculo
    capacidad_kg: Positive2
    capacidad_m3: Positive2
    rendimiento_km_l: Positive3
    factor_co2_kg_km: NonNegative5
    anio_fabricacion: Year


class VehicleUpdate(_VehicleInput):
    placa: str | None = Field(default=None, min_length=1, max_length=10)
    tipo: TipoVehiculo | None = None
    capacidad_kg: Positive2 | None = None
    capacidad_m3: Positive2 | None = None
    rendimiento_km_l: Positive3 | None = None
    factor_co2_kg_km: NonNegative5 | None = None
    anio_fabricacion: Year | None = None

    @model_validator(mode="before")
    @classmethod
    def require_nonempty_nonnull_patch(cls, value: Any) -> Any:
        if isinstance(value, dict):
            if not value or any(item is None for item in value.values()):
                raise ValueError("PATCH requires non-null fields")
        return value


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vehiculo_id: UUID
    placa: str
    tipo: TipoVehiculo
    capacidad_kg: Decimal
    capacidad_m3: Decimal
    rendimiento_km_l: Decimal
    factor_co2_kg_km: Decimal
    anio_fabricacion: int
    estado: str
