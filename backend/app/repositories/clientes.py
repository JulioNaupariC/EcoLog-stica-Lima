"""Client existence lookup for order registration only."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.cliente import Cliente


class ClienteStorageError(RuntimeError):
    """Sanitized client lookup failure."""


class ClienteRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def exists(self, cliente_id: UUID) -> bool:
        try:
            lookup = select(Cliente.cliente_id).where(Cliente.cliente_id == cliente_id)
            return bool(self._session.scalar(select(lookup.exists())))
        except SQLAlchemyError:
            raise ClienteStorageError("Client storage unavailable") from None
