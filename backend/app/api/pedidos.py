"""Authenticated order registration API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import require_permission
from app.api.validation import SanitizedRoute
from app.core.rbac import Identidad, Permiso
from app.schemas.pedido import PedidoCreate, PedidoResponse
from app.services.pedidos import (
    PedidoClienteNoEncontrado,
    PedidoService,
    PedidoUnavailable,
)

router = APIRouter(prefix="/pedidos", tags=["pedidos"], route_class=SanitizedRoute)


def get_pedido_service(request: Request) -> PedidoService:
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        )
    return PedidoService(factory)


@router.post("", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED)
def create_pedido(
    payload: PedidoCreate,
    service: Annotated[PedidoService, Depends(get_pedido_service)],
    _identity: Annotated[Identidad, Depends(require_permission(Permiso.PEDIDOS_CREAR))],
) -> PedidoResponse:
    try:
        return service.create(payload)
    except PedidoClienteNoEncontrado:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Cliente no encontrado"
        ) from None
    except PedidoUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        ) from None
