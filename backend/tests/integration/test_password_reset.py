"""ECL-77 / US-013 over PostgreSQL: reset, mandatory change, audit and migration.

The real dependency chain is kept: login, opaque cookie, persisted session,
RBAC, Argon2id and audit. Passwords here are synthetic and test-only.
"""

import logging
from datetime import datetime, timedelta, timezone

import pytest
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.core.config import Settings
from app.db.session import session_factory
from app.main import create_app
from app.models import Auditoria, Sesion, Usuario
from app.repositories.auditoria import Evento
from app.repositories.usuarios import UsuarioRepository
from app.services.credenciales import CredentialService

pytestmark = pytest.mark.integration

ADMIN = "admin-reset@example.test"
OPERATOR = "operador-reset@example.test"
ORIGINAL = "original-password-1"
DEFINITIVE = "definitive-password-1"


@pytest.fixture
def reset_database(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = session_factory(engine)
    try:
        yield factory, config.attributes["database_url"]
    finally:
        # Disposable *_test evidence; lets the protected 0012 downgrade run.
        with factory.begin() as session:
            session.execute(delete(Auditoria))


def create_user(factory, email, role):
    with factory.begin() as session:
        return (
            CredentialService(UsuarioRepository(session))
            .create(email, ORIGINAL, role)
            .usuario_id
        )


def client_for(database_url):
    return TestClient(create_app(Settings(app_env="test", database_url=database_url)))


def login(client, email, password):
    return client.post("/login", json={"email": email, "password": password})


def audit_rows(factory, event):
    with factory() as session:
        return list(
            session.scalars(select(Auditoria).where(Auditoria.accion == event.value))
        )


def reset(admin_client, user_id):
    response = admin_client.post(f"/usuarios/{user_id}/restablecer-contrasena")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    return response.json()["contrasena_temporal"]


def test_golden_reset_revokes_sessions_and_audits(reset_database):
    factory, url = reset_database
    admin_id = create_user(factory, ADMIN, "ADMINISTRADOR")
    user_id = create_user(factory, OPERATOR, "OPERADOR")
    with client_for(url) as user_client, client_for(url) as admin_client:
        assert login(user_client, OPERATOR, ORIGINAL).status_code == 200
        assert user_client.get("/vehiculos").status_code == 200
        assert login(admin_client, ADMIN, ORIGINAL).status_code == 200

        listing = admin_client.get("/usuarios")
        assert listing.status_code == 200
        assert "password" not in listing.text and "argon2" not in listing.text
        temporary = reset(admin_client, user_id)

        assert len(temporary) == 16
        # The user's previous session is revoked by the reset.
        assert user_client.get("/vehiculos").status_code == 401
        assert login(user_client, OPERATOR, ORIGINAL).status_code == 401

    with factory() as session:
        account = session.get(Usuario, user_id)
        assert account.debe_cambiar_contrasena is True
        assert account.password_hash.startswith("$argon2id$")
        assert temporary not in account.password_hash
        assert account.contrasena_temporal_expira_en > datetime.now(timezone.utc)
        assert session.scalar(
            select(Sesion.revocada_en).where(Sesion.usuario_id == user_id)
        )
    [row] = audit_rows(factory, Evento.CONTRASENA_RESTABLECIDA)
    assert (row.usuario_id, row.entidad, row.entidad_id) == (
        admin_id,
        "usuario",
        user_id,
    )
    assert row.detalle == {"sesiones_revocadas": 1}
    assert temporary not in str(row.detalle)


def test_happy_temporary_login_forces_change_then_normal_access(reset_database):
    factory, url = reset_database
    create_user(factory, ADMIN, "ADMINISTRADOR")
    user_id = create_user(factory, OPERATOR, "OPERADOR")
    with client_for(url) as admin_client, client_for(url) as user_client:
        login(admin_client, ADMIN, ORIGINAL)
        temporary = reset(admin_client, user_id)

        response = login(user_client, OPERATOR, temporary)
        assert response.status_code == 200
        assert response.json()["debe_cambiar_contrasena"] is True
        for path in ("/vehiculos", "/usuarios", "/conductores"):
            blocked = user_client.get(path)
            assert blocked.status_code == 403
            assert blocked.json() == {"detail": "Cambio de contraseña requerido"}

        changed = user_client.post(
            "/cambiar-contrasena",
            json={"contrasena_actual": temporary, "contrasena_nueva": DEFINITIVE},
        )
        assert changed.status_code == 204
        # The current session is kept and now works normally.
        assert user_client.get("/vehiculos").status_code == 200

    with client_for(url) as fresh:
        assert login(fresh, OPERATOR, temporary).status_code == 401
        relogin = login(fresh, OPERATOR, DEFINITIVE)
        assert relogin.json()["debe_cambiar_contrasena"] is False
    [row] = audit_rows(factory, Evento.CONTRASENA_CAMBIADA)
    assert row.usuario_id == row.entidad_id == user_id


def test_change_revokes_other_sessions_but_keeps_current(reset_database):
    factory, url = reset_database
    create_user(factory, OPERATOR, "OPERADOR")
    with client_for(url) as current, client_for(url) as other:
        login(current, OPERATOR, ORIGINAL)
        login(other, OPERATOR, ORIGINAL)
        response = current.post(
            "/cambiar-contrasena",
            json={"contrasena_actual": ORIGINAL, "contrasena_nueva": DEFINITIVE},
        )
        assert response.status_code == 204
        assert current.get("/vehiculos").status_code == 200
        assert other.get("/vehiculos").status_code == 401
    [row] = audit_rows(factory, Evento.CONTRASENA_CAMBIADA)
    assert row.detalle == {"sesiones_revocadas": 1}


@pytest.mark.parametrize(
    "email,role",
    [("operador-x@example.test", "OPERADOR"), ("aud@example.test", "AUDITOR")],
)
def test_unhappy_non_admin_cannot_reset(reset_database, email, role):
    factory, url = reset_database
    actor_id = create_user(factory, email, role)
    target_id = create_user(factory, ADMIN, "ADMINISTRADOR")
    with client_for(url) as client:
        login(client, email, ORIGINAL)
        response = client.post(f"/usuarios/{target_id}/restablecer-contrasena")
    assert response.status_code == 403
    assert response.json() == {"detail": "Acceso denegado"}
    denied = [
        row
        for row in audit_rows(factory, Evento.DENEGADA)
        if row.detalle["permiso"] == "usuarios.actualizar"
    ]
    assert [(row.usuario_id, row.entidad_id) for row in denied] == [
        (actor_id, target_id)
    ]
    assert audit_rows(factory, Evento.CONTRASENA_RESTABLECIDA) == []


@pytest.mark.parametrize(
    "email,role",
    [
        ("operador-list@example.test", "OPERADOR"),
        ("conductor-list@example.test", "CONDUCTOR"),
        ("analista-list@example.test", "ANALISTA"),
        ("auditor-list@example.test", "AUDITOR"),
    ],
)
def test_unhappy_user_list_is_administrator_only(reset_database, email, role):
    factory, url = reset_database
    actor_id = create_user(factory, email, role)
    with client_for(url) as client:
        login(client, email, ORIGINAL)
        response = client.get("/usuarios")
    assert response.status_code == 403
    assert response.json() == {"detail": "Acceso denegado"}
    assert "@" not in response.text
    denied = [
        row.usuario_id
        for row in audit_rows(factory, Evento.DENEGADA)
        if row.detalle["permiso"] == "usuarios.actualizar"
    ]
    assert denied == [actor_id]


def test_edge_expired_temporary_is_generic_401(reset_database):
    factory, url = reset_database
    create_user(factory, ADMIN, "ADMINISTRADOR")
    user_id = create_user(factory, OPERATOR, "OPERADOR")
    with client_for(url) as admin_client:
        login(admin_client, ADMIN, ORIGINAL)
        temporary = reset(admin_client, user_id)
    with factory.begin() as session:
        session.execute(
            update(Usuario)
            .where(Usuario.usuario_id == user_id)
            .values(
                contrasena_temporal_expira_en=datetime.now(timezone.utc)
                - timedelta(seconds=1)
            )
        )
    with client_for(url) as client:
        expired = login(client, OPERATOR, temporary)
        wrong = login(client, OPERATOR, "not-the-password-1")
    assert expired.status_code == wrong.status_code == 401
    assert expired.json() == wrong.json() == {"detail": "Credenciales inválidas"}
    assert "set-cookie" not in expired.headers


def test_edge_password_policy_self_reset_and_missing_user(reset_database):
    factory, url = reset_database
    admin_id = create_user(factory, ADMIN, "ADMINISTRADOR")
    with client_for(url) as client:
        login(client, ADMIN, ORIGINAL)
        short = client.post(
            "/cambiar-contrasena",
            json={"contrasena_actual": ORIGINAL, "contrasena_nueva": "short-11ch"},
        )
        same = client.post(
            "/cambiar-contrasena",
            json={"contrasena_actual": ORIGINAL, "contrasena_nueva": ORIGINAL},
        )
        own = client.post(f"/usuarios/{admin_id}/restablecer-contrasena")
        missing = client.post(
            "/usuarios/00000000-0000-4000-8000-000000000000/restablecer-contrasena"
        )
    assert short.status_code == same.status_code == 422
    assert "short-11ch" not in short.text and ORIGINAL not in same.text
    assert own.status_code == 409
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Usuario no encontrado"}


def test_edge_inactive_user_cannot_be_reset(reset_database):
    factory, url = reset_database
    create_user(factory, ADMIN, "ADMINISTRADOR")
    user_id = create_user(factory, OPERATOR, "OPERADOR")
    with factory.begin() as session:
        session.get(Usuario, user_id).estado = "INACTIVO"
    with client_for(url) as client:
        login(client, ADMIN, ORIGINAL)
        response = client.post(f"/usuarios/{user_id}/restablecer-contrasena")
    assert response.status_code == 409


def test_wrong_current_password_counts_and_locks_like_login(reset_database):
    factory, url = reset_database
    user_id = create_user(factory, OPERATOR, "OPERADOR")
    with client_for(url) as client:
        login(client, OPERATOR, ORIGINAL)
        for _ in range(3):
            response = client.post(
                "/cambiar-contrasena",
                json={
                    "contrasena_actual": "wrong-password-1",
                    "contrasena_nueva": DEFINITIVE,
                },
            )
        assert response.status_code == 400
        # Locked accounts lose their sessions until the lockout expires.
        assert client.get("/vehiculos").status_code == 401
    with factory() as session:
        account = session.get(Usuario, user_id)
        assert account.intentos_fallidos == 3
        assert account.bloqueado_hasta > datetime.now(timezone.utc)
    assert len(audit_rows(factory, Evento.LOGIN_FALLIDO)) == 3
    assert len(audit_rows(factory, Evento.CUENTA_BLOQUEADA)) == 1


def test_no_error_response_or_log_contains_a_password(reset_database, caplog):
    factory, url = reset_database
    create_user(factory, ADMIN, "ADMINISTRADOR")
    user_id = create_user(factory, OPERATOR, "OPERADOR")
    caplog.set_level(logging.DEBUG)
    bodies = []
    with client_for(url) as admin_client, client_for(url) as user_client:
        login(admin_client, ADMIN, ORIGINAL)
        temporary = reset(admin_client, user_id)
        login(user_client, OPERATOR, temporary)
        for body in (
            {"contrasena_actual": temporary, "contrasena_nueva": "short-11ch"},
            {"contrasena_actual": temporary, "contrasena_nueva": temporary},
            {"contrasena_actual": "wrong-password-1", "contrasena_nueva": DEFINITIVE},
        ):
            response = user_client.post("/cambiar-contrasena", json=body)
            assert response.status_code >= 400
            bodies.append(response.text)
        bodies.append(login(user_client, OPERATOR, "wrong-password-1").text)
    secrets = (temporary, ORIGINAL, DEFINITIVE, "short-11ch", "wrong-password-1")
    for secret in secrets:
        assert all(secret not in body for body in bodies)
        assert secret not in caplog.text
    with factory() as session:
        stored = str([row.detalle for row in session.scalars(select(Auditoria))])
    assert all(secret not in stored for secret in secrets)


def test_0012_upgrade_downgrade_upgrade_and_single_head(migration_database):
    engine, config = migration_database
    assert ScriptDirectory.from_config(config).get_heads() == ["0012_password_reset"]
    command.upgrade(config, "0012_password_reset")
    with engine.connect() as connection:
        columns = {
            row.column_name: row
            for row in connection.execute(
                text(
                    "SELECT column_name, is_nullable, column_default "
                    "FROM information_schema.columns WHERE table_name = 'usuario'"
                )
            )
        }
        assert columns["debe_cambiar_contrasena"].is_nullable == "NO"
        assert columns["debe_cambiar_contrasena"].column_default == "false"
        assert columns["contrasena_temporal_expira_en"].is_nullable == "YES"
        constraint = connection.scalar(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'ck_auditoria_accion'"
            )
        )
        for action in (
            "CONTRASENA_RESTABLECIDA",
            "CONTRASENA_CAMBIADA",
            "CONDUCTOR_ACTUALIZADO",
            "LOGIN_EXITOSO",
        ):
            assert action in constraint
    command.downgrade(config, "0011_pedido_prioridad_index")
    with engine.connect() as connection:
        assert not connection.scalar(
            text(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = 'usuario' AND column_name LIKE '%contrasena%'"
            )
        )
    command.upgrade(config, "head")
    command.check(config)


@pytest.mark.parametrize("action", ["CONTRASENA_RESTABLECIDA", "CONTRASENA_CAMBIADA"])
def test_0012_downgrade_rejects_and_preserves_password_audit(
    migration_database, action
):
    engine, config = migration_database
    command.upgrade(config, "0012_password_reset")
    with engine.begin() as connection:
        user_id = connection.scalar(
            text(
                "INSERT INTO usuario (email, password_hash, rol) "
                "VALUES ('reset-audit@example.test', 'placeholder', 'ADMINISTRADOR') "
                "RETURNING usuario_id"
            )
        )
        connection.execute(
            text(
                "INSERT INTO auditoria (usuario_id, entidad, entidad_id, accion, "
                "detalle) VALUES (:user_id, 'usuario', :user_id, :action, "
                "'{\"sesiones_revocadas\": 0}'::jsonb)"
            ),
            {"user_id": user_id, "action": action},
        )
    with pytest.raises(IntegrityError, match="require manual treatment"):
        command.downgrade(config, "0011_pedido_prioridad_index")
    with engine.begin() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0012_password_reset"
        )
        # Explicit cleanup applies only to the disposable test database.
        result = connection.execute(
            text("DELETE FROM auditoria WHERE accion = :action"), {"action": action}
        )
        assert result.rowcount == 1
    command.downgrade(config, "0011_pedido_prioridad_index")
