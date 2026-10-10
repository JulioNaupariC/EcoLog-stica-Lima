"""Authenticated-driver itinerary and report use cases."""

from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.models.driver_stop_assignment import DriverStopAssignment
from app.models.pedido import Pedido
from app.models.usuario import Usuario
from app.repositories.driver_reports import (
    DriverReportConcurrentOperation,
    DriverReportConflict,
    DriverReportRepository,
    DriverReportStorageError,
    DriverStopAlreadyReported,
    DriverStopNotAssigned,
)
from app.schemas.driver_report import (
    AssignedStopResponse,
    DeliveryDetails,
    DriverReportAcknowledgement,
    DriverReportCreate,
)


class DriverReportUnavailable(RuntimeError):
    """Sanitized itinerary or report service failure."""


class DriverReportIdentityConflict(RuntimeError):
    """An idempotency key belongs to a different event or account."""


class DriverReportStopNotAssigned(RuntimeError):
    """The stop is not assigned to the authenticated driver."""


class DriverReportAlreadyFinal(RuntimeError):
    """A terminal delivery result already exists for this stop."""


class DriverAssignmentInvalid(ValueError):
    """Invalid assignment data supplied by a trusted route-planning adapter."""


class DriverReportService:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def list_assignments(self, owner_id: UUID) -> list[AssignedStopResponse]:
        try:
            with self._factory() as session:
                rows = DriverReportRepository(session).list_assignments(owner_id)
                return [
                    AssignedStopResponse(
                        stop_id=row.stop_id,
                        position=row.position,
                        status=row.status,
                        delivery=self._delivery(session, row.pedido_id),
                    )
                    for row in rows
                ]
        except (DriverReportStorageError, SQLAlchemyError):
            raise DriverReportUnavailable("Driver itinerary unavailable") from None

    def save_report(
        self, owner_id: UUID, payload: DriverReportCreate
    ) -> DriverReportAcknowledgement:
        try:
            with self._factory.begin() as session:
                report, _created = DriverReportRepository(session).save_report(
                    owner_id=owner_id,
                    operation_id=payload.operation_id,
                    stop_id=payload.stop_id,
                    status=payload.status.value,
                )
                operation_id = report.operation_id
            return DriverReportAcknowledgement(operation_id=operation_id)
        except DriverReportConcurrentOperation:
            try:
                with self._factory() as session:
                    report = DriverReportRepository(session).find_report(
                        payload.operation_id
                    )
            except DriverReportStorageError:
                raise DriverReportUnavailable("Driver report unavailable") from None
            if report is None:
                raise DriverReportUnavailable("Driver report unavailable") from None
            if (
                report.owner_id != owner_id
                or report.stop_id != payload.stop_id
                or report.status != payload.status.value
            ):
                raise DriverReportIdentityConflict("Operation ID conflict") from None
            return DriverReportAcknowledgement(operation_id=report.operation_id)
        except DriverReportConflict:
            raise DriverReportIdentityConflict("Operation ID conflict") from None
        except DriverStopNotAssigned:
            raise DriverReportStopNotAssigned("Stop not assigned") from None
        except DriverStopAlreadyReported:
            raise DriverReportAlreadyFinal("Stop already reported") from None
        except DriverReportStorageError:
            raise DriverReportUnavailable("Driver report unavailable") from None
        except SQLAlchemyError:
            raise DriverReportUnavailable("Driver report unavailable") from None

    def provision_assignment(
        self,
        *,
        stop_id: UUID,
        owner_id: UUID,
        position: int,
        status: str = "PENDIENTE",
        pedido_id: UUID | None = None,
    ) -> None:
        """Trusted route-planning integration point; never expose to driver clients."""
        if (
            not isinstance(position, int)
            or isinstance(position, bool)
            or position < 1
            or status not in ("PENDIENTE", "EN_RUTA")
        ):
            raise DriverAssignmentInvalid("Invalid driver assignment")
        try:
            with self._factory.begin() as session:
                if pedido_id is not None and session.get(Pedido, pedido_id) is None:
                    raise DriverAssignmentInvalid("Order does not exist")
                driver = session.get(Usuario, owner_id)
                if (
                    driver is None
                    or driver.rol != "CONDUCTOR"
                    or driver.estado != "ACTIVO"
                ):
                    raise DriverReportStopNotAssigned("Driver is not active")
                existing = session.get(DriverStopAssignment, stop_id)
                if existing is not None:
                    if pedido_id is not None and existing.pedido_id not in (
                        None,
                        pedido_id,
                    ):
                        raise DriverReportIdentityConflict(
                            "Stop belongs to another order"
                        )
                    if existing.owner_id != owner_id:
                        raise DriverReportIdentityConflict("Stop is assigned elsewhere")
                    if existing.status in ("ENTREGADO", "NO_ENTREGADO"):
                        raise DriverReportAlreadyFinal("Stop already reported")
                    existing.position = position
                    if pedido_id is not None:
                        existing.pedido_id = pedido_id
                    if status != "PENDIENTE":
                        existing.status = status
                else:
                    session.add(
                        DriverStopAssignment(
                            stop_id=stop_id,
                            owner_id=owner_id,
                            position=position,
                            status=status,
                            pedido_id=pedido_id,
                        )
                    )
        except (
            DriverReportStopNotAssigned,
            DriverReportIdentityConflict,
            DriverReportAlreadyFinal,
        ):
            raise
        except SQLAlchemyError:
            raise DriverReportUnavailable("Driver assignment unavailable") from None

    @staticmethod
    def _delivery(session: Session, pedido_id: UUID | None) -> DeliveryDetails | None:
        if pedido_id is None:
            return None
        pedido = session.get(Pedido, pedido_id)
        if pedido is None:
            raise DriverReportStorageError("Assigned order unavailable")
        return DeliveryDetails(
            address=pedido.direccion,
            reference=pedido.referencia,
            window_start=pedido.ventana_inicio,
            window_end=pedido.ventana_fin,
        )
