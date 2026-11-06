"""Validated order creation and public response contracts."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)


class PrioridadPedido(str, Enum):
    EXPRESS = "EXPRESS"
    ESTANDAR = "ESTANDAR"
    ECONOMICO = "ECONOMICO"


class PedidoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    cliente_id: UUID
    direccion: str = Field(min_length=1, max_length=255)
    referencia: str | None = Field(default=None, min_length=1, max_length=255)
    latitud: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitud: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)
    peso_kg: Decimal = Field(gt=0, allow_inf_nan=False, max_digits=10, decimal_places=2)
    volumen_m3: Decimal = Field(
        gt=0, allow_inf_nan=False, max_digits=10, decimal_places=3
    )
    ventana_inicio: AwareDatetime
    ventana_fin: AwareDatetime
    prioridad: PrioridadPedido
    tipo_producto: str = Field(min_length=1, max_length=20)

    @field_validator("direccion", "referencia", "tipo_producto", mode="before")
    @classmethod
    def trim_text(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def valid_order(self) -> "PedidoCreate":
        has_latitude = self.latitud is not None
        has_longitude = self.longitud is not None
        if has_latitude != has_longitude:
            raise ValueError("latitud y longitud deben enviarse juntas")
        if not has_latitude and self.referencia is None:
            raise ValueError("Se requiere coordenadas o referencia")
        return self

    @field_validator("ventana_fin")
    @classmethod
    def window_after_start(cls, value: datetime, info: ValidationInfo) -> datetime:
        # ECL-84: a field error keeps loc ["body", "ventana_fin"], so the
        # sanitized 422 stays actionable without echoing the value.
        inicio = info.data.get("ventana_inicio")
        if inicio is not None and value <= inicio:
            raise ValueError("ventana_fin debe ser posterior a ventana_inicio")
        return value


class PedidoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pedido_id: UUID
    cliente_id: UUID
    direccion: str
    referencia: str | None
    latitud: float | None
    longitud: float | None
    peso_kg: Decimal
    volumen_m3: Decimal
    ventana_inicio: AwareDatetime
    ventana_fin: AwareDatetime
    prioridad: PrioridadPedido
    tipo_producto: str
    estado: str
