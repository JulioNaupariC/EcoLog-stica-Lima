"""Atomic, partial preference updates confined to one existing client."""

from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.repositories.preferencias import PreferenciasRepository
from app.schemas.preferencias import PreferenciasPatch, PreferenciasResponse


class PreferenciasNotFound(LookupError):
    """The existing client resource was not found."""


class PreferenciasUnavailable(RuntimeError):
    """Sanitized storage failure."""


class PreferenciasService:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def get(self, cliente_id: UUID) -> PreferenciasResponse:
        try:
            with self._factory.begin() as session:
                row = PreferenciasRepository(session).get(cliente_id)
                if row is None:
                    raise PreferenciasNotFound("Client not found")
                return PreferenciasResponse.model_validate(row)
        except SQLAlchemyError:
            raise PreferenciasUnavailable("Preferences unavailable") from None

    def update(
        self, cliente_id: UUID, payload: PreferenciasPatch
    ) -> PreferenciasResponse:
        try:
            with self._factory.begin() as session:
                repository = PreferenciasRepository(session)
                row = repository.get(cliente_id, lock=True)
                if row is None:
                    raise PreferenciasNotFound("Client not found")
                for field, value in payload.model_dump(exclude_unset=True).items():
                    setattr(row, field, value)
                repository.flush()
                return PreferenciasResponse.model_validate(row)
        except SQLAlchemyError:
            raise PreferenciasUnavailable("Preferences unavailable") from None
