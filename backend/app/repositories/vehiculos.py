"""Vehicle persistence boundary; callers own transactions."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.vehiculo import Vehiculo


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

    def list_all(self) -> list[Vehiculo]:
        try:
            return list(
                self._session.scalars(select(Vehiculo).order_by(Vehiculo.placa)).all()
            )
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
