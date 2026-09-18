from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.rbac import Motivo, Permiso
from app.models.auditoria import Auditoria
from app.repositories.auditoria import (
    AuditoriaRepository,
    AuditStorageError,
    Detalle,
    Evento,
    Registro,
)
from app.services.auditoria import AuditoriaService


@pytest.fixture
def record():
    return Registro(
        usuario_id=uuid4(),
        evento=Evento.PERMITIDA,
        detalle=Detalle(permiso=Permiso.PEDIDOS_CREAR, motivo=Motivo.PERMITIDO),
    )


def test_insert_has_only_structured_data_and_no_commit(record):
    session = MagicMock()
    AuditoriaRepository(session).insert(record)
    row = session.add.call_args.args[0]
    assert row.entidad == "pedidos"
    assert row.detalle == {"permiso": "pedidos.crear", "motivo": "PERMITIDO"}
    session.flush.assert_called_once()
    session.commit.assert_not_called()
    assert repr(row) == "<Auditoria>"
    assert set(Auditoria.__table__.columns.keys()) == {
        "auditoria_id",
        "usuario_id",
        "entidad",
        "entidad_id",
        "accion",
        "creado_en",
        "detalle",
    }


def test_unknown_permission_is_not_persisted_as_text():
    record = Registro(
        usuario_id=None,
        evento=Evento.DENEGADA,
        detalle=Detalle(permiso=None, motivo=Motivo.PERMISO_INVALIDO),
    )
    session = MagicMock()
    AuditoriaRepository(session).insert(record)
    assert session.add.call_args.args[0].entidad == "autorizacion"


@pytest.mark.parametrize(
    "fields",
    [
        {"password": "secret"},
        {"motivo": "secret"},
        {"permiso": "secret"},
    ],
)
def test_detail_rejects_arbitrary_payload_and_hides_values(fields):
    values = {"permiso": Permiso.PEDIDOS_CREAR, "motivo": Motivo.PERMITIDO, **fields}
    with pytest.raises(ValidationError) as error:
        Detalle(**values)
    assert "secret" not in str(error.value)


def test_consistency_and_frozen_record(record):
    for changes in (
        {"evento": Evento.DENEGADA},
        {"usuario_id": None},
        {"secret": "secret"},
    ):
        with pytest.raises(ValidationError):
            Registro.model_validate({**record.model_dump(), **changes})
    with pytest.raises(ValidationError):
        record.usuario_id = uuid4()


def test_nested_detail_is_revalidated_before_storage(record):
    session = MagicMock()
    forged = record.model_copy(
        update={
            "detalle": Detalle.model_construct(
                permiso="secret", motivo=Motivo.PERMITIDO
            )
        }
    )
    with pytest.raises(ValidationError) as error:
        AuditoriaRepository(session).insert(forged)
    assert "secret" not in str(error.value)
    session.add.assert_not_called()


def test_repository_failure_sanitized(record, caplog):
    session = MagicMock()
    session.flush.side_effect = SQLAlchemyError("secret driver payload")
    with pytest.raises(AuditStorageError, match="^Audit storage unavailable$"):
        AuditoriaRepository(session).insert(record)
    assert "secret" not in caplog.text


@pytest.mark.parametrize("failure", [None, "flush", "commit", "connect"])
def test_service_transaction_and_errors(record, failure, caplog):
    factory = MagicMock()
    transaction = factory.begin.return_value
    if failure == "flush":
        transaction.__enter__.return_value.flush.side_effect = SQLAlchemyError("secret")
    if failure == "commit":
        transaction.__exit__.side_effect = SQLAlchemyError("secret")
    if failure == "connect":
        factory.begin.side_effect = SQLAlchemyError("secret")
    if failure:
        with pytest.raises(AuditStorageError, match="^Audit storage unavailable$"):
            AuditoriaService(factory).registrar(record)
    else:
        AuditoriaService(factory).registrar(record)
        transaction.__exit__.assert_called_once_with(None, None, None)
    assert "secret" not in caplog.text
