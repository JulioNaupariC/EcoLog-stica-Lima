"""Login and current-session logout endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.api.dependencies import (
    COOKIE_NAME,
    get_authenticated_session,
    get_authentication_service,
)
from app.core.config import Settings
from app.core.rbac import Rol
from app.services.autenticacion import (
    AutenticacionService,
    AuthenticatedSession,
    AuthenticationUnavailable,
    InvalidCredentials,
)

router = APIRouter(tags=["access"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    email: str = Field(min_length=1, max_length=255)
    password: SecretStr = Field(min_length=1)


class LoginResponse(BaseModel):
    usuario_id: UUID
    rol: Rol


@router.post("/login", response_model=LoginResponse)
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
        max_age=settings.session_ttl_minutes * 60,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
        path="/",
    )
    return LoginResponse(
        usuario_id=result.identidad.usuario_id,
        rol=Rol(result.identidad.rol),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    authenticated: Annotated[AuthenticatedSession, Depends(get_authenticated_session)],
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
