"""Vehicle persistence boundary; callers own transactions."""

from uuid import UUID

from sqlalchemy import RowMapping, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.vehiculo import Vehiculo

# Columns of the listing (the fields of ``VehicleResponse``), read as plain rows.
LIST_COLUMNS = (
    Vehiculo.vehiculo_id,
    Vehiculo.placa,
    Vehiculo.tipo,
    Vehiculo.capacidad_kg,
    Vehiculo.capacidad_m3,
    Vehiculo.rendimiento_km_l,
    Vehiculo.factor_co2_kg_km,
    Vehiculo.anio_fabricacion,
    Vehiculo.estado,
)


class VehicleStorageError(RuntimeError):
    """Sanitized vehicle storage failure."""


class DuplicatePlateError(VehicleStorageError):
    """The canonical plate already exists."""


class VehiculoRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, vehicle: Vehiculo) -> None:
        try:
            self._session.add(vehicle)
            self._session.flush()
        except IntegrityError as error:
            constraint = getattr(
                getattr(error.orig, "diag", None), "constraint_name", None
            )
            if constraint == "uq_vehiculo_placa":
                raise DuplicatePlateError("Vehicle plate already exists") from None
            raise VehicleStorageError("Vehicle storage unavailable") from None
        except SQLAlchemyError:
            raise VehicleStorageError("Vehicle storage unavailable") from None

    def get(self, vehicle_id: UUID) -> Vehiculo | None:
        try:
            return self._session.get(Vehiculo, vehicle_id)
        except SQLAlchemyError:
            raise VehicleStorageError("Vehicle storage unavailable") from None

    def get_for_update(self, vehicle_id: UUID) -> Vehiculo | None:
        try:
            return self._session.scalar(
                select(Vehiculo)
                .where(Vehiculo.vehiculo_id == vehicle_id)
                .with_for_update()
            )
        except SQLAlchemyError:
            raise VehicleStorageError("Vehicle storage unavailable") from None

    def list_page(self, page: int, page_size: int) -> tuple[list[RowMapping], int]:
        """Return one page of vehicles as plain rows ordered by plate.

        Green IT (ECL-109): before, the whole fleet was loaded as ORM
        entities on every request; now only one page is read, as rows with
        the columns of the response, plus one ``count``.
        """
        try:
            total = self._session.scalar(select(func.count()).select_from(Vehiculo))
            query = (
                select(*LIST_COLUMNS)
                .order_by(Vehiculo.placa, Vehiculo.vehiculo_id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            return list(self._session.execute(query).mappings()), total or 0
        except SQLAlchemyError:
            raise VehicleStorageError("Vehicle storage unavailable") from None

    def flush(self) -> None:
        try:
            self._session.flush()
        except IntegrityError as error:
            constraint = getattr(
                getattr(error.orig, "diag", None), "constraint_name", None
            )
            if constraint == "uq_vehiculo_placa":
                raise DuplicatePlateError("Vehicle plate already exists") from None
            raise VehicleStorageError("Vehicle storage unavailable") from None
        except SQLAlchemyError:
            raise VehicleStorageError("Vehicle storage unavailable") from None
