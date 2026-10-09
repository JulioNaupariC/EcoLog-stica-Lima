"""Preferences for existing clients, protected by the established client RBAC."""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.api.dependencies import require_permission
from app.core.rbac import Identidad, Permiso
from app.schemas.preferencias import PreferenciasPatch, PreferenciasResponse
from app.services.preferencias import (
    PreferenciasNotFound,
    PreferenciasService,
    PreferenciasUnavailable,
)


class PreferenciasRoute(APIRoute):
    """Avoid reflecting personal values in validation error responses."""

    def get_route_handler(self) -> Callable:
        handler = super().get_route_handler()

        async def sanitized(request: Request) -> Response:
            try:
                return await handler(request)
            except RequestValidationError as error:
                details = [
                    {
                        "loc": item["loc"],
                        "type": item["type"],
                        "msg": "Entrada inválida",
                    }
                    for item in error.errors()
                ]
                return JSONResponse(status_code=422, content={"detail": details})

        return sanitized


router = APIRouter(
    prefix="/clientes", tags=["preferencias"], route_class=PreferenciasRoute
)
ERRORS = {
    401: {"description": "No autenticado"},
    403: {"description": "Acceso denegado"},
    404: {"description": "Cliente no encontrado"},
    503: {"description": "Servicio no disponible"},
}


def get_preferencias_service(request: Request) -> PreferenciasService:
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise HTTPException(503, "Servicio no disponible")
    return PreferenciasService(factory)


@router.get(
    "/{cliente_id}/preferencias", response_model=PreferenciasResponse, responses=ERRORS
)
def get_preferencias(
    cliente_id: UUID,
    response: Response,
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.CLIENTES_CONSULTAR))
    ],
    service: Annotated[PreferenciasService, Depends(get_preferencias_service)],
) -> PreferenciasResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        return service.get(cliente_id)
    except PreferenciasNotFound:
        raise HTTPException(404, "Cliente no encontrado") from None
    except PreferenciasUnavailable:
        raise HTTPException(503, "Servicio no disponible") from None


@router.patch(
    "/{cliente_id}/preferencias", response_model=PreferenciasResponse, responses=ERRORS
)
def update_preferencias(
    cliente_id: UUID,
    response: Response,
    payload: PreferenciasPatch,
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.CLIENTES_ACTUALIZAR))
    ],
    service: Annotated[PreferenciasService, Depends(get_preferencias_service)],
) -> PreferenciasResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        return service.update(cliente_id, payload)
    except PreferenciasNotFound:
        raise HTTPException(404, "Cliente no encontrado") from None
    except PreferenciasUnavailable:
        raise HTTPException(503, "Servicio no disponible") from None
