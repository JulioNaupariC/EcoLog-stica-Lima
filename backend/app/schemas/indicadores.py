"""Operational aggregates for the home dashboard; no personal data."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class VehiculosIndicadores(BaseModel):
    total: int = Field(ge=0)
    activos: int = Field(ge=0)
    capacidad_kg_activa: Decimal = Field(ge=0)


class ConductoresIndicadores(BaseModel):
    total: int = Field(ge=0)
    habilitados_asignacion: int = Field(ge=0)
    no_habilitados: int = Field(ge=0)


class PedidosIndicadores(BaseModel):
    total: int = Field(ge=0)
    por_estado: dict[str, int]
    por_prioridad: dict[str, int]


class IndicadoresOperacionResponse(BaseModel):
    generado_en: datetime
    vigencia_segundos: int = Field(ge=0)
    vehiculos: VehiculosIndicadores
    conductores: ConductoresIndicadores
    pedidos: PedidosIndicadores
