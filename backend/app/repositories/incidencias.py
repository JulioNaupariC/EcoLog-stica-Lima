"""ECL-73 incident persistence; callers own the transaction."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from geoalchemy2 import Geography, Geometry
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.conductor import Conductor
from app.models.driver_stop_assignment import DriverStopAssignment
from app.models.incidencia import Incidencia


class IncidenciaStorageError(RuntimeError):
    """Sanitized storage failure."""


class IncidenciaDuplicateOperation(RuntimeError):
    """Another transaction stored the same operation_id first."""


@dataclass(frozen=True)
class StoredIncidencia:
    """Fields compared for idempotency plus the registration acknowledgement."""

    incidencia_id: UUID
    operation_id: UUID
    conductor_id: UUID
    parada_id: UUID | None
    tipo: str
    severidad: str
    ocurrida_en: datetime
    latitud: float
    longitud: float
    observacion: str | None
    estado: str
    registrada_en: datetime


@dataclass(frozen=True)
class IncidenciaRow:
    incidencia_id: UUID
    tipo: str
    severidad: str
    ocurrida_en: datetime
    registrada_en: datetime
    conductor_id: UUID
    nombre: str
    latitud: float
    longitud: float
    observacion: str | None
    estado: str


_POINT = Incidencia.ubicacion.cast(Geometry(geometry_type="POINT", srid=4326))


class IncidenciaRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def conductor_id_for(self, usuario_id: UUID) -> UUID | None:
        try:
            return self._session.scalar(
                select(Conductor.conductor_id).where(Conductor.usuario_id == usuario_id)
            )
        except SQLAlchemyError:
            raise IncidenciaStorageError("Incident storage unavailable") from None

    def stop_belongs_to(self, stop_id: UUID, owner_id: UUID) -> bool:
        try:
            return (
                self._session.scalar(
                    select(DriverStopAssignment.stop_id).where(
                        DriverStopAssignment.stop_id == stop_id,
                        DriverStopAssignment.owner_id == owner_id,
                    )
                )
                is not None
            )
        except SQLAlchemyError:
            raise IncidenciaStorageError("Incident storage unavailable") from None

    def find_by_operation(self, operation_id: UUID) -> StoredIncidencia | None:
        try:
            row = self._session.execute(
                select(
                    Incidencia.incidencia_id,
                    Incidencia.operation_id,
                    Incidencia.conductor_id,
                    Incidencia.parada_id,
                    Incidencia.tipo,
                    Incidencia.severidad,
                    Incidencia.ocurrida_en,
                    func.ST_Y(_POINT),
                    func.ST_X(_POINT),
                    Incidencia.observacion,
                    Incidencia.estado,
                    Incidencia.registrada_en,
                ).where(Incidencia.operation_id == operation_id)
            ).one_or_none()
            return None if row is None else StoredIncidencia(*row)
        except SQLAlchemyError:
            raise IncidenciaStorageError("Incident storage unavailable") from None

    def add(
        self, incidencia: Incidencia, latitud: float, longitud: float
    ) -> Incidencia:
        incidencia.ubicacion = func.ST_SetSRID(
            func.ST_MakePoint(longitud, latitud), 4326
        ).cast(Geography(geometry_type="POINT", srid=4326))
        try:
            self._session.add(incidencia)
            self._session.flush()
            self._session.refresh(incidencia, ["registrada_en", "estado"])
            return incidencia
        except IntegrityError as error:
            constraint = getattr(
                getattr(error.orig, "diag", None), "constraint_name", None
            )
            if constraint == "uq_incidencia_operation_id":
                raise IncidenciaDuplicateOperation("Duplicate operation") from None
            raise IncidenciaStorageError("Incident storage unavailable") from None
        except SQLAlchemyError:
            raise IncidenciaStorageError("Incident storage unavailable") from None

    def list_page(
        self, estado: str, page: int, page_size: int
    ) -> tuple[list[IncidenciaRow], int]:
        try:
            total = self._session.scalar(
                select(func.count())
                .select_from(Incidencia)
                .where(Incidencia.estado == estado)
            )
            rows = self._session.execute(
                select(
                    Incidencia.incidencia_id,
                    Incidencia.tipo,
                    Incidencia.severidad,
                    Incidencia.ocurrida_en,
                    Incidencia.registrada_en,
                    Conductor.conductor_id,
                    Conductor.nombre,
                    func.ST_Y(_POINT),
                    func.ST_X(_POINT),
                    Incidencia.observacion,
                    Incidencia.estado,
                )
                .join(Conductor, Conductor.conductor_id == Incidencia.conductor_id)
                .where(Incidencia.estado == estado)
                .order_by(Incidencia.ocurrida_en.desc(), Incidencia.incidencia_id)
                .limit(page_size)
                .offset((page - 1) * page_size)
            ).all()
            return [IncidenciaRow(*row) for row in rows], int(total or 0)
        except SQLAlchemyError:
            raise IncidenciaStorageError("Incident storage unavailable") from None
