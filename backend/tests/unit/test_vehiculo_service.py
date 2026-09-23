from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models.vehiculo import Vehiculo
from app.repositories.auditoria import AuditStorageError, Evento
from app.repositories.vehiculos import DuplicatePlateError, VehicleStorageError
from app.schemas.vehiculo import VehicleCreate, VehicleUpdate
from app.services import vehiculos as module
from app.services.vehiculos import (
    VehicleDuplicatePlate,
    VehicleInactive,
    VehicleNotFound,
    VehicleUnavailable,
    VehiculoService,
)


def create_payload():
    return VehicleCreate(
        placa="ABC123",
        tipo="CAMIONETA",
        capacidad_kg=Decimal("1000.00"),
        capacidad_m3=Decimal("8.00"),
        rendimiento_km_l=Decimal("10.000"),
        factor_co2_kg_km=Decimal("0.30000"),
        anio_fabricacion=2024,
    )


def vehicle(**changes):
    values = {
        "vehiculo_id": uuid4(),
        "placa": "ABC123",
        "tipo": "CAMIONETA",
        "capacidad_kg": Decimal("1000.00"),
        "capacidad_m3": Decimal("8.00"),
        "rendimiento_km_l": Decimal("10.000"),
        "factor_co2_kg_km": Decimal("0.30000"),
        "anio_fabricacion": 2024,
        "estado": "ACTIVO",
    }
    values.update(changes)
    return Vehiculo(**values)


def service_mocks(monkeypatch):
    factory = MagicMock()
    transactional_session = factory.begin.return_value.__enter__.return_value
    read_session = factory.return_value.__enter__.return_value
    repository = MagicMock()
    audit_repository = MagicMock()
    repository_type = MagicMock(return_value=repository)
    audit_type = MagicMock(return_value=audit_repository)
    monkeypatch.setattr(module, "VehiculoRepository", repository_type)
    monkeypatch.setattr(module, "AuditoriaRepository", audit_type)
    return (
        VehiculoService(factory),
        factory,
        transactional_session,
        read_session,
        repository,
        audit_repository,
    )


def test_create_success(monkeypatch):
    service, factory, session, _, repository, _ = service_mocks(monkeypatch)
    created = service.create(create_payload())
    assert created.placa == "ABC123"
    repository.add.assert_called_once_with(created)
    module.VehiculoRepository.assert_called_once_with(session)
    factory.begin.return_value.__exit__.assert_called_once_with(None, None, None)


@pytest.mark.parametrize(
    "failure,expected",
    [
        (DuplicatePlateError(), VehicleDuplicatePlate),
        (VehicleStorageError(), VehicleUnavailable),
        (SQLAlchemyError(), VehicleUnavailable),
    ],
)
def test_create_failures_are_translated(monkeypatch, failure, expected):
    service, _, _, _, repository, _ = service_mocks(monkeypatch)
    repository.add.side_effect = failure
    with pytest.raises(expected):
        service.create(create_payload())


def test_get_and_list(monkeypatch):
    service, _, _, read_session, repository, _ = service_mocks(monkeypatch)
    row = vehicle()
    repository.get.return_value = row
    repository.list_all.return_value = [row]
    assert service.get(row.vehiculo_id) is row
    assert service.list_all() == [row]
    assert module.VehiculoRepository.call_args_list[0].args == (read_session,)


def test_get_not_found(monkeypatch):
    service, _, _, _, repository, _ = service_mocks(monkeypatch)
    repository.get.return_value = None
    with pytest.raises(VehicleNotFound):
        service.get(uuid4())


@pytest.mark.parametrize("method", ["get", "list_all"])
def test_read_storage_failures_are_sanitized(monkeypatch, method):
    service, _, _, _, repository, _ = service_mocks(monkeypatch)
    getattr(repository, method).side_effect = VehicleStorageError("private")
    with pytest.raises(VehicleUnavailable, match="^Vehicle service unavailable$"):
        getattr(service, method)(uuid4()) if method == "get" else service.list_all()


def test_patch_normal_same_value_and_parameter_audit(monkeypatch):
    service, _, session, _, repository, audit = service_mocks(monkeypatch)
    actor_id = uuid4()
    row = vehicle()
    repository.get_for_update.return_value = row

    assert service.update(row.vehiculo_id, VehicleUpdate(tipo="MOTO"), actor_id) is row
    assert row.tipo == "MOTO"
    audit.insert.assert_not_called()

    service.update(
        row.vehiculo_id,
        VehicleUpdate(rendimiento_km_l=Decimal("10.000")),
        actor_id,
    )
    audit.insert.assert_not_called()

    service.update(
        row.vehiculo_id,
        VehicleUpdate(
            rendimiento_km_l=Decimal("11.000"),
            factor_co2_kg_km=Decimal("0.25000"),
        ),
        actor_id,
    )
    record = audit.insert.call_args.args[0]
    assert record.evento is Evento.VEHICULO_PARAMETROS_ACTUALIZADOS
    assert record.usuario_id == actor_id and record.entidad_id == row.vehiculo_id
    assert record.detalle.campos_modificados == (
        "rendimiento_km_l",
        "factor_co2_kg_km",
    )
    module.VehiculoRepository.assert_called_with(session)


@pytest.mark.parametrize(
    "row,failure,expected",
    [
        (None, None, VehicleNotFound),
        (vehicle(estado="INACTIVO"), None, VehicleInactive),
        (vehicle(), DuplicatePlateError(), VehicleDuplicatePlate),
        (vehicle(), VehicleStorageError(), VehicleUnavailable),
    ],
)
def test_patch_failures(monkeypatch, row, failure, expected):
    service, _, _, _, repository, _ = service_mocks(monkeypatch)
    repository.get_for_update.return_value = row
    repository.flush.side_effect = failure
    with pytest.raises(expected):
        service.update(uuid4(), VehicleUpdate(placa="NEW123"), uuid4())


def test_patch_audit_failure_is_sanitized(monkeypatch):
    service, _, _, _, repository, audit = service_mocks(monkeypatch)
    repository.get_for_update.return_value = vehicle()
    audit.insert.side_effect = AuditStorageError("private")
    with pytest.raises(VehicleUnavailable, match="^Vehicle service unavailable$"):
        service.update(uuid4(), VehicleUpdate(rendimiento_km_l=Decimal("11")), uuid4())


def test_deactivate_active_and_idempotent(monkeypatch):
    service, _, _, _, repository, audit = service_mocks(monkeypatch)
    actor_id = uuid4()
    active = vehicle()
    repository.get_for_update.return_value = active
    service.deactivate(active.vehiculo_id, actor_id)
    assert active.estado == "INACTIVO"
    record = audit.insert.call_args.args[0]
    assert record.evento is Evento.VEHICULO_DESACTIVADO
    assert record.usuario_id == actor_id

    audit.reset_mock()
    service.deactivate(active.vehiculo_id, actor_id)
    audit.insert.assert_not_called()


@pytest.mark.parametrize(
    "row,failure,expected",
    [
        (None, None, VehicleNotFound),
        (vehicle(), VehicleStorageError(), VehicleUnavailable),
    ],
)
def test_deactivate_failures(monkeypatch, row, failure, expected):
    service, _, _, _, repository, _ = service_mocks(monkeypatch)
    repository.get_for_update.return_value = row
    repository.flush.side_effect = failure
    with pytest.raises(expected):
        service.deactivate(uuid4(), uuid4())


def test_deactivate_audit_failure_is_sanitized(monkeypatch):
    service, _, _, _, repository, audit = service_mocks(monkeypatch)
    repository.get_for_update.return_value = vehicle()
    audit.insert.side_effect = AuditStorageError("private")
    with pytest.raises(VehicleUnavailable, match="^Vehicle service unavailable$"):
        service.deactivate(uuid4(), uuid4())
