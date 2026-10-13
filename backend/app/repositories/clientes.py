"""Client existence lookup and minimal paginated search for selectors."""

from uuid import UUID

from sqlalchemy import func, or_, select
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

    def search(
        self, term: str | None, page: int, page_size: int
    ) -> tuple[list[tuple[UUID, str]], int]:
        """Return ``(cliente_id, nombre)`` matching ``term`` by name or exact id."""
        try:
            condition = None
            if term:
                pattern = "%" + _escape_like(term) + "%"
                condition = Cliente.nombre.ilike(pattern, escape="\\")
                exact_id = _as_uuid(term)
                if exact_id is not None:
                    condition = or_(condition, Cliente.cliente_id == exact_id)
            count = select(func.count()).select_from(Cliente)
            query = select(Cliente.cliente_id, Cliente.nombre)
            if condition is not None:
                count = count.where(condition)
                query = query.where(condition)
            total = self._session.scalar(count) or 0
            rows = self._session.execute(
                query.order_by(Cliente.nombre, Cliente.cliente_id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            return [(row.cliente_id, row.nombre) for row in rows], total
        except SQLAlchemyError:
            raise ClienteStorageError("Client storage unavailable") from None


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _as_uuid(term: str) -> UUID | None:
    try:
        return UUID(term)
    except ValueError:
        return None
