"""Transactional vehicle use cases and functional audit coordination."""

from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.models.vehiculo import Vehiculo
from app.repositories.auditoria import (
    AuditoriaRepository,
    AuditStorageError,
    DetalleParametrosVehiculo,
    DetalleVehiculoDesactivado,
    Evento,
    Registro,
)
from app.repositories.vehiculos import (
    DuplicatePlateError,
    VehicleStorageError,
    VehiculoRepository,
)
from app.schemas.vehiculo import VehicleCreate, VehicleUpdate


class VehicleNotFound(LookupError):
    """Requested vehicle does not exist."""


class VehicleInactive(RuntimeError):
    """Inactive vehicles cannot be modified."""


class VehicleUnavailable(RuntimeError):
    """Sanitized operational vehicle failure."""


class VehicleDuplicatePlate(ValueError):
    """The canonical plate is already registered."""


class VehiculoService:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def create(self, payload: VehicleCreate) -> Vehiculo:
        try:
            with self._factory.begin() as session:
                vehicle = Vehiculo(**payload.model_dump(mode="python"))
                VehiculoRepository(session).add(vehicle)
                return vehicle
        except DuplicatePlateError:
            raise VehicleDuplicatePlate("Vehicle plate already exists") from None
        except (VehicleStorageError, SQLAlchemyError):
            raise VehicleUnavailable("Vehicle service unavailable") from None

    def list_all(self) -> list[Vehiculo]:
        try:
            with self._factory() as session:
                return VehiculoRepository(session).list_all()
        except (VehicleStorageError, SQLAlchemyError):
            raise VehicleUnavailable("Vehicle service unavailable") from None

    def get(self, vehicle_id: UUID) -> Vehiculo:
        try:
            with self._factory() as session:
                vehicle = VehiculoRepository(session).get(vehicle_id)
                if vehicle is None:
                    raise VehicleNotFound("Vehicle not found")
                return vehicle
        except VehicleNotFound:
            raise
        except (VehicleStorageError, SQLAlchemyError):
            raise VehicleUnavailable("Vehicle service unavailable") from None

    def update(
        self, vehicle_id: UUID, payload: VehicleUpdate, actor_id: UUID
    ) -> Vehiculo:
        try:
            with self._factory.begin() as session:
                repository = VehiculoRepository(session)
                vehicle = repository.get_for_update(vehicle_id)
                if vehicle is None:
                    raise VehicleNotFound("Vehicle not found")
                if vehicle.estado == "INACTIVO":
                    raise VehicleInactive("Inactive vehicle cannot be modified")
                changes = payload.model_dump(exclude_unset=True, mode="python")
                audited_fields = tuple(
                    field
                    for field in ("rendimiento_km_l", "factor_co2_kg_km")
                    if field in changes and getattr(vehicle, field) != changes[field]
                )
                for field, value in changes.items():
                    setattr(vehicle, field, value)
                repository.flush()
                if audited_fields:
                    AuditoriaRepository(session).insert(
                        Registro(
                            usuario_id=actor_id,
                            entidad_id=vehicle.vehiculo_id,
                            evento=Evento.VEHICULO_PARAMETROS_ACTUALIZADOS,
                            detalle=DetalleParametrosVehiculo(
                                campos_modificados=audited_fields
                            ),
                        )
                    )
                return vehicle
        except (VehicleNotFound, VehicleInactive):
            raise
        except DuplicatePlateError:
            raise VehicleDuplicatePlate("Vehicle plate already exists") from None
        except (VehicleStorageError, AuditStorageError, SQLAlchemyError):
            raise VehicleUnavailable("Vehicle service unavailable") from None

    def deactivate(self, vehicle_id: UUID, actor_id: UUID) -> None:
        try:
            with self._factory.begin() as session:
                repository = VehiculoRepository(session)
                vehicle = repository.get_for_update(vehicle_id)
                if vehicle is None:
                    raise VehicleNotFound("Vehicle not found")
                if vehicle.estado == "INACTIVO":
                    return
                vehicle.estado = "INACTIVO"
                repository.flush()
                AuditoriaRepository(session).insert(
                    Registro(
                        usuario_id=actor_id,
                        entidad_id=vehicle.vehiculo_id,
                        evento=Evento.VEHICULO_DESACTIVADO,
                        detalle=DetalleVehiculoDesactivado(),
                    )
                )
        except VehicleNotFound:
            raise
        except (VehicleStorageError, AuditStorageError, SQLAlchemyError):
            raise VehicleUnavailable("Vehicle service unavailable") from None
