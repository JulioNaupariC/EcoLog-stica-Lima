"""Driver persistence; the service owns transactions and error translation."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.conductor import Conductor


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

    def list_page(self, page: int, page_size: int) -> tuple[list[Conductor], int]:
        total = self._session.scalar(select(func.count()).select_from(Conductor))
        query = (
            select(Conductor)
            .order_by(Conductor.conductor_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self._session.scalars(query)), total or 0
