"""Driver persistence; the service owns transactions and error translation."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.conductor import Conductor
from app.models.usuario import Usuario


class ConductorRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, driver: Conductor) -> None:
        self._session.add(driver)
        self._session.flush()

    def get(self, driver_id: UUID, *, lock: bool = False) -> Conductor | None:
        query = select(Conductor).where(Conductor.conductor_id == driver_id)
        if lock:
            query = query.with_for_update()
        return self._session.scalar(query)

    def list_page(
        self, page: int, page_size: int
    ) -> tuple[list[tuple[Conductor, Usuario | None]], int]:
        """Return a page of drivers with their accounts in a single query.

        The outer join avoids one extra ``SELECT usuario`` per row (N+1).
        """
        total = self._session.scalar(select(func.count()).select_from(Conductor))
        query = (
            select(Conductor, Usuario)
            .outerjoin(Usuario, Usuario.usuario_id == Conductor.usuario_id)
            .order_by(Conductor.conductor_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = [(driver, account) for driver, account in self._session.execute(query)]
        return rows, total or 0
