"""Strict contracts for driver itinerary summaries and delivery reports."""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssignedStopStatus(str, Enum):
    PENDIENTE = "PENDIENTE"
    EN_RUTA = "EN_RUTA"
    ENTREGADO = "ENTREGADO"
    NO_ENTREGADO = "NO_ENTREGADO"


class DriverReportStatus(str, Enum):
    ENTREGADO = "ENTREGADO"
    NO_ENTREGADO = "NO_ENTREGADO"


class DriverReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    operation_id: UUID
    stop_id: UUID
    status: DriverReportStatus


class DriverReportAcknowledgement(BaseModel):
    operation_id: UUID
    acknowledged: bool = True


class AssignedStopResponse(BaseModel):
    stop_id: UUID
    position: int = Field(ge=1)
    status: AssignedStopStatus


class DriverItineraryResponse(BaseModel):
    stops: list[AssignedStopResponse]
