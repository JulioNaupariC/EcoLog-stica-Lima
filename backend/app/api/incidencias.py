"""ECL-73 incident endpoints: driver registration and pending list."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.api.dependencies import require_permission
from app.api.validation import SanitizedRoute
from app.core.incidencias import PAGE_SIZE_MAX, EstadoIncidencia
from app.core.rbac import Contexto, Identidad, Permiso
from app.schemas.incidencia import (
    IncidenciaCreate,
    IncidenciaPage,
    IncidenciaRegistrada,
)
from app.services.incidencias import (
    IncidenciaConflicto,
    IncidenciaInvalida,
    IncidenciaService,
    IncidenciaSinConductor,
    IncidenciaUnavailable,
)

conductor_router = APIRouter(
    prefix="/conductor", tags=["incidencias"], route_class=SanitizedRoute
)
router = APIRouter(
    prefix="/incidencias", tags=["incidencias"], route_class=SanitizedRoute
)


_ERRORS = {
    401: {"description": "Sin sesión"},
    403: {"description": "Rol sin permiso o cambio de contraseña requerido"},
    503: {"description": "Servicio no disponible"},
}


def get_incident_service(request: Request) -> IncidenciaService:
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        )
    return IncidenciaService(factory)


def _self_context(identity: Identidad) -> Contexto:
    return Contexto(propietario_id=identity.usuario_id)


@conductor_router.post(
    "/incidencias",
    response_model=IncidenciaRegistrada,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"description": "Reenvío idempotente: misma respuesta"},
        409: {"description": "Mismo operation_id con contenido distinto"},
        **_ERRORS,
    },
)
def register_incident(
    payload: IncidenciaCreate,
    response: Response,
    identity: Annotated[
        Identidad,
        Depends(require_permission(Permiso.INCIDENCIAS_CREAR, _self_context)),
    ],
    service: Annotated[IncidenciaService, Depends(get_incident_service)],
) -> IncidenciaRegistrada:
    try:
        acknowledgement, created = service.registrar(identity.usuario_id, payload)
    except IncidenciaSinConductor:
        # Only an authenticated driver can report from its own itinerary.
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acceso denegado") from None
    except IncidenciaInvalida:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Datos de la incidencia inválidos",
        ) from None
    except IncidenciaConflicto:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El identificador de operación ya se usó con otros datos",
        ) from None
    except IncidenciaUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        ) from None
    if not created:
        response.status_code = status.HTTP_200_OK
    return acknowledgement


@router.get("", response_model=IncidenciaPage, responses=_ERRORS)
def list_incidents(
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.INCIDENCIAS_CONSULTAR))
    ],
    service: Annotated[IncidenciaService, Depends(get_incident_service)],
    estado: EstadoIncidencia = EstadoIncidencia.PENDIENTE_VALIDACION,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=PAGE_SIZE_MAX)] = 20,
) -> IncidenciaPage:
    try:
        return service.listar(estado, page, page_size)
    except IncidenciaUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        ) from None
