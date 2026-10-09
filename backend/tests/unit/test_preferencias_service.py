from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models.cliente import Cliente
from app.repositories.preferencias import PreferenciasRepository
from app.schemas.preferencias import PreferenciasPatch
from app.services import preferencias as module
from app.services.preferencias import (
    PreferenciasNotFound,
    PreferenciasService,
    PreferenciasUnavailable,
)


def setup(monkeypatch):
    factory = MagicMock()
    repo = Mock()
    row = Cliente(
        cliente_id=uuid4(),
        nombre="No exponer",
        horario_preferido="Mañana",
        referencia="Referencia inicial",
        restriccion_acceso="Acceso",
    )
    repo.get.return_value = row
    monkeypatch.setattr(module, "PreferenciasRepository", Mock(return_value=repo))
    return PreferenciasService(factory), repo, row, factory


def test_get_projection_has_only_preferences(monkeypatch):
    service, repo, row, _ = setup(monkeypatch)
    result = service.get(row.cliente_id)
    assert set(result.model_dump()) == {
        "cliente_id",
        "horario_preferido",
        "referencia",
        "restriccion_acceso",
    }
    repo.get.assert_called_once_with(row.cliente_id)
    assert result.referencia == row.referencia


def test_update_locks_and_commits_only_supplied_fields(monkeypatch):
    service, repo, row, factory = setup(monkeypatch)
    result = service.update(row.cliente_id, PreferenciasPatch(referencia=None))
    assert result.referencia is None
    assert (
        result.horario_preferido == "Mañana" and result.restriccion_acceso == "Acceso"
    )
    repo.get.assert_called_once_with(row.cliente_id, lock=True)
    repo.flush.assert_called_once()
    factory.begin.return_value.__exit__.assert_called_once_with(None, None, None)


@pytest.mark.parametrize("action", ["get", "update"])
def test_missing_or_storage_failure_is_safe(monkeypatch, action):
    service, repo, row, _ = setup(monkeypatch)
    args = (
        (row.cliente_id,)
        if action == "get"
        else (row.cliente_id, PreferenciasPatch(referencia="Nuevo"))
    )
    repo.get.return_value = None
    with pytest.raises(PreferenciasNotFound):
        getattr(service, action)(*args)
    repo.get.side_effect = SQLAlchemyError("private connection")
    with pytest.raises(PreferenciasUnavailable, match="^Preferences unavailable$"):
        getattr(service, action)(*args)


def test_commit_failure_cannot_return_success(monkeypatch):
    service, _, row, factory = setup(monkeypatch)
    factory.begin.return_value.__exit__.side_effect = SQLAlchemyError("private")
    with pytest.raises(PreferenciasUnavailable):
        service.update(row.cliente_id, PreferenciasPatch(referencia="Nuevo"))


def test_repository_targets_one_id_and_locks():
    session = Mock()
    repo = PreferenciasRepository(session)
    identifier = uuid4()
    repo.get(identifier)
    stmt = session.scalar.call_args.args[0]
    assert stmt.compile().params["cliente_id_1"] == identifier
    assert "FOR UPDATE" not in str(stmt)
    repo.get(identifier, lock=True)
    assert "FOR UPDATE" in str(session.scalar.call_args.args[0])
    repo.flush()
    session.flush.assert_called_once()
