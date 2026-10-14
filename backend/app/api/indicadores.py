"""Aggregated operational indicators for the home dashboard."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.dependencies import require_permission
from app.core.rbac import Identidad, Permiso
from app.schemas.indicadores import IndicadoresOperacionResponse
from app.services.indicadores import (
    VIGENCIA_SEGUNDOS,
    IndicadoresService,
    IndicatorsUnavailable,
)

router = APIRouter(prefix="/indicadores", tags=["indicadores"])


def get_indicator_service(request: Request) -> IndicadoresService:
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        )
    return IndicadoresService(factory)


@router.get(
    "/operacion",
    response_model=IndicadoresOperacionResponse,
    summary="Indicadores agregados de la operación",
    description=(
        "Conteos de vehículos, conductores y pedidos calculados en SQL, sin datos "
        "personales. Respuesta privada con vigencia de "
        f"{VIGENCIA_SEGUNDOS} s (Cache-Control). Requiere indicadores.consultar "
        "con alcance general."
    ),
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Permission denied"},
        503: {"description": "Service unavailable"},
    },
)
def operational_indicators(
    response: Response,
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.INDICADORES_CONSULTAR))
    ],
    service: Annotated[IndicadoresService, Depends(get_indicator_service)],
) -> IndicadoresOperacionResponse:
    try:
        result = service.operational()
    except IndicatorsUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        ) from None
    response.headers["Cache-Control"] = f"private, max-age={VIGENCIA_SEGUNDOS}"
    return result
