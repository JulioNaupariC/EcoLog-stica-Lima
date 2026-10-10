from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.models.driver_report import DriverReport
from app.models.driver_stop_assignment import DriverStopAssignment
from app.models.usuario import Usuario
from app.repositories.driver_reports import (
    DriverReportConcurrentOperation,
    DriverReportConflict,
    DriverReportRepository,
    DriverReportStorageError,
)
from app.schemas.driver_report import DriverReportCreate
from app.services.driver_reports import (
    DriverAssignmentInvalid,
    DriverReportAlreadyFinal,
    DriverReportIdentityConflict,
    DriverReportService,
    DriverReportStopNotAssigned,
    DriverReportUnavailable,
)


@pytest.fixture
def service():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Usuario.__table__.create(engine)
    DriverStopAssignment.__table__.create(engine)
    DriverReport.__table__.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as session:
        session.add_all(
            [
                Usuario(
                    usuario_id=uuid4(),
                    email="driver@example.test",
                    password_hash="not-a-real-hash",
                    rol="CONDUCTOR",
                    estado="ACTIVO",
                ),
                Usuario(
                    usuario_id=uuid4(),
                    email="other@example.test",
                    password_hash="not-a-real-hash",
                    rol="CONDUCTOR",
                    estado="ACTIVO",
                ),
                Usuario(
                    usuario_id=uuid4(),
                    email="operator@example.test",
                    password_hash="not-a-real-hash",
                    rol="OPERADOR",
                    estado="ACTIVO",
                ),
            ]
        )
    with factory() as session:
        identities = {
            user.email: user.usuario_id for user in session.scalars(select(Usuario))
        }
    yield DriverReportService(factory), identities, factory
    engine.dispose()


def test_provisions_assignment_only_for_active_conductor(service):
    reports, identities, factory = service
    stop_id = uuid4()
    driver_id = identities["driver@example.test"]

    reports.provision_assignment(
        stop_id=stop_id,
        owner_id=driver_id,
        position=1,
    )

    with factory() as session:
        assignment = session.get(DriverStopAssignment, stop_id)
        assert assignment is not None
        assert assignment.owner_id == driver_id
        assert assignment.position == 1
        assert assignment.status == "PENDIENTE"
    assert [
        stop.model_dump(mode="json", exclude_none=True)
        for stop in reports.list_assignments(driver_id)
    ] == [
        {
            "stop_id": str(stop_id),
            "position": 1,
            "status": "PENDIENTE",
        }
    ]

    with pytest.raises(DriverReportStopNotAssigned):
        reports.provision_assignment(
            stop_id=uuid4(),
            owner_id=identities["operator@example.test"],
            position=1,
        )


def test_report_ack_is_idempotent_and_updates_assigned_stop_once(service):
    reports, identities, factory = service
    owner_id = identities["driver@example.test"]
    stop_id = uuid4()
    operation_id = uuid4()
    reports.provision_assignment(stop_id=stop_id, owner_id=owner_id, position=1)
    payload = DriverReportCreate(
        operation_id=operation_id,
        stop_id=stop_id,
        status="ENTREGADO",
    )

    first = reports.save_report(owner_id, payload)
    replay = reports.save_report(owner_id, payload)

    assert first == replay
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(DriverReport)) == 1
        assert session.get(DriverStopAssignment, stop_id).status == "ENTREGADO"


def test_operation_id_cannot_be_reused_for_a_different_payload(service):
    reports, identities, _ = service
    owner_id = identities["driver@example.test"]
    stop_id = uuid4()
    operation_id = uuid4()
    reports.provision_assignment(stop_id=stop_id, owner_id=owner_id, position=1)
    reports.save_report(
        owner_id,
        DriverReportCreate(
            operation_id=operation_id,
            stop_id=stop_id,
            status="ENTREGADO",
        ),
    )

    with pytest.raises(DriverReportIdentityConflict):
        reports.save_report(
            owner_id,
            DriverReportCreate(
                operation_id=operation_id,
                stop_id=stop_id,
                status="NO_ENTREGADO",
            ),
        )


def test_report_cannot_cross_owner_or_reopen_a_final_stop(service):
    reports, identities, _ = service
    owner_id = identities["driver@example.test"]
    other_id = identities["other@example.test"]
    stop_id = uuid4()
    reports.provision_assignment(stop_id=stop_id, owner_id=owner_id, position=1)

    with pytest.raises(DriverReportStopNotAssigned):
        reports.save_report(
            other_id,
            DriverReportCreate(
                operation_id=uuid4(),
                stop_id=stop_id,
                status="ENTREGADO",
            ),
        )
    reports.save_report(
        owner_id,
        DriverReportCreate(
            operation_id=uuid4(),
            stop_id=stop_id,
            status="NO_ENTREGADO",
        ),
    )
    with pytest.raises(DriverReportAlreadyFinal):
        reports.save_report(
            owner_id,
            DriverReportCreate(
                operation_id=uuid4(),
                stop_id=stop_id,
                status="ENTREGADO",
            ),
        )


@pytest.mark.parametrize(
    "position,status",
    [
        (0, "PENDIENTE"),
        (-1, "PENDIENTE"),
        (True, "PENDIENTE"),
        (1, "DESCONOCIDO"),
        (1, "ENTREGADO"),
    ],
)
def test_invalid_assignment_data_is_rejected_before_database_access(
    service, position, status
):
    reports, identities, _ = service

    with pytest.raises(DriverAssignmentInvalid):
        reports.provision_assignment(
            stop_id=uuid4(),
            owner_id=identities["driver@example.test"],
            position=position,
            status=status,
        )


def test_assignment_conflicts_and_final_status_are_rejected(service):
    reports, identities, _ = service
    first_owner = identities["driver@example.test"]
    second_owner = identities["other@example.test"]
    stop_id = uuid4()
    reports.provision_assignment(stop_id=stop_id, owner_id=first_owner, position=1)

    with pytest.raises(DriverReportIdentityConflict):
        reports.provision_assignment(stop_id=stop_id, owner_id=second_owner, position=2)

    reports.provision_assignment(
        stop_id=stop_id,
        owner_id=first_owner,
        position=2,
        status="EN_RUTA",
    )
    reports.provision_assignment(
        stop_id=stop_id,
        owner_id=first_owner,
        position=3,
        status="PENDIENTE",
    )
    reports.save_report(
        first_owner,
        DriverReportCreate(
            operation_id=uuid4(),
            stop_id=stop_id,
            status="ENTREGADO",
        ),
    )
    with pytest.raises(DriverReportAlreadyFinal):
        reports.provision_assignment(
            stop_id=stop_id,
            owner_id=first_owner,
            position=1,
        )


@pytest.mark.parametrize(
    "stored_report,expected_error",
    [
        (
            lambda owner_id, payload: SimpleNamespace(
                owner_id=owner_id,
                stop_id=payload.stop_id,
                status=payload.status.value,
                operation_id=payload.operation_id,
            ),
            None,
        ),
        (
            lambda owner_id, payload: SimpleNamespace(
                owner_id=uuid4(),
                stop_id=payload.stop_id,
                status=payload.status.value,
                operation_id=payload.operation_id,
            ),
            DriverReportIdentityConflict,
        ),
        (lambda _owner_id, _payload: None, DriverReportUnavailable),
        (
            lambda _owner_id, _payload: (_ for _ in ()).throw(
                DriverReportStorageError("private")
            ),
            DriverReportUnavailable,
        ),
    ],
)
def test_concurrent_replay_is_acknowledged_only_for_the_same_report(
    service, monkeypatch, stored_report, expected_error
):
    reports, identities, _ = service
    owner_id = identities["driver@example.test"]
    payload = DriverReportCreate(
        operation_id=uuid4(),
        stop_id=uuid4(),
        status="ENTREGADO",
    )

    def report_concurrently_written(_self, **_kwargs):
        raise DriverReportConcurrentOperation("concurrent insert")

    monkeypatch.setattr(
        DriverReportRepository, "save_report", report_concurrently_written
    )
    monkeypatch.setattr(
        DriverReportRepository,
        "find_report",
        lambda _self, _operation_id: stored_report(owner_id, payload),
    )

    if expected_error is None:
        acknowledgement = reports.save_report(owner_id, payload)
        assert acknowledgement.operation_id == payload.operation_id
    else:
        with pytest.raises(expected_error):
            reports.save_report(owner_id, payload)


@pytest.mark.parametrize("failure", [DriverReportStorageError, SQLAlchemyError])
def test_report_service_sanitizes_persistence_errors(service, monkeypatch, failure):
    reports, identities, _ = service

    def failed_save(_self, **_kwargs):
        raise failure("private database detail")

    monkeypatch.setattr(DriverReportRepository, "save_report", failed_save)
    with pytest.raises(DriverReportUnavailable) as error:
        reports.save_report(
            identities["driver@example.test"],
            DriverReportCreate(
                operation_id=uuid4(),
                stop_id=uuid4(),
                status="ENTREGADO",
            ),
        )

    assert "private database detail" not in str(error.value)


def test_itinerary_service_sanitizes_storage_errors(service, monkeypatch):
    reports, identities, _ = service
    monkeypatch.setattr(
        DriverReportRepository,
        "list_assignments",
        Mock(side_effect=DriverReportStorageError("private database detail")),
    )

    with pytest.raises(DriverReportUnavailable) as error:
        reports.list_assignments(identities["driver@example.test"])

    assert "private database detail" not in str(error.value)


def test_assignment_service_sanitizes_storage_errors(service):
    reports, identities, factory = service
    factory.kw["bind"].dispose()

    with pytest.raises(DriverReportUnavailable):
        reports.provision_assignment(
            stop_id=uuid4(),
            owner_id=identities["driver@example.test"],
            position=1,
        )


@pytest.mark.parametrize(
    "method,expected_message",
    [
        ("list_assignments", "Driver itinerary unavailable"),
        ("find_report", "Driver report lookup unavailable"),
    ],
)
def test_repository_lookup_errors_are_sanitized(method, expected_message):
    session = Mock()
    repository = DriverReportRepository(session)
    if method == "list_assignments":
        session.scalars.side_effect = SQLAlchemyError("private database detail")

        def operation():
            return repository.list_assignments(uuid4())
    else:
        session.get.side_effect = SQLAlchemyError("private database detail")

        def operation():
            return repository.find_report(uuid4())

    with pytest.raises(DriverReportStorageError) as error:
        operation()

    assert str(error.value) == expected_message
    assert "private database detail" not in str(error.value)


def test_repository_handles_idempotent_race_and_database_errors():
    owner_id, stop_id, operation_id = uuid4(), uuid4(), uuid4()
    assignment = SimpleNamespace(status="PENDIENTE")
    concurrent_report = SimpleNamespace(
        owner_id=owner_id,
        stop_id=stop_id,
        status="ENTREGADO",
        operation_id=operation_id,
    )
    session = Mock()
    session.get.side_effect = [None, concurrent_report]
    session.scalar.return_value = assignment
    repository = DriverReportRepository(session)

    assert repository.save_report(
        owner_id=owner_id,
        operation_id=operation_id,
        stop_id=stop_id,
        status="ENTREGADO",
    ) == (concurrent_report, False)

    conflicting_report = SimpleNamespace(
        owner_id=uuid4(),
        stop_id=stop_id,
        status="ENTREGADO",
        operation_id=operation_id,
    )
    session = Mock()
    session.get.side_effect = [None, conflicting_report]
    session.scalar.return_value = assignment
    with pytest.raises(DriverReportConflict):
        DriverReportRepository(session).save_report(
            owner_id=owner_id,
            operation_id=operation_id,
            stop_id=stop_id,
            status="ENTREGADO",
        )

    assignment.status = "PENDIENTE"
    session = Mock()
    session.get.side_effect = [None, None]
    session.scalar.return_value = assignment
    session.flush.side_effect = SQLAlchemyError("private database detail")
    with pytest.raises(
        DriverReportStorageError,
        match="Driver report storage unavailable",
    ):
        DriverReportRepository(session).save_report(
            owner_id=owner_id,
            operation_id=operation_id,
            stop_id=stop_id,
            status="ENTREGADO",
        )

    assignment.status = "PENDIENTE"
    session = Mock()
    session.get.side_effect = [None, None]
    session.scalar.return_value = assignment
    session.flush.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
    with pytest.raises(DriverReportConcurrentOperation):
        DriverReportRepository(session).save_report(
            owner_id=owner_id,
            operation_id=operation_id,
            stop_id=stop_id,
            status="ENTREGADO",
        )

    session = Mock()
    session.get.side_effect = SQLAlchemyError("private database detail")
    with pytest.raises(
        DriverReportStorageError, match="Driver report storage unavailable"
    ):
        DriverReportRepository(session).save_report(
            owner_id=owner_id,
            operation_id=operation_id,
            stop_id=stop_id,
            status="ENTREGADO",
        )
