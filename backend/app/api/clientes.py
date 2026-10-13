"""Paginated client search for selectors, protected by CLIENTES_CONSULTAR."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.api.dependencies import require_permission
from app.core.rbac import Identidad, Permiso
from app.schemas.cliente import ClientePage
from app.services.clientes import (
    MAX_TERM_LENGTH,
    ClienteSearchInvalid,
    ClienteService,
    ClientesUnavailable,
)


class ClientesRoute(APIRoute):
    """Avoid reflecting search terms in validation error responses."""

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


router = APIRouter(prefix="/clientes", tags=["clientes"], route_class=ClientesRoute)
ERRORS = {
    401: {"description": "No autenticado"},
    403: {"description": "Acceso denegado"},
    422: {"description": "Parámetros inválidos"},
    503: {"description": "Servicio no disponible"},
}


def get_cliente_service(request: Request) -> ClienteService:
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise HTTPException(503, "Servicio no disponible")
    return ClienteService(factory)


@router.get("", response_model=ClientePage, responses=ERRORS)
def list_clientes(
    response: Response,
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.CLIENTES_CONSULTAR))
    ],
    service: Annotated[ClienteService, Depends(get_cliente_service)],
    buscar: Annotated[
        str | None,
        Query(
            max_length=MAX_TERM_LENGTH,
            description="Fragmento del nombre o identificador exacto del cliente",
        ),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ClientePage:
    response.headers["Cache-Control"] = "no-store"
    try:
        return service.search(buscar, page, page_size)
    except ClienteSearchInvalid:
        raise HTTPException(422, "Entrada inválida") from None
    except ClientesUnavailable:
        raise HTTPException(503, "Servicio no disponible") from None
