"""ECL-95 (ST-046): read access to the persisted route model.

For now only what ECL-82 needs: the jornada (operating date) and driver of the
planned stop behind a driver's stop assignment. ST-047 adds the writes.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.driver_stop_assignment import DriverStopAssignment
from app.models.ruta import ParadaRuta, Ruta


class RutaStorageError(RuntimeError):
    """Sanitized route storage failure."""


@dataclass(frozen=True)
class JornadaParada:
    ruta_id: UUID
    conductor_id: UUID | None
    fecha_operacion: date


class RutaRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def jornada_de_asignacion(self, stop_id: UUID) -> JornadaParada | None:
        """Route, driver and jornada of an assignment; None if it has no route.

        Sprint 3 assignments have no planned stop, so they return None: the
        caller (ECL-82) decides how to treat them, never this repository.
        """
        try:
            row = self._session.execute(
                select(Ruta.ruta_id, Ruta.conductor_id, Ruta.fecha_operacion)
                .join(ParadaRuta, ParadaRuta.ruta_id == Ruta.ruta_id)
                .join(
                    DriverStopAssignment,
                    DriverStopAssignment.parada_ruta_id == ParadaRuta.parada_id,
                )
                .where(DriverStopAssignment.stop_id == stop_id)
            ).one_or_none()
        except SQLAlchemyError:
            raise RutaStorageError("Route storage unavailable") from None
        return None if row is None else JornadaParada(*row)
