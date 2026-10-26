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


@pytest.mark.parametrize(
    "identity,motivo",
    [
        (Identidad(uuid4(), "INVALID", "ACTIVO"), Motivo.ROL_INVALIDO),
        (None, Motivo.IDENTIDAD_INVALIDA),
        ({}, Motivo.IDENTIDAD_INVALIDA),
        (Identidad("invalid", Rol.OPERADOR, "ACTIVO"), Motivo.IDENTIDAD_INVALIDA),
    ],
)
def test_invalid_identity_has_no_audit_actor(identity, motivo):
    sink = Mock()
    with pytest.raises(AuthorizationDenied):
        AutorizacionService(sink).autorizar(identity, Permiso.USUARIOS_CREAR)
    sink.registrar.assert_called_once()
    record = sink.registrar.call_args.args[0]
    assert record.usuario_id is None
    assert record.evento is Evento.DENEGADA
    assert record.detalle.motivo is motivo


@pytest.mark.parametrize(
    "estado,motivo",
    [
        ("ACTIVO", Motivo.SIN_PERMISO),
        ("BLOQUEADO", Motivo.ESTADO_NO_ACTIVO),
        ("INACTIVO", Motivo.ESTADO_NO_ACTIVO),
    ],
)
def test_known_denied_actor_is_preserved(estado, motivo):
    sink = Mock()
    identity = Identidad(uuid4(), Rol.OPERADOR, estado)
    with pytest.raises(AuthorizationDenied):
        AutorizacionService(sink).autorizar(identity, Permiso.USUARIOS_CREAR)
    record = sink.registrar.call_args.args[0]
    assert record.usuario_id == identity.usuario_id
    assert record.detalle.motivo is motivo


def test_ecl73_restriccion_de_roles_del_endpoint_sin_cambiar_la_matriz():
    """I08: an endpoint may admit fewer roles than the matrix; denial is audited."""
    from unittest.mock import Mock
    from uuid import uuid4

    from app.core.rbac import MATRIZ_RBAC, Identidad, Motivo, Permiso, Rol
    from app.repositories.auditoria import Evento
    from app.services.autorizacion import AuthorizationDenied, AutorizacionService

    assert Permiso.INCIDENCIAS_CREAR in MATRIZ_RBAC[Rol.OPERADOR]
    audit = Mock()
    service = AutorizacionService(audit)
    operator = Identidad(uuid4(), Rol.OPERADOR, "ACTIVO")
    service.autorizar(operator, Permiso.INCIDENCIAS_CREAR)  # Matrix unchanged.
    with pytest.raises(AuthorizationDenied):
        service.autorizar(
            operator, Permiso.INCIDENCIAS_CREAR, roles=frozenset({Rol.CONDUCTOR})
        )
    allowed, denied = [call.args[0] for call in audit.registrar.mock_calls]
    assert allowed.evento is Evento.PERMITIDA
    assert denied.evento is Evento.DENEGADA
    assert denied.detalle.motivo is Motivo.SIN_PERMISO
    assert denied.usuario_id == operator.usuario_id
