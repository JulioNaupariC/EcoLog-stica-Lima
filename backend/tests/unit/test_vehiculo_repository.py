from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.vehiculo import Vehiculo
from app.repositories.vehiculos import (
    DuplicatePlateError,
    VehicleStorageError,
    VehiculoRepository,
)


def integrity_error(constraint):
    original = SimpleNamespace(diag=SimpleNamespace(constraint_name=constraint))
    return IntegrityError("private statement", {}, original)


def test_repository_add_get_list_and_flush_without_commit():
    session = MagicMock()
    row = Vehiculo(vehiculo_id=uuid4(), placa="ABC123")
    session.get.return_value = row
    session.scalar.return_value = row
    session.scalars.return_value.all.return_value = [row]
    repository = VehiculoRepository(session)
    repository.add(row)
    assert repository.get(row.vehiculo_id) is row
    assert repository.get_for_update(row.vehiculo_id) is row
    assert session.scalar.call_args.args[0]._for_update_arg is not None
    assert repository.list_all() == [row]
    repository.flush()
    session.commit.assert_not_called()


@pytest.mark.parametrize("operation", ["add", "flush"])
def test_duplicate_plate_is_classified_without_driver_details(operation):
    session = MagicMock()
    session.flush.side_effect = integrity_error("uq_vehiculo_placa")
    repository = VehiculoRepository(session)
    with pytest.raises(DuplicatePlateError, match="^Vehicle plate already exists$"):
        if operation == "add":
            repository.add(Vehiculo())
        else:
            repository.flush()


@pytest.mark.parametrize(
    "operation", ["add", "get", "get_for_update", "list_all", "flush"]
)
def test_repository_failures_are_sanitized(operation):
    session = MagicMock()
    if operation in ("add", "flush"):
        session.flush.side_effect = SQLAlchemyError("private SQL")
    elif operation == "get":
        session.get.side_effect = SQLAlchemyError("private SQL")
    elif operation == "get_for_update":
        session.scalar.side_effect = SQLAlchemyError("private SQL")
    else:
        session.scalars.side_effect = SQLAlchemyError("private SQL")
    repository = VehiculoRepository(session)
    arguments = {
        "add": (Vehiculo(),),
        "get": (uuid4(),),
        "get_for_update": (uuid4(),),
        "list_all": (),
        "flush": (),
    }
    with pytest.raises(VehicleStorageError, match="^Vehicle storage unavailable$"):
        getattr(repository, operation)(*arguments[operation])
