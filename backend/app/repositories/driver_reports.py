"""Persistence for assigned stops and idempotent driver reports."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.driver_report import DriverReport
from app.models.driver_stop_assignment import DriverStopAssignment


class DriverReportStorageError(RuntimeError):
    """Sanitized report persistence failure."""


class DriverStopNotAssigned(DriverReportStorageError):
    """Stop is not assigned to the authenticated driver."""


class DriverReportConflict(DriverReportStorageError):
    """An operation ID was reused with a different report payload."""


class DriverReportConcurrentOperation(DriverReportStorageError):
    """A concurrent request committed the same operation ID."""


class DriverStopAlreadyReported(DriverReportStorageError):
    """A final delivery report already exists for the assigned stop."""


class DriverReportRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_assignments(self, owner_id: UUID) -> list[DriverStopAssignment]:
        try:
            return list(
                self._session.scalars(
                    select(DriverStopAssignment)
                    .where(DriverStopAssignment.owner_id == owner_id)
                    .order_by(
                        DriverStopAssignment.position,
                        DriverStopAssignment.stop_id,
                    )
                )
            )
        except SQLAlchemyError:
            raise DriverReportStorageError("Driver itinerary unavailable") from None

    def find_report(self, operation_id: UUID) -> DriverReport | None:
        try:
            return self._session.get(DriverReport, operation_id)
        except SQLAlchemyError:
            raise DriverReportStorageError("Driver report lookup unavailable") from None

    def save_report(
        self,
        *,
        owner_id: UUID,
        operation_id: UUID,
        stop_id: UUID,
        status: str,
    ) -> tuple[DriverReport, bool]:
        try:
            existing = self._session.get(DriverReport, operation_id)
            if existing is not None:
                if (
                    existing.owner_id != owner_id
                    or existing.stop_id != stop_id
                    or existing.status != status
                ):
                    raise DriverReportConflict("Operation ID conflict")
                return existing, False

            assignment = self._session.scalar(
                select(DriverStopAssignment)
                .where(
                    DriverStopAssignment.stop_id == stop_id,
                    DriverStopAssignment.owner_id == owner_id,
                )
                .with_for_update()
            )
            if assignment is None:
                raise DriverStopNotAssigned("Stop not assigned")
            existing = self._session.get(DriverReport, operation_id)
            if existing is not None:
                if (
                    existing.owner_id != owner_id
                    or existing.stop_id != stop_id
                    or existing.status != status
                ):
                    raise DriverReportConflict("Operation ID conflict")
                return existing, False
            if assignment.status in ("ENTREGADO", "NO_ENTREGADO"):
                raise DriverStopAlreadyReported("Stop already reported")

            report = DriverReport(
                operation_id=operation_id,
                owner_id=owner_id,
                stop_id=stop_id,
                status=status,
            )
            self._session.add(report)
            assignment.status = status
            self._session.flush()
            return report, True
        except (
            DriverReportConflict,
            DriverStopNotAssigned,
            DriverStopAlreadyReported,
        ):
            raise
        except IntegrityError:
            raise DriverReportConcurrentOperation("Concurrent operation ID") from None
        except SQLAlchemyError:
            raise DriverReportStorageError(
                "Driver report storage unavailable"
            ) from None
