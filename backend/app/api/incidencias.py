"""ECL-73 incident endpoints: driver registration and pending list."""

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)

from app.api.dependencies import require_permission
from app.api.validation import SanitizedRoute
from app.core.incidencias import (
    ESTADO_LISTADO,
    PAGE_SIZE_DEFAULT,
    PAGE_SIZE_MAX,
    EstadoIncidencia,
)
from app.core.rbac import Contexto, Identidad, Permiso, Rol
from app.schemas.incidencia import (
    IncidenciaCreate,
    IncidenciaPage,
    IncidenciaRegistrada,
)
from app.services.incidencias import (
    IncidenciaConflicto,
    IncidenciaInvalida,
    IncidenciaParadaAjena,
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
        # I08: only the Conductor role, although the global matrix also grants
        # incidencias.crear to the Operador; denied before reaching the service.
        Depends(
            require_permission(
                Permiso.INCIDENCIAS_CREAR, _self_context, roles={Rol.CONDUCTOR}
            )
        ),
    ],
    service: Annotated[IncidenciaService, Depends(get_incident_service)],
    expected_owner_id: Annotated[
        UUID | None, Header(alias="X-Expected-Owner-ID")
    ] = None,
) -> IncidenciaRegistrada:
    # ECL-74: cookies are shared by tabs. Reject an outbox from account A if
    # account B logged in after the client's itinerary/owner verification.
    # This header is a consistency guard, never a source of authorization.
    if expected_owner_id is not None and expected_owner_id != identity.usuario_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "La sesión cambió")
    try:
        acknowledgement, created = service.registrar(identity.usuario_id, payload)
    except (IncidenciaSinConductor, IncidenciaParadaAjena):
        # Generic: no profile, or a stop of another driver (I08, I10).
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acceso denegado") from None
    except IncidenciaInvalida as error:
        # Same shape as SanitizedRoute 422s: field location and code, no input.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            [
                {
                    "loc": ["body", error.field],
                    "type": error.code,
                    "msg": "Entrada inválida",
                }
            ],
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
    estado: EstadoIncidencia = ESTADO_LISTADO,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=PAGE_SIZE_MAX)] = PAGE_SIZE_DEFAULT,
) -> IncidenciaPage:
    if estado is not ESTADO_LISTADO:
        # I15: this operational list only admits pending incidents.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Estado no admitido en este listado",
        )
    try:
        return service.listar(estado, page, page_size)
    except IncidenciaUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        ) from None
