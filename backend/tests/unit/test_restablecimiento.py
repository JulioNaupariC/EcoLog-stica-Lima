"""ECL-77 password reset and change service, with persistence replaced by mocks."""

import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core import passwords
from app.core.rbac import Identidad, Motivo, Permiso, Rol
from app.repositories.auditoria import (
    AuditoriaRepository,
    Detalle,
    DetalleAcceso,
    DetalleContrasena,
    Evento,
    Registro,
    ResultadoAcceso,
)
from app.repositories.usuarios import LoginAccount, UserSummary
from app.services import restablecimiento as module
from app.services.autenticacion import (
    AuthenticatedSession,
    register_failed_attempt,
    temporary_password_expired,
)
from app.services.autorizacion import AuthorizationDenied, AutorizacionService
from app.services.restablecimiento import (
    AutoRestablecimiento,
    ContrasenaActualInvalida,
    ContrasenaNuevaInvalida,
    RestablecimientoService,
    RestablecimientoUnavailable,
    UsuarioInactivo,
    UsuarioNoEncontrado,
)

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
AMBIGUOUS = set("0Oo1lI")


def account(**changes):
    values = {
        "usuario_id": uuid4(),
        "rol": "OPERADOR",
        "estado": "ACTIVO",
        "intentos_fallidos": 0,
        "bloqueado_hasta": None,
        "debe_cambiar_contrasena": False,
        "contrasena_temporal_expira_en": None,
    }
    values.update(changes)
    return LoginAccount(**values)


@pytest.fixture
def fakes(monkeypatch):
    """Replace every repository the service builds; capture what it writes."""
    users = Mock()
    sessions = Mock()
    sessions.revoke_all_for_user.return_value = 2
    credentials = Mock()
    credentials.verify.return_value = True
    audit_rows = []
    audit_repository = Mock()
    audit_repository.insert.side_effect = audit_rows.append
    monkeypatch.setattr(module, "UsuarioRepository", lambda session: users)
    monkeypatch.setattr(module, "SesionRepository", lambda session: sessions)
    monkeypatch.setattr(module, "CredentialService", lambda repository: credentials)
    monkeypatch.setattr(module, "AuditoriaRepository", lambda session: audit_repository)
    factory = MagicMock()
    authorization_audit = Mock()
    access_audit = Mock()
    service = RestablecimientoService(
        factory, AutorizacionService(authorization_audit), access_audit
    )
    return SimpleNamespace(
        service=service,
        factory=factory,
        users=users,
        sessions=sessions,
        credentials=credentials,
        audit_rows=audit_rows,
        authorization_audit=authorization_audit,
        access_audit=access_audit,
    )


def admin():
    return Identidad(uuid4(), Rol.ADMINISTRADOR, "ACTIVO")


def test_temporary_password_is_long_random_and_unambiguous():
    generated = {passwords.generate_temporary_password() for _ in range(200)}
    assert len(generated) == 200
    for value in generated:
        assert len(value) == 16
        assert set(value) <= set(passwords.TEMPORARY_PASSWORD_ALPHABET)
        assert not set(value) & AMBIGUOUS
    assert not AMBIGUOUS & set(passwords.TEMPORARY_PASSWORD_ALPHABET)


@pytest.mark.parametrize(
    "flag,expires,expired",
    [
        (False, None, False),
        (True, NOW + timedelta(seconds=1), False),
        (True, NOW, True),
        (True, None, True),
    ],
)
def test_temporary_password_expiration_rule(flag, expires, expired):
    assert temporary_password_expired(flag, expires, NOW) is expired


@pytest.mark.parametrize("attempts,blocked", [(0, False), (1, False), (2, True)])
def test_failed_attempt_counter_matches_login(attempts, blocked):
    users = Mock()
    user_id = uuid4()
    assert register_failed_attempt(users, user_id, attempts, NOW) is blocked
    users.set_login_state.assert_called_once_with(
        user_id,
        intentos_fallidos=attempts + 1,
        bloqueado_hasta=NOW + timedelta(minutes=15) if blocked else None,
    )


@pytest.mark.parametrize(
    "evento", [Evento.CONTRASENA_RESTABLECIDA, Evento.CONTRASENA_CAMBIADA]
)
def test_password_audit_requires_actor_entity_and_its_own_detail(evento):
    detail = DetalleContrasena(sesiones_revocadas=1)
    assert Registro(
        usuario_id=uuid4(), entidad_id=uuid4(), evento=evento, detalle=detail
    )
    for usuario_id, entidad_id in ((None, uuid4()), (uuid4(), None)):
        with pytest.raises(ValueError):
            Registro(
                usuario_id=usuario_id,
                entidad_id=entidad_id,
                evento=evento,
                detalle=detail,
            )
    with pytest.raises(ValueError):
        Registro(
            usuario_id=uuid4(),
            entidad_id=uuid4(),
            evento=evento,
            detalle=DetalleAcceso(resultado=ResultadoAcceso.EXITOSO),
        )
    with pytest.raises(ValueError):
        Registro(
            usuario_id=uuid4(),
            entidad_id=uuid4(),
            evento=Evento.LOGIN_EXITOSO,
            detalle=detail,
        )
    with pytest.raises(ValueError):
        DetalleContrasena(sesiones_revocadas=-1)


def test_password_audit_is_stored_against_the_user_entity():
    session = Mock()
    AuditoriaRepository(session).insert(
        Registro(
            usuario_id=uuid4(),
            entidad_id=uuid4(),
            evento=Evento.CONTRASENA_RESTABLECIDA,
            detalle=DetalleContrasena(sesiones_revocadas=3),
        )
    )
    row = session.add.call_args.args[0]
    assert row.entidad == "usuario"
    assert row.accion == "CONTRASENA_RESTABLECIDA"
    assert row.detalle == {"sesiones_revocadas": 3}


def test_golden_reset_hashes_revokes_and_audits_once(fakes, caplog):
    actor = admin()
    target = account()
    fakes.users.find_by_id_for_update.return_value = target
    caplog.set_level(logging.DEBUG)

    result = fakes.service.restablecer(actor, target.usuario_id, now=NOW)

    assert len(result.contrasena_temporal) == 16
    assert result.expira_en == NOW + timedelta(hours=24)
    assert result.contrasena_temporal not in repr(result)
    fakes.credentials.set_temporary.assert_called_once_with(
        target.usuario_id, result.contrasena_temporal, NOW + timedelta(hours=24)
    )
    fakes.sessions.revoke_all_for_user.assert_called_once_with(target.usuario_id, NOW)
    [row] = fakes.audit_rows
    assert row.evento is Evento.CONTRASENA_RESTABLECIDA
    assert row.usuario_id == actor.usuario_id
    assert row.entidad_id == target.usuario_id
    assert row.detalle == DetalleContrasena(sesiones_revocadas=2)
    assert result.contrasena_temporal not in str(row.model_dump())
    [decision] = [c.args[0] for c in fakes.authorization_audit.registrar.mock_calls]
    assert decision.evento is Evento.PERMITIDA
    assert decision.detalle == Detalle(
        permiso=Permiso.USUARIOS_ACTUALIZAR, motivo=Motivo.PERMITIDO
    )
    assert decision.entidad_id == target.usuario_id
    assert result.contrasena_temporal not in caplog.text


@pytest.mark.parametrize(
    "role", [Rol.OPERADOR, Rol.CONDUCTOR, Rol.ANALISTA, Rol.AUDITOR]
)
def test_non_admin_reset_is_denied_audited_and_touches_nothing(fakes, role):
    with pytest.raises(AuthorizationDenied):
        fakes.service.restablecer(Identidad(uuid4(), role, "ACTIVO"), uuid4())
    [decision] = [c.args[0] for c in fakes.authorization_audit.registrar.mock_calls]
    assert decision.evento is Evento.DENEGADA
    fakes.factory.begin.assert_not_called()


def test_admin_cannot_reset_own_password(fakes):
    actor = admin()
    with pytest.raises(AutoRestablecimiento):
        fakes.service.restablecer(actor, actor.usuario_id)
    fakes.factory.begin.assert_not_called()


def test_reset_rejects_missing_and_inactive_users(fakes):
    fakes.users.find_by_id_for_update.return_value = None
    with pytest.raises(UsuarioNoEncontrado):
        fakes.service.restablecer(admin(), uuid4())
    fakes.users.find_by_id_for_update.return_value = account(estado="INACTIVO")
    with pytest.raises(UsuarioInactivo):
        fakes.service.restablecer(admin(), uuid4())
    fakes.credentials.set_temporary.assert_not_called()
    assert fakes.audit_rows == []


def test_locked_user_can_be_reset(fakes):
    fakes.users.find_by_id_for_update.return_value = account(
        intentos_fallidos=3, bloqueado_hasta=NOW + timedelta(minutes=5)
    )
    assert fakes.service.restablecer(admin(), uuid4(), now=NOW)
    fakes.credentials.set_temporary.assert_called_once()


@pytest.mark.parametrize(
    "failure", [SQLAlchemyError("private sql"), passwords.PasswordOperationError()]
)
def test_reset_storage_failures_are_sanitized(fakes, failure):
    fakes.users.find_by_id_for_update.return_value = account()
    fakes.credentials.set_temporary.side_effect = failure
    with pytest.raises(RestablecimientoUnavailable) as error:
        fakes.service.restablecer(admin(), uuid4())
    assert "private" not in str(error.value)


def own_session(user=None):
    user = user or account()
    return AuthenticatedSession(
        uuid4(), Identidad(user.usuario_id, Rol.OPERADOR, "ACTIVO"), True
    )


@pytest.mark.parametrize(
    "current,new",
    [("temporary-pass-16", "short-11ch"), ("same-password-1", "same-password-1")],
)
def test_change_rejects_weak_or_unchanged_password_before_storage(fakes, current, new):
    with pytest.raises(ContrasenaNuevaInvalida) as error:
        fakes.service.cambiar(own_session(), current, new)
    assert new not in str(error.value)
    fakes.factory.begin.assert_not_called()


def test_happy_change_replaces_hash_keeps_current_session_and_audits(fakes):
    user = account(
        debe_cambiar_contrasena=True,
        contrasena_temporal_expira_en=NOW + timedelta(hours=1),
    )
    fakes.users.find_by_id_for_update.return_value = user
    current = own_session(user)

    fakes.service.cambiar(current, "temporary-pass-16", "definitive-pass-1", now=NOW)

    fakes.credentials.verify.assert_called_once_with(
        user.usuario_id, "temporary-pass-16"
    )
    fakes.credentials.replace.assert_called_once_with(
        user.usuario_id, "definitive-pass-1"
    )
    fakes.sessions.revoke_all_for_user.assert_called_once_with(
        user.usuario_id, NOW, except_sesion_id=current.sesion_id
    )
    [row] = fakes.audit_rows
    assert row.evento is Evento.CONTRASENA_CAMBIADA
    assert row.usuario_id == row.entidad_id == user.usuario_id
    fakes.access_audit.registrar.assert_not_called()


@pytest.mark.parametrize(
    "user,verified",
    [
        (account(), False),
        (account(intentos_fallidos=2), False),
        (
            account(
                debe_cambiar_contrasena=True,
                contrasena_temporal_expira_en=NOW - timedelta(seconds=1),
            ),
            True,
        ),
    ],
)
def test_wrong_or_expired_current_password_counts_like_login(fakes, user, verified):
    fakes.users.find_by_id_for_update.return_value = user
    fakes.credentials.verify.return_value = verified

    with pytest.raises(ContrasenaActualInvalida):
        fakes.service.cambiar(
            own_session(user), "wrong-or-old-pass", "definitive-pass-1", now=NOW
        )

    blocked = user.intentos_fallidos == 2
    fakes.users.set_login_state.assert_called_once_with(
        user.usuario_id,
        intentos_fallidos=user.intentos_fallidos + 1,
        bloqueado_hasta=NOW + timedelta(minutes=15) if blocked else None,
    )
    fakes.credentials.replace.assert_not_called()
    events = [c.args[0].evento for c in fakes.access_audit.registrar.mock_calls]
    expected = [Evento.LOGIN_FALLIDO] + ([Evento.CUENTA_BLOQUEADA] if blocked else [])
    assert events == expected
    assert fakes.audit_rows == []


def test_change_for_vanished_account_is_invalid(fakes):
    fakes.users.find_by_id_for_update.return_value = None
    with pytest.raises(ContrasenaActualInvalida):
        fakes.service.cambiar(own_session(), "temporary-pass-16", "definitive-pass-1")


def test_change_storage_failure_is_sanitized(fakes):
    fakes.users.find_by_id_for_update.side_effect = SQLAlchemyError("private sql")
    with pytest.raises(RestablecimientoUnavailable):
        fakes.service.cambiar(own_session(), "temporary-pass-16", "definitive-pass-1")


def test_list_returns_page_and_sanitizes_failures(fakes):
    summary = UserSummary(uuid4(), "a@example.test", "OPERADOR", "ACTIVO", True)
    fakes.users.list_page.return_value = ([summary], 41)
    page = fakes.service.listar(3, 20)
    assert (page.items, page.page, page.page_size, page.total) == (
        [summary],
        3,
        20,
        41,
    )
    fakes.users.list_page.assert_called_once_with(3, 20)
    fakes.users.list_page.side_effect = SQLAlchemyError("private sql")
    with pytest.raises(RestablecimientoUnavailable):
        fakes.service.listar(1, 20)
