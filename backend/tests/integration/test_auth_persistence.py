from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from argon2 import PasswordHasher
from sqlalchemy import delete, func, select

from alembic import command
from app.core.config import Settings
from app.core.passwords import PasswordOperationError, needs_rehash, verify_password
from app.core.rbac import Rol
from app.db.session import build_audit_engine, session_factory
from app.models import Auditoria, Sesion, Usuario
from app.repositories.auditoria import AuditStorageError, Evento
from app.repositories.usuarios import UsuarioRepository
from app.services.auditoria import AuditoriaService
from app.services.autenticacion import (
    AutenticacionService,
    AuthenticationUnavailable,
    InvalidCredentials,
    InvalidSession,
)
from app.services.credenciales import CredentialService

pytestmark = pytest.mark.integration


@pytest.fixture
def auth_database(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    audit_engine = build_audit_engine(Settings())
    try:
        business_factory = session_factory(engine)
        audit_factory = session_factory(audit_engine)
        yield (
            business_factory,
            AutenticacionService(
                business_factory, AuditoriaService(audit_factory), ttl_minutes=60
            ),
        )
    finally:
        # Explicit treatment of disposable test evidence before fixture downgrade.
        with business_factory.begin() as session:
            session.execute(
                delete(Auditoria).where(
                    Auditoria.accion.in_(
                        (
                            Evento.LOGIN_EXITOSO.value,
                            Evento.LOGIN_FALLIDO.value,
                            Evento.CUENTA_BLOQUEADA.value,
                            Evento.SESION_CERRADA.value,
                        )
                    )
                )
            )
        audit_engine.dispose()


def create_user(factory, email="user@example.test", password="correct", **values):
    with factory.begin() as session:
        identity = CredentialService(UsuarioRepository(session)).create(
            email, password, values.pop("rol", "OPERADOR")
        )
        for key, value in values.items():
            setattr(session.get(Usuario, identity.usuario_id), key, value)
        return identity.usuario_id


def test_login_session_identity_logout_and_audit(auth_database):
    factory, service = auth_database
    identifier = create_user(factory)
    result = service.login("user@example.test", "correct")
    assert result.identidad.usuario_id == identifier
    assert result.identidad.rol is Rol.OPERADOR
    with factory() as session:
        stored = session.scalar(select(Sesion))
        assert stored.token_hash != result.token
        assert result.token not in repr(stored)
        assert len(stored.token_hash) == 64
        assert stored.creado_en.utcoffset() is not None
        assert stored.expira_en.utcoffset() is not None
    assert service.resolve(result.token).identidad.usuario_id == identifier
    with factory.begin() as session:
        user = session.get(Usuario, identifier)
        user.rol = "AUDITOR"
    assert service.resolve(result.token).identidad.rol is Rol.AUDITOR
    with factory.begin() as session:
        session.get(Usuario, identifier).estado = "INACTIVO"
    with pytest.raises(InvalidSession):
        service.resolve(result.token)
    with factory.begin() as session:
        session.get(Usuario, identifier).estado = "ACTIVO"
    service.logout(service.resolve(result.token))
    with pytest.raises(InvalidSession):
        service.resolve(result.token)
    with factory() as session:
        stored = session.scalar(select(Sesion))
        assert stored.revocada_en.utcoffset() is not None
        actions = set(session.scalars(select(Auditoria.accion)))
        assert {Evento.LOGIN_EXITOSO.value, Evento.SESION_CERRADA.value} <= actions
        assert result.token not in "".join(
            str(row.detalle) for row in session.scalars(select(Auditoria))
        )


def test_failures_lock_for_fifteen_minutes_and_expire(auth_database):
    factory, service = auth_database
    identifier = create_user(factory)
    now = datetime.now(timezone.utc)
    for attempt in range(1, 4):
        with pytest.raises(InvalidCredentials):
            service.login("user@example.test", "wrong", now=now)
        with factory() as session:
            user = session.get(Usuario, identifier)
            assert user.intentos_fallidos == attempt
            assert user.estado == "ACTIVO"
    with factory() as session:
        user = session.get(Usuario, identifier)
        assert user.bloqueado_hasta == now + timedelta(minutes=15)
    with pytest.raises(InvalidCredentials):
        service.login("user@example.test", "correct", now=now + timedelta(minutes=1))
    with factory() as session:
        user = session.get(Usuario, identifier)
        assert user.intentos_fallidos == 3
        assert user.bloqueado_hasta == now + timedelta(minutes=15)
    result = service.login(
        "user@example.test", "correct", now=now + timedelta(minutes=15)
    )
    assert result.identidad.usuario_id == identifier
    with factory() as session:
        user = session.get(Usuario, identifier)
        assert user.intentos_fallidos == 0 and user.bloqueado_hasta is None
        actions = list(session.scalars(select(Auditoria.accion)))
        assert Evento.CUENTA_BLOQUEADA.value in actions
        failed = session.scalars(
            select(Auditoria).where(Auditoria.accion == Evento.LOGIN_FALLIDO.value)
        ).all()
        assert failed and all(row.usuario_id is None for row in failed)


@pytest.mark.parametrize("state", ["INACTIVO", "BLOQUEADO"])
def test_structural_state_is_never_reactivated(auth_database, state):
    factory, service = auth_database
    identifier = create_user(factory, estado=state)
    with pytest.raises(InvalidCredentials):
        service.login("user@example.test", "correct")
    with factory() as session:
        assert session.get(Usuario, identifier).estado == state


def test_unknown_user_matches_invalid_password_contract(auth_database):
    factory, service = auth_database
    create_user(factory)
    for email in ("missing@example.test", "user@example.test"):
        with pytest.raises(InvalidCredentials, match="^Invalid credentials$"):
            service.login(email, "wrong")


def test_unknown_user_runs_stable_argon_verification_without_creating_account(
    auth_database, monkeypatch
):
    factory, service = auth_database
    from app.services import autenticacion as authentication_module

    observed_hashes = []
    real_verify = authentication_module.verify_password

    def observe_verification(password, password_hash):
        observed_hashes.append(password_hash)
        return real_verify(password, password_hash)

    monkeypatch.setattr(authentication_module, "verify_password", observe_verification)
    for _ in range(2):
        with pytest.raises(InvalidCredentials):
            service.login("missing@example.test", "wrong")

    assert len(observed_hashes) == 2
    assert len(set(observed_hashes)) == 1
    assert observed_hashes[0].startswith("$argon2id$")
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Usuario)) == 0
        assert session.scalar(select(func.count()).select_from(Sesion)) == 0


def test_existing_user_password_operation_failure_is_operational(
    auth_database, monkeypatch
):
    factory, service = auth_database
    identifier = create_user(factory)

    def fail_password_operation(*args, **kwargs):
        raise PasswordOperationError("private existing-user argon details")

    monkeypatch.setattr("app.core.passwords.verify_password", fail_password_operation)
    with pytest.raises(AuthenticationUnavailable, match="^Authentication unavailable$"):
        service.login("user@example.test", "correct")

    with factory() as session:
        user = session.get(Usuario, identifier)
        assert user.intentos_fallidos == 0
        assert user.bloqueado_hasta is None
        assert session.scalar(select(func.count()).select_from(Sesion)) == 0


def test_unknown_user_dummy_password_failure_is_operational(auth_database, monkeypatch):
    factory, service = auth_database
    email = "missing-private@example.test"

    def fail_dummy_verification(*args, **kwargs):
        raise PasswordOperationError("private dummy argon details")

    monkeypatch.setattr(
        "app.services.autenticacion.verify_password", fail_dummy_verification
    )
    with pytest.raises(AuthenticationUnavailable, match="^Authentication unavailable$"):
        service.login(email, "correct")

    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Usuario)) == 0
        assert session.scalar(select(func.count()).select_from(Sesion)) == 0
        audit_details = "".join(
            str(row.detalle) for row in session.scalars(select(Auditoria))
        )
        assert email not in audit_details


def test_concurrent_failures_do_not_lose_increments(auth_database):
    factory, service = auth_database
    identifier = create_user(factory)
    with pytest.raises(InvalidCredentials):
        service.login("user@example.test", "wrong")

    def fail_login():
        with pytest.raises(InvalidCredentials):
            service.login("user@example.test", "wrong")

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda _: fail_login(), range(2)))
    with factory() as session:
        user = session.get(Usuario, identifier)
        assert user.intentos_fallidos == 3
        assert user.bloqueado_hasta is not None


def test_rehash_expiration_and_current_account_state(auth_database):
    factory, service = auth_database
    old_hash = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1).hash("p")
    with factory.begin() as session:
        user = Usuario(email="old@example.test", password_hash=old_hash, rol="OPERADOR")
        session.add(user)
        session.flush()
        identifier = user.usuario_id
    now = datetime.now(timezone.utc)
    result = service.login("old@example.test", "p", now=now)
    with factory() as session:
        stored = session.get(Usuario, identifier).password_hash
        assert verify_password("p", stored) and not needs_rehash(stored)
    with pytest.raises(InvalidSession):
        service.resolve(result.token, now=result.expira_en)
    with factory.begin() as session:
        session.get(Usuario, identifier).bloqueado_hasta = now + timedelta(minutes=5)
    with pytest.raises(InvalidSession):
        service.resolve(
            result.token, now=now + timedelta(minutes=5) - timedelta(microseconds=1)
        )
    assert (
        service.resolve(
            result.token, now=now + timedelta(minutes=5)
        ).identidad.usuario_id
        == identifier
    )


def test_failed_success_audit_compensates_session(auth_database, monkeypatch):
    factory, _ = auth_database
    create_user(factory)

    class FailedAudit:
        def registrar(self, registro):
            raise AuditStorageError("Audit storage unavailable")

    service = AutenticacionService(factory, FailedAudit(), ttl_minutes=60)
    known_token = "compensated-session-token"
    monkeypatch.setattr(
        "app.services.autenticacion.generate_session_token", lambda: known_token
    )
    with pytest.raises(AuthenticationUnavailable):
        service.login("user@example.test", "correct")
    with factory() as session:
        stored = session.scalar(select(Sesion))
        assert stored is not None and stored.revocada_en is not None
    with pytest.raises(InvalidSession):
        service.resolve(known_token)
