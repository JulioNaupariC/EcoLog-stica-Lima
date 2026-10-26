"""ECL-77 password change for the authenticated user (mandatory or voluntary)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_session
from app.api.usuarios import get_password_reset_service
from app.api.validation import SanitizedRoute
from app.schemas.usuario import CambioContrasenaRequest
from app.services.autenticacion import AuthenticatedSession
from app.services.restablecimiento import (
    ContrasenaActualInvalida,
    ContrasenaNuevaInvalida,
    RestablecimientoService,
    RestablecimientoUnavailable,
)

router = APIRouter(tags=["access"], route_class=SanitizedRoute)


@router.post("/cambiar-contrasena", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: CambioContrasenaRequest,
    # Allowed while a change is pending: this is the way out of that state.
    authenticated: Annotated[AuthenticatedSession, Depends(get_current_session)],
    service: Annotated[RestablecimientoService, Depends(get_password_reset_service)],
) -> None:
    try:
        service.cambiar(
            authenticated,
            payload.contrasena_actual.get_secret_value(),
            payload.contrasena_nueva.get_secret_value(),
        )
    except ContrasenaNuevaInvalida:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "La nueva contraseña debe tener al menos 12 caracteres "
            "y ser distinta de la actual",
        ) from None
    except ContrasenaActualInvalida:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "La contraseña actual no es válida"
        ) from None
    except RestablecimientoUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        ) from None
