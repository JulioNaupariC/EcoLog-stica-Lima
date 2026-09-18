"""Typed audit insertion; callers own transactions. No update/delete API."""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.rbac import Motivo, Permiso
from app.models.auditoria import Auditoria


class Evento(str, Enum):
    PERMITIDA = "AUTORIZACION_PERMITIDA"
    DENEGADA = "AUTORIZACION_DENEGADA"


class Detalle(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
        revalidate_instances="always",
    )
    permiso: Permiso | None
    motivo: Motivo


class Registro(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
        revalidate_instances="always",
    )
    usuario_id: UUID | None
    entidad_id: UUID | None = None
    evento: Evento
    detalle: Detalle

    @model_validator(mode="after")
    def coherente(self) -> "Registro":
        permitido = self.evento is Evento.PERMITIDA
        if permitido != (self.detalle.motivo is Motivo.PERMITIDO):
            raise ValueError("Invalid audit decision")
        if permitido and (self.usuario_id is None or self.detalle.permiso is None):
            raise ValueError("Invalid audit decision")
        return self


class AuditStorageError(RuntimeError):
    """Storage failed without exposing the driver error or parameters."""


class AuditoriaRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert(self, registro: Registro) -> None:
        registro = Registro.model_validate(registro)
        permiso = registro.detalle.permiso
        row = Auditoria(
            usuario_id=registro.usuario_id,
            entidad=permiso.value.split(".")[0] if permiso else "autorizacion",
            entidad_id=registro.entidad_id,
            accion=registro.evento.value,
            detalle=registro.detalle.model_dump(mode="json"),
        )
        try:
            self._session.add(row)
            self._session.flush()
        except SQLAlchemyError:
            raise AuditStorageError("Audit storage unavailable") from None
