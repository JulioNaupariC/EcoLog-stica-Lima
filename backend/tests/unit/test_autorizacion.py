from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.rbac import Identidad, Motivo, Permiso, Rol
from app.repositories.auditoria import AuditStorageError, Evento
from app.services.autorizacion import AuthorizationDenied, AutorizacionService


def test_allowed_records_before_return():
    sink = Mock()
    identity = Identidad(uuid4(), Rol.OPERADOR, "ACTIVO")
    decision = AutorizacionService(sink).autorizar(identity, Permiso.PEDIDOS_CREAR)
    assert decision.permitido
    record = sink.registrar.call_args.args[0]
    assert record.evento is Evento.PERMITIDA
    assert record.usuario_id == identity.usuario_id
    assert record.detalle.motivo is Motivo.PERMITIDO


@pytest.mark.parametrize(
    "identity", [None, Identidad(uuid4(), "secret-invalid-role", "ACTIVO")]
)
def test_denial_is_audited_without_raw_input(identity):
    sink = Mock()
    with pytest.raises(AuthorizationDenied, match="^Access denied$"):
        AutorizacionService(sink).autorizar(identity, "secret-invalid-permission")
    record = sink.registrar.call_args.args[0]
    assert record.evento is Evento.DENEGADA
    assert record.detalle.permiso is None
    assert "secret" not in record.model_dump_json()


def test_storage_failure_never_grants_access():
    sink = Mock()
    sink.registrar.side_effect = AuditStorageError("Audit storage unavailable")
    identity = Identidad(uuid4(), Rol.OPERADOR, "ACTIVO")
    with pytest.raises(AuditStorageError):
        AutorizacionService(sink).autorizar(identity, Permiso.PEDIDOS_CREAR)
