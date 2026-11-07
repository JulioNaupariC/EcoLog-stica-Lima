"""Login and current-session logout endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.api.dependencies import (
    COOKIE_NAME,
    get_authentication_service,
    get_current_session,
)
from app.core.config import Settings
from app.core.rbac import Rol
from app.services.autenticacion import (
    ABSOLUTE_SESSION_LIFETIME,
    AutenticacionService,
    AuthenticatedSession,
    AuthenticationUnavailable,
    InvalidCredentials,
    InvalidSession,
    SessionLimitReached,
)

router = APIRouter(tags=["access"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    email: str = Field(min_length=1, max_length=255)
    password: SecretStr = Field(min_length=1)


class LoginResponse(BaseModel):
    usuario_id: UUID
    rol: Rol
    expires_at: datetime
    max_expires_at: datetime
    debe_cambiar_contrasena: bool = False


@router.post("/login", response_model=LoginResponse, response_model_exclude_none=True)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: Annotated[AutenticacionService, Depends(get_authentication_service)],
) -> LoginResponse:
    try:
        result = service.login(payload.email, payload.password.get_secret_value())
    except InvalidCredentials:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas"
        ) from None
    except AuthenticationUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        ) from None
    settings: Settings = request.app.state.settings
    response.set_cookie(
        COOKIE_NAME,
        result.token,
        # ECL-83: the browser keeps the cookie up to the absolute limit; the
        # server-side `sesion.expira_en` decides when it stops being valid, so an
        # extension never has to reissue the token.
        max_age=int(ABSOLUTE_SESSION_LIFETIME.total_seconds()),
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return LoginResponse(
        usuario_id=result.identidad.usuario_id,
        rol=Rol(result.identidad.rol),
        expires_at=result.expira_en,
        max_expires_at=result.max_expira_en or result.expira_en,
        debe_cambiar_contrasena=result.debe_cambiar_contrasena,
    )


class SessionExtensionResponse(BaseModel):
    expires_at: datetime
    max_expires_at: datetime


@router.post("/sesion/extender", response_model=SessionExtensionResponse)
def extend_session(
    request: Request,
    response: Response,
    authenticated: Annotated[AuthenticatedSession, Depends(get_current_session)],
    service: Annotated[AutenticacionService, Depends(get_authentication_service)],
) -> SessionExtensionResponse:
    settings: Settings = request.app.state.settings
    origin = request.headers.get("origin")
    if origin is not None and origin not in settings.cors_allowed_origins:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Origen no permitido")
    # This keeps the ECL-77 restriction: extending time grants no operational access.
    try:
        result = service.extend(authenticated)
    except InvalidSession:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado") from None
    except SessionLimitReached:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La sesión alcanzó su duración máxima; vuelve a iniciar sesión",
        ) from None
    except AuthenticationUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        ) from None
    # Only the server-side expiration moves: the cookie is not reissued.
    response.headers["Cache-Control"] = "no-store"
    return SessionExtensionResponse(
        expires_at=result.expira_en, max_expires_at=result.max_expira_en
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    # A pending password change must not prevent leaving the session.
    authenticated: Annotated[AuthenticatedSession, Depends(get_current_session)],
    service: Annotated[AutenticacionService, Depends(get_authentication_service)],
) -> None:
    settings: Settings = request.app.state.settings
    try:
        service.logout(authenticated)
    except AuthenticationUnavailable:
        cookie_deletion = Response()
        cookie_deletion.delete_cookie(
            COOKIE_NAME,
            path="/",
            httponly=True,
            secure=settings.app_env == "production",
            samesite="strict",
        )
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Servicio no disponible",
            headers={"Set-Cookie": cookie_deletion.headers["set-cookie"]},
        ) from None
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
    )
