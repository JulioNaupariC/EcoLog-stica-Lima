"""Persist each authorization decision in an independent short transaction."""

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.repositories.auditoria import (
    AuditoriaRepository,
    AuditStorageError,
    Registro,
)


class AuditoriaService:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def registrar(self, registro: Registro) -> None:
        # Validate before opening a connection; never accept an arbitrary payload.
        registro = Registro.model_validate(registro)
        try:
            with self._factory.begin() as session:
                AuditoriaRepository(session).insert(registro)
        except (SQLAlchemyError, AuditStorageError):
            raise AuditStorageError("Audit storage unavailable") from None
