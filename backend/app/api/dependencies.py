"""Trusted HTTP identity resolution and reusable RBAC integration."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.core.rbac import Identidad, Permiso
from app.repositories.auditoria import AuditStorageError
from app.services.autenticacion import (
    AutenticacionService,
    AuthenticatedSession,
    AuthenticationUnavailable,
    InvalidSession,
)
from app.services.autorizacion import AuthorizationDenied, AutorizacionService

COOKIE_NAME = "ecologistica_session"


def get_authentication_service(request: Request) -> AutenticacionService:
    service = getattr(request.app.state, "authentication_service", None)
    if service is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        )
    return service


def get_authenticated_session(
    request: Request,
    service: Annotated[AutenticacionService, Depends(get_authentication_service)],
) -> AuthenticatedSession:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado")
    try:
        return service.resolve(token)
    except InvalidSession:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado") from None
    except AuthenticationUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        ) from None


def require_permission(permiso: Permiso) -> Callable[..., Identidad]:
    def dependency(
        request: Request,
        authenticated: Annotated[
            AuthenticatedSession, Depends(get_authenticated_session)
        ],
    ) -> Identidad:
        service: AutorizacionService | None = getattr(
            request.app.state, "authorization_service", None
        )
        if service is None:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
            )
        try:
            service.autorizar(authenticated.identidad, permiso)
        except AuthorizationDenied:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Acceso denegado") from None
        except AuditStorageError:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
            ) from None
        return authenticated.identidad

    return dependency
