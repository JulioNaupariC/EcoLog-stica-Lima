"""Read-only client search used by order and preference selectors."""

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.repositories.clientes import ClienteRepository, ClienteStorageError
from app.schemas.cliente import ClienteListItem, ClientePage

MAX_TERM_LENGTH = 160


class ClienteSearchInvalid(ValueError):
    """The search term cannot be used safely."""


class ClientesUnavailable(RuntimeError):
    """Sanitized storage failure."""


def normalize_term(term: str | None) -> str | None:
    """Trim the term; reject control characters and oversized input."""
    if term is None:
        return None
    cleaned = term.strip()
    if len(cleaned) > MAX_TERM_LENGTH or any(ord(char) < 32 for char in cleaned):
        raise ClienteSearchInvalid("Término de búsqueda inválido")
    return cleaned or None


class ClienteService:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def search(self, term: str | None, page: int, page_size: int) -> ClientePage:
        cleaned = normalize_term(term)
        try:
            with self._factory() as session:
                rows, total = ClienteRepository(session).search(
                    cleaned, page, page_size
                )
        except (ClienteStorageError, SQLAlchemyError):
            raise ClientesUnavailable("Clients unavailable") from None
        return ClientePage(
            items=[
                ClienteListItem(cliente_id=cliente_id, nombre=nombre)
                for cliente_id, nombre in rows
            ],
            page=page,
            page_size=page_size,
            total=total,
        )
