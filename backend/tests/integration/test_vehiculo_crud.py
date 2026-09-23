from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event, Lock
from time import monotonic, sleep
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import sessionmaker

from alembic import command
from app.models.auditoria import Auditoria
from app.models.vehiculo import Vehiculo
from app.repositories.auditoria import AuditoriaRepository, AuditStorageError
from app.repositories.vehiculos import VehiculoRepository
from app.schemas.vehiculo import VehicleCreate, VehicleUpdate
from app.services.vehiculos import (
    VehicleDuplicatePlate,
    VehicleInactive,
    VehicleNotFound,
    VehicleUnavailable,
    VehiculoService,
)

pytestmark = pytest.mark.integration


def payload(**changes):
    values = {
        "placa": " abc-123 ",
        "tipo": "CAMIONETA",
        "capacidad_kg": Decimal("1000.00"),
        "capacidad_m3": Decimal("8.00"),
        "rendimiento_km_l": Decimal("10.000"),
        "factor_co2_kg_km": Decimal("0.30000"),
        "anio_fabricacion": 2024,
    }
    values.update(changes)
    return VehicleCreate(**values)


def setup_service(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with engine.begin() as connection:
        actor_id = connection.scalar(
            text(
                "INSERT INTO usuario (email, password_hash, rol) "
                "VALUES ('vehicle-actor@example.test', 'placeholder', 'ADMINISTRADOR') "
                "RETURNING usuario_id"
            )
        )
    return engine, factory, VehiculoService(factory), actor_id


def clear_functional_audits(engine):
    with engine.begin() as connection:
        connection.execute(
            text(
                "DELETE FROM auditoria WHERE accion IN "
                "('VEHICULO_PARAMETROS_ACTUALIZADOS','VEHICULO_DESACTIVADO')"
            )
        )


def concurrency_gates(monkeypatch):
    first_audit_entered = Event()
    release_first = Event()
    second_pid_observed = Event()
    counter_lock = Lock()
    lock_calls = 0
    audit_calls = 0
    transaction_pids = {}
    real_get_for_update = VehiculoRepository.get_for_update
    real_insert = AuditoriaRepository.insert

    def observed_get_for_update(self, vehicle_id):
        nonlocal lock_calls
        self._session.execute(text("SET LOCAL lock_timeout = '10s'"))
        self._session.execute(text("SET LOCAL statement_timeout = '15s'"))
        backend_pid = self._session.scalar(text("SELECT pg_backend_pid()"))
        with counter_lock:
            lock_calls += 1
            call_number = lock_calls
            transaction_pids[call_number] = backend_pid
        if call_number == 2:
            second_pid_observed.set()
        return real_get_for_update(self, vehicle_id)

    def gated_insert(self, record):
        nonlocal audit_calls
        with counter_lock:
            audit_calls += 1
            call_number = audit_calls
        if call_number == 1:
            first_audit_entered.set()
            assert release_first.wait(15), "first transaction was not released"
        return real_insert(self, record)

    monkeypatch.setattr(VehiculoRepository, "get_for_update", observed_get_for_update)
    monkeypatch.setattr(AuditoriaRepository, "insert", gated_insert)
    return first_audit_entered, release_first, second_pid_observed, transaction_pids


def wait_for_database_blocking(engine, blocked_pid, blocking_pid, timeout=8.0):
    deadline = monotonic() + timeout
    with engine.connect() as observer:
        while monotonic() < deadline:
            blocking_pids = observer.scalar(
                text("SELECT pg_blocking_pids(:blocked_pid)"),
                {"blocked_pid": blocked_pid},
            )
            if blocking_pid in blocking_pids:
                return blocking_pids
            sleep(0.05)
    pytest.fail(
        f"PostgreSQL did not report PID {blocking_pid} blocking PID {blocked_pid}"
    )


def audit_count(factory, action):
    with factory() as session:
        return session.scalar(
            select(func.count())
            .select_from(Auditoria)
            .where(Auditoria.accion == action)
        )


def test_real_crud_normalization_duplicate_and_not_found(migration_database):
    engine, _factory, service, actor_id = setup_service(migration_database)
    vehicle = service.create(payload())
    assert vehicle.placa == "ABC-123"
    assert service.get(vehicle.vehiculo_id).vehiculo_id == vehicle.vehiculo_id
    assert [row.vehiculo_id for row in service.list_all()] == [vehicle.vehiculo_id]
    with pytest.raises(VehicleDuplicatePlate):
        service.create(payload())
    with pytest.raises(VehicleNotFound):
        service.get(uuid4())
    service.deactivate(vehicle.vehiculo_id, actor_id)
    assert service.get(vehicle.vehiculo_id).estado == "INACTIVO"
    clear_functional_audits(engine)


def test_patch_audits_only_real_parameter_changes(migration_database):
    engine, factory, service, actor_id = setup_service(migration_database)
    vehicle = service.create(payload())
    service.update(vehicle.vehiculo_id, VehicleUpdate(tipo="MOTO"), actor_id)
    service.update(
        vehicle.vehiculo_id,
        VehicleUpdate(rendimiento_km_l=Decimal("10.000")),
        actor_id,
    )
    service.update(
        vehicle.vehiculo_id,
        VehicleUpdate(
            rendimiento_km_l=Decimal("11.000"),
            factor_co2_kg_km=Decimal("0.25000"),
        ),
        actor_id,
    )
    with factory() as session:
        audits = list(
            session.scalars(
                select(Auditoria).where(
                    Auditoria.accion == "VEHICULO_PARAMETROS_ACTUALIZADOS"
                )
            )
        )
        assert len(audits) == 1
        assert audits[0].entidad == "vehiculo"
        assert audits[0].entidad_id == vehicle.vehiculo_id
        assert audits[0].usuario_id == actor_id
        assert set(audits[0].detalle["campos_modificados"]) == {
            "rendimiento_km_l",
            "factor_co2_kg_km",
        }
    assert service.get(vehicle.vehiculo_id).rendimiento_km_l == Decimal("11.000")
    clear_functional_audits(engine)


def test_deactivation_is_audited_idempotent_and_blocks_patch(migration_database):
    engine, factory, service, actor_id = setup_service(migration_database)
    vehicle = service.create(payload())
    service.deactivate(vehicle.vehiculo_id, actor_id)
    service.deactivate(vehicle.vehiculo_id, actor_id)
    with factory() as session:
        stored = session.get(Vehiculo, vehicle.vehiculo_id)
        assert stored is not None and stored.estado == "INACTIVO"
        assert (
            session.scalar(
                select(text("count(*)"))
                .select_from(Auditoria)
                .where(Auditoria.accion == "VEHICULO_DESACTIVADO")
            )
            == 1
        )
    with pytest.raises(VehicleInactive):
        service.update(vehicle.vehiculo_id, VehicleUpdate(tipo="MOTO"), actor_id)
    clear_functional_audits(engine)


def test_functional_audit_failure_rolls_back_change(migration_database, monkeypatch):
    _engine, _factory, service, actor_id = setup_service(migration_database)
    vehicle = service.create(payload())

    def fail_audit(self, record):
        raise AuditStorageError("private audit error")

    monkeypatch.setattr(AuditoriaRepository, "insert", fail_audit)
    with pytest.raises(VehicleUnavailable, match="^Vehicle service unavailable$"):
        service.update(
            vehicle.vehiculo_id,
            VehicleUpdate(rendimiento_km_l=Decimal("12.000")),
            actor_id,
        )
    assert service.get(vehicle.vehiculo_id).rendimiento_km_l == Decimal("10.000")


def test_deactivation_audit_failure_rolls_back_state(migration_database, monkeypatch):
    _engine, _factory, service, actor_id = setup_service(migration_database)
    vehicle = service.create(payload())

    def fail_audit(self, record):
        raise AuditStorageError("private audit error")

    monkeypatch.setattr(AuditoriaRepository, "insert", fail_audit)
    with pytest.raises(VehicleUnavailable, match="^Vehicle service unavailable$"):
        service.deactivate(vehicle.vehiculo_id, actor_id)
    assert service.get(vehicle.vehiculo_id).estado == "ACTIVO"


def test_concurrent_deactivations_emit_one_transition(migration_database, monkeypatch):
    engine, factory, service, actor_id = setup_service(migration_database)
    vehicle = service.create(payload())
    entered, release, second_pid_observed, pids = concurrency_gates(monkeypatch)
    executor = ThreadPoolExecutor(max_workers=2)
    try:
        first = executor.submit(service.deactivate, vehicle.vehiculo_id, actor_id)
        assert entered.wait(10)
        second = executor.submit(service.deactivate, vehicle.vehiculo_id, actor_id)
        assert second_pid_observed.wait(10)
        assert pids[1] != pids[2]
        assert pids[1] in wait_for_database_blocking(engine, pids[2], pids[1])
        assert not second.done()
        release.set()
        first.result(timeout=20)
        second.result(timeout=20)
    finally:
        release.set()
        executor.shutdown(wait=True, cancel_futures=True)

    assert service.get(vehicle.vehiculo_id).estado == "INACTIVO"
    assert audit_count(factory, "VEHICULO_DESACTIVADO") == 1
    clear_functional_audits(engine)


def test_delete_committed_before_patch_blocks_mutation(migration_database, monkeypatch):
    engine, factory, service, actor_id = setup_service(migration_database)
    vehicle = service.create(payload())
    entered, release, second_pid_observed, pids = concurrency_gates(monkeypatch)
    executor = ThreadPoolExecutor(max_workers=2)
    try:
        deletion = executor.submit(service.deactivate, vehicle.vehiculo_id, actor_id)
        assert entered.wait(10)
        patch = executor.submit(
            service.update,
            vehicle.vehiculo_id,
            VehicleUpdate(rendimiento_km_l=Decimal("12.000")),
            actor_id,
        )
        assert second_pid_observed.wait(10)
        assert pids[1] != pids[2]
        assert pids[1] in wait_for_database_blocking(engine, pids[2], pids[1])
        assert not patch.done()
        release.set()
        deletion.result(timeout=20)
        with pytest.raises(VehicleInactive):
            patch.result(timeout=20)
    finally:
        release.set()
        executor.shutdown(wait=True, cancel_futures=True)

    stored = service.get(vehicle.vehiculo_id)
    assert stored.estado == "INACTIVO"
    assert stored.rendimiento_km_l == Decimal("10.000")
    assert audit_count(factory, "VEHICULO_DESACTIVADO") == 1
    assert audit_count(factory, "VEHICULO_PARAMETROS_ACTUALIZADOS") == 0
    clear_functional_audits(engine)


def test_concurrent_same_patch_emits_one_real_change(migration_database, monkeypatch):
    engine, factory, service, actor_id = setup_service(migration_database)
    vehicle = service.create(payload())
    entered, release, second_pid_observed, pids = concurrency_gates(monkeypatch)
    update = VehicleUpdate(rendimiento_km_l=Decimal("11.000"))

    executor = ThreadPoolExecutor(max_workers=2)
    try:
        first = executor.submit(service.update, vehicle.vehiculo_id, update, actor_id)
        assert entered.wait(10)
        second = executor.submit(service.update, vehicle.vehiculo_id, update, actor_id)
        assert second_pid_observed.wait(10)
        assert pids[1] != pids[2]
        assert pids[1] in wait_for_database_blocking(engine, pids[2], pids[1])
        assert not second.done()
        release.set()
        first.result(timeout=20)
        second.result(timeout=20)
    finally:
        release.set()
        executor.shutdown(wait=True, cancel_futures=True)

    assert service.get(vehicle.vehiculo_id).rendimiento_km_l == Decimal("11.000")
    assert audit_count(factory, "VEHICULO_PARAMETROS_ACTUALIZADOS") == 1
    clear_functional_audits(engine)
