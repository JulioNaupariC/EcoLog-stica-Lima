"""Targeted existing-client preference lookup; no client creation or deletion."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente


class PreferenciasRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, cliente_id: UUID, *, lock: bool = False) -> Cliente | None:
        query = select(Cliente).where(Cliente.cliente_id == cliente_id)
        if lock:
            query = query.with_for_update()
        return self._session.scalar(query)

    def flush(self) -> None:
        self._session.flush()
