from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.pedido import Pedido
from app.repositories.clientes import ClienteRepository, ClienteStorageError
from app.repositories.pedidos import (
    PedidoClienteMissing,
    PedidoRepository,
    PedidoStorageError,
)


def order():
    return Pedido(
        pedido_id=uuid4(),
        cliente_id=uuid4(),
        direccion="Av. Principal",
        peso_kg=Decimal("1.00"),
        volumen_m3=Decimal("0.100"),
        ventana_inicio=datetime(2026, 10, 1, 9, tzinfo=timezone.utc),
        ventana_fin=datetime(2026, 10, 1, 11, tzinfo=timezone.utc),
        prioridad="ESTANDAR",
        tipo_producto="Libre",
    )


def test_client_lookup_and_sanitized_failure():
    session = Mock()
    identifier = uuid4()
    repository = ClienteRepository(session)
    session.scalar.return_value = True
    assert repository.exists(identifier)
    session.scalar.return_value = False
    assert not repository.exists(identifier)
    session.scalar.side_effect = SQLAlchemyError("private")
    with pytest.raises(ClienteStorageError, match="Client storage unavailable"):
        repository.exists(identifier)


def test_order_add_uses_spatial_expression_and_flush():
    session = Mock()
    row = order()
    PedidoRepository(session).add(row, -11.9, -76.9)
    assert "ST_MakePoint" in str(row.ubicacion)
    compiled = row.ubicacion.compile()
    assert -76.9 in compiled.params.values()
    assert -11.9 in compiled.params.values()
    session.add.assert_called_once_with(row)
    session.flush.assert_called_once()
    session.commit.assert_not_called()


def test_reference_only_leaves_location_null():
    session = Mock()
    row = order()
    row.referencia = "Frente al parque"
    PedidoRepository(session).add(row, None, None)
    assert row.ubicacion is None


def test_coordinates_projection_and_failure():
    session = Mock()
    session.execute.return_value.one.return_value = (-11.9, -76.9)
    repository = PedidoRepository(session)
    assert repository.coordinates(uuid4()) == (-11.9, -76.9)
    assert "ST_Y" in str(session.execute.call_args.args[0])
    assert "ST_X" in str(session.execute.call_args.args[0])
    session.execute.side_effect = SQLAlchemyError("private")
    with pytest.raises(PedidoStorageError, match="Order storage unavailable"):
        repository.coordinates(uuid4())


class _Diag:
    constraint_name = "fk_pedido_cliente_id_cliente"


class _ForeignKeyFailure(Exception):
    diag = _Diag()


@pytest.mark.parametrize(
    "error,expected",
    [
        (
            IntegrityError("sql", {}, _ForeignKeyFailure("private")),
            PedidoClienteMissing,
        ),
        (IntegrityError("sql", {}, Exception("private")), PedidoStorageError),
        (SQLAlchemyError("private"), PedidoStorageError),
    ],
)
def test_order_storage_failures_are_sanitized(error, expected):
    session = Mock()
    session.flush.side_effect = error
    with pytest.raises(expected) as raised:
        PedidoRepository(session).add(order(), None, None)
    assert "private" not in str(raised.value)
