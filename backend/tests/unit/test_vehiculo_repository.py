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
    repository = VehiculoRepository(session)
    repository.add(row)
    assert repository.get(row.vehiculo_id) is row
    assert repository.get_for_update(row.vehiculo_id) is row
    assert session.scalar.call_args.args[0]._for_update_arg is not None
    repository.flush()
    session.commit.assert_not_called()


def test_list_page_reads_one_page_of_plain_rows():
    """ECL-109: only the response columns, one page and one count."""
    session = MagicMock()
    listing = [{"placa": "ABC123"}]
    session.scalar.return_value = 30
    session.execute.return_value.mappings.return_value = listing
    rows, total = VehiculoRepository(session).list_page(3, 12)
    assert rows == listing
    assert total == 30
    query = session.execute.call_args.args[0]
    assert [column.name for column in query.selected_columns] == [
        "vehiculo_id",
        "placa",
        "tipo",
        "capacidad_kg",
        "capacidad_m3",
        "rendimiento_km_l",
        "factor_co2_kg_km",
        "anio_fabricacion",
        "estado",
    ]
    compiled = query.compile(compile_kwargs={"literal_binds": True})
    assert "LIMIT 12" in str(compiled)
    assert "OFFSET 24" in str(compiled)
    assert "ORDER BY vehiculo.placa" in str(compiled)
    session.scalars.assert_not_called()
    session.commit.assert_not_called()


def test_list_page_counts_zero_on_empty_table():
    session = MagicMock()
    session.scalar.return_value = None
    session.execute.return_value.mappings.return_value = []
    assert VehiculoRepository(session).list_page(1, 12) == ([], 0)


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
    "operation", ["add", "get", "get_for_update", "list_page", "flush"]
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
        session.scalar.side_effect = SQLAlchemyError("private SQL")
    repository = VehiculoRepository(session)
    arguments = {
        "add": (Vehiculo(),),
        "get": (uuid4(),),
        "get_for_update": (uuid4(),),
        "list_page": (1, 12),
        "flush": (),
    }
    with pytest.raises(VehicleStorageError, match="^Vehicle storage unavailable$"):
        getattr(repository, operation)(*arguments[operation])
