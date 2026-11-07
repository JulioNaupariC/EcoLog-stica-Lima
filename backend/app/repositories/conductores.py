"""Driver persistence; the service owns transactions and error translation."""

from uuid import UUID

from sqlalchemy import RowMapping, func, select
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

    def list_page(self, page: int, page_size: int) -> tuple[list[RowMapping], int]:
        """Return a page of drivers with only the columns the list shows.

        Green IT (ECL-109): selects the eight columns needed by the list and
        its eligibility rule as plain rows, instead of hydrating full
        ``Conductor`` and ``Usuario`` entities (DNI, licence, phone, e-mail
        and password hash are never read). The outer join keeps a single
        query per page, without N+1 (ST-038).
        """
        total = self._session.scalar(select(func.count()).select_from(Conductor))
        query = (
            select(
                Conductor.conductor_id,
                Conductor.nombre,
                Conductor.disponible_desde,
                Conductor.disponible_hasta,
                Conductor.estado,
                Conductor.licencia_vigente_hasta,
                Usuario.rol.label("cuenta_rol"),
                Usuario.estado.label("cuenta_estado"),
            )
            .outerjoin(Usuario, Usuario.usuario_id == Conductor.usuario_id)
            .order_by(Conductor.conductor_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self._session.execute(query).mappings()), total or 0
