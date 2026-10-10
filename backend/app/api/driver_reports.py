"""Authenticated conductor itinerary and idempotent delivery-report endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.dependencies import require_permission
from app.core.rbac import Contexto, Identidad, Permiso
from app.schemas.driver_report import (
    DriverItineraryResponse,
    DriverReportAcknowledgement,
    DriverReportCreate,
)
from app.services.driver_reports import (
    DriverReportAlreadyFinal,
    DriverReportIdentityConflict,
    DriverReportService,
    DriverReportStopNotAssigned,
    DriverReportUnavailable,
)

router = APIRouter(prefix="/conductor", tags=["conductor"])


def get_driver_report_service(request: Request) -> DriverReportService:
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        )
    return DriverReportService(factory)


def _self_context(identity: Identidad) -> Contexto:
    return Contexto(propietario_id=identity.usuario_id)


@router.get(
    "/itinerario",
    response_model=DriverItineraryResponse,
    response_model_exclude_none=True,
)
def get_itinerary(
    response: Response,
    service: Annotated[DriverReportService, Depends(get_driver_report_service)],
    identity: Annotated[
        Identidad,
        Depends(require_permission(Permiso.ITINERARIOS_CONSULTAR, _self_context)),
    ],
) -> DriverItineraryResponse:
    try:
        response.headers["Cache-Control"] = "no-store"
        return DriverItineraryResponse(
            owner_id=identity.usuario_id,
            stops=service.list_assignments(identity.usuario_id),
        )
    except DriverReportUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        ) from None


@router.post(
    "/reportes",
    response_model=DriverReportAcknowledgement,
    status_code=status.HTTP_200_OK,
)
def create_report(
    payload: DriverReportCreate,
    service: Annotated[DriverReportService, Depends(get_driver_report_service)],
    identity: Annotated[
        Identidad,
        Depends(require_permission(Permiso.PARADAS_REPORTAR, _self_context)),
    ],
) -> DriverReportAcknowledgement:
    try:
        return service.save_report(identity.usuario_id, payload)
    except DriverReportStopNotAssigned:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Parada no asignada") from None
    except DriverReportIdentityConflict:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Identificador de operación en conflicto"
        ) from None
    except DriverReportAlreadyFinal:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "La parada ya tiene un resultado final"
        ) from None
    except DriverReportUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        ) from None
