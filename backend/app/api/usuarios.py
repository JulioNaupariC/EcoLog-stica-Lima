"""ECL-77 user list and administrator password reset endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.api.dependencies import get_authenticated_session, require_permission
from app.api.validation import SanitizedRoute
from app.core.rbac import Identidad, Permiso
from app.repositories.auditoria import AuditStorageError
from app.schemas.usuario import (
    ContrasenaTemporalResponse,
    UsuarioListItem,
    UsuarioPage,
)
from app.services.autenticacion import AuthenticatedSession
from app.services.autorizacion import AuthorizationDenied
from app.services.restablecimiento import (
    AutoRestablecimiento,
    RestablecimientoService,
    RestablecimientoUnavailable,
    UsuarioInactivo,
    UsuarioNoEncontrado,
)

router = APIRouter(prefix="/usuarios", tags=["usuarios"], route_class=SanitizedRoute)


def get_password_reset_service(request: Request) -> RestablecimientoService:
    service = getattr(request.app.state, "password_reset_service", None)
    if service is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        )
    return service


# Least privilege (OWASP A01): the list exposes every account e-mail and only
# the Administrator can act on it, so it requires USUARIOS_ACTUALIZAR. The
# matrix still grants USUARIOS_CONSULTAR to the Operator, pending team review.
@router.get("", response_model=UsuarioPage)
def list_usuarios(
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.USUARIOS_ACTUALIZAR))
    ],
    service: Annotated[RestablecimientoService, Depends(get_password_reset_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> UsuarioPage:
    try:
        result = service.listar(page, page_size)
    except RestablecimientoUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        ) from None
    return UsuarioPage(
        items=[UsuarioListItem.model_validate(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
    )


@router.post(
    "/{usuario_id}/restablecer-contrasena",
    response_model=ContrasenaTemporalResponse,
)
def reset_password(
    usuario_id: UUID,
    response: Response,
    authenticated: Annotated[AuthenticatedSession, Depends(get_authenticated_session)],
    service: Annotated[RestablecimientoService, Depends(get_password_reset_service)],
) -> ContrasenaTemporalResponse:
    try:
        result = service.restablecer(authenticated.identidad, usuario_id)
    except AuthorizationDenied:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acceso denegado") from None
    except UsuarioNoEncontrado:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Usuario no encontrado"
        ) from None
    except UsuarioInactivo:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "El usuario está inactivo"
        ) from None
    except AutoRestablecimiento:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Usa el cambio de contraseña para tu propia cuenta",
        ) from None
    except (RestablecimientoUnavailable, AuditStorageError):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        ) from None
    # The temporary password is shown once: no browser or proxy may keep it.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return ContrasenaTemporalResponse(
        contrasena_temporal=result.contrasena_temporal, expira_en=result.expira_en
    )
