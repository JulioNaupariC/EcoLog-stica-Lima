"""Strict contracts for driver itinerary summaries and delivery reports."""

from datetime import datetime
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


class DeliveryDetails(BaseModel):
    """Operational fields only; no customer names, contacts or credentials."""

    address: str = Field(min_length=1, max_length=255)
    reference: str | None = Field(default=None, max_length=255)
    window_start: datetime
    window_end: datetime


class AssignedStopResponse(BaseModel):
    stop_id: UUID
    position: int = Field(ge=1)
    status: AssignedStopStatus
    delivery: DeliveryDetails | None = None


class DriverItineraryResponse(BaseModel):
    owner_id: UUID | None = None
    stops: list[AssignedStopResponse]
