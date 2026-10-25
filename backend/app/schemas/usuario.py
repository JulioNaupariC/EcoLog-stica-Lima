"""ECL-77 user administration and password change contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.core.passwords import MIN_PASSWORD_LENGTH
from app.core.rbac import Rol

MAX_PASSWORD_LENGTH = 128


class UsuarioListItem(BaseModel):
    """Never carries password_hash, attempts or lockout state."""

    model_config = ConfigDict(from_attributes=True)
    usuario_id: UUID
    email: str
    rol: Rol
    estado: str
    debe_cambiar_contrasena: bool


class UsuarioPage(BaseModel):
    items: list[UsuarioListItem]
    page: int
    page_size: int
    total: int


class ContrasenaTemporalResponse(BaseModel):
    contrasena_temporal: str
    expira_en: datetime


class CambioContrasenaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    contrasena_actual: SecretStr = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)
    contrasena_nueva: SecretStr = Field(
        min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH
    )
