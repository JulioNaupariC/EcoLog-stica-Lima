"""EN-008 (ECL-26): versioned parameters. RBAC per the current matrix:
parametros.consultar (Administrador, Operador, Analista, Auditor) reads;
parametros.crear (only Administrador) registers a version."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from pydantic import AwareDatetime

from app.api.dependencies import require_permission
from app.api.validation import SanitizedRoute
from app.core.parametros import VERSION_MAX
from app.core.rbac import Identidad, Permiso
from app.schemas.parametro import VersionCreate, VersionResponse
from app.services.parametros import (
    ParametrosConflicto,
    ParametroService,
    ParametrosNoEncontrados,
    ParametrosUnavailable,
)

router = APIRouter(
    prefix="/parametros", tags=["parametros"], route_class=SanitizedRoute
)


def get_parameter_service(request: Request) -> ParametroService:
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        )
    return ParametroService(factory)


def _translate(operation):
    try:
        return operation()
    except ParametrosNoEncontrados:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Versión de parámetros no encontrada"
        ) from None
    except ParametrosConflicto:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La versión ya existe o su inicio no es posterior a la vigente",
        ) from None
    except ParametrosUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        ) from None


@router.get("", response_model=VersionResponse)
def parametros_vigentes(
    service: Annotated[ParametroService, Depends(get_parameter_service)],
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.PARAMETROS_CONSULTAR))
    ],
    fecha: Annotated[AwareDatetime | None, Query()] = None,
) -> VersionResponse:
    """Version in force now, or at ``fecha`` (ISO-8601 with offset)."""
    return _translate(lambda: service.vigente(fecha))


@router.get("/{version}", response_model=VersionResponse)
def parametros_de_version(
    version: Annotated[str, Path(max_length=VERSION_MAX)],
    service: Annotated[ParametroService, Depends(get_parameter_service)],
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.PARAMETROS_CONSULTAR))
    ],
) -> VersionResponse:
    return _translate(lambda: service.por_version(version))


@router.post("", response_model=VersionResponse, status_code=status.HTTP_201_CREATED)
def registrar_version(
    payload: VersionCreate,
    service: Annotated[ParametroService, Depends(get_parameter_service)],
    identity: Annotated[
        Identidad, Depends(require_permission(Permiso.PARAMETROS_CREAR))
    ],
) -> VersionResponse:
    return _translate(lambda: service.registrar(payload, identity.usuario_id))
