"""Protected ECL-48 driver registration, consultation and update endpoints."""

from collections.abc import Callable
from typing import Annotated, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.dependencies import require_permission
from app.api.validation import SanitizedRoute
from app.core.rbac import Contexto, Identidad, Permiso, Rol
from app.repositories.auditoria import AuditStorageError
from app.schemas.conductor import (
    ConductorCreate,
    ConductorPage,
    ConductorResponse,
    ConductorSummary,
    ConductorUpdate,
)
from app.services.autorizacion import AuthorizationDenied
from app.services.conductores import (
    ConductorConflict,
    ConductorInvalid,
    ConductorNotFound,
    ConductorService,
    ConductorUnavailable,
)

router = APIRouter(
    prefix="/conductores", tags=["conductores"], route_class=SanitizedRoute
)
T = TypeVar("T")


def get_conductor_service(request: Request) -> ConductorService:
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise HTTPException(503, "Servicio no disponible")
    return ConductorService(factory)


def _translate(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except ConductorNotFound:
        raise HTTPException(404, "Conductor no encontrado") from None
    except ConductorConflict:
        raise HTTPException(409, "DNI o cuenta ya registrados") from None
    except ConductorInvalid:
        raise HTTPException(422, "Disponibilidad o perfil inválidos") from None
    except ConductorUnavailable:
        raise HTTPException(503, "Servicio no disponible") from None


def _candidate_self(identity: Identidad) -> Contexto:
    # Preliminary gate; object ownership is checked separately before returning data.
    return Contexto(propietario_id=identity.usuario_id)


@router.post("", response_model=ConductorSummary, status_code=status.HTTP_201_CREATED)
def create_conductor(
    identity: Annotated[
        Identidad, Depends(require_permission(Permiso.CONDUCTORES_CREAR))
    ],
    payload: ConductorCreate,
    service: Annotated[ConductorService, Depends(get_conductor_service)],
) -> ConductorSummary:
    return _translate(lambda: service.create(payload, identity.usuario_id))


@router.get("", response_model=ConductorPage)
def list_conductores(
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.CONDUCTORES_CONSULTAR))
    ],
    service: Annotated[ConductorService, Depends(get_conductor_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ConductorPage:
    return _translate(lambda: service.list_page(page, page_size))


@router.get("/{conductor_id}", response_model=ConductorResponse | ConductorSummary)
def get_conductor(
    conductor_id: UUID,
    request: Request,
    identity: Annotated[
        Identidad,
        Depends(require_permission(Permiso.CONDUCTORES_CONSULTAR, _candidate_self)),
    ],
    service: Annotated[ConductorService, Depends(get_conductor_service)],
) -> ConductorResponse | ConductorSummary:
    row = _translate(lambda: service.get(conductor_id))
    try:
        request.app.state.authorization_service.autorizar(
            identity,
            Permiso.CONDUCTORES_CONSULTAR,
            Contexto(propietario_id=row.usuario_id),
            entidad_id=conductor_id,
        )
    except AuthorizationDenied:
        raise HTTPException(403, "Acceso denegado") from None
    except AuditStorageError:
        raise HTTPException(503, "Servicio no disponible") from None
    if identity.rol == Rol.CONDUCTOR:
        return ConductorSummary.model_validate(row.model_dump())
    return row


@router.patch("/{conductor_id}", response_model=ConductorResponse)
def update_conductor(
    conductor_id: UUID,
    identity: Annotated[
        Identidad, Depends(require_permission(Permiso.CONDUCTORES_ACTUALIZAR))
    ],
    payload: ConductorUpdate,
    service: Annotated[ConductorService, Depends(get_conductor_service)],
) -> ConductorResponse:
    return _translate(
        lambda: service.update(conductor_id, payload, identity.usuario_id)
    )
