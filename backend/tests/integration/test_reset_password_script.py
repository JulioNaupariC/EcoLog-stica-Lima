"""ECL-78 over PostgreSQL: scripts/reset_password.py with the real login chain.

The transaction is exercised directly because the disposable test database
ends in ``_test``, which the script's guard refuses by design; that refusal is
itself checked end to end. Passwords here are synthetic and test-only.
"""

import io
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from alembic import command
from app.core.config import Settings
from app.db.session import session_factory
from app.main import create_app
from app.models import Auditoria, Sesion, Usuario
from app.repositories.auditoria import Evento
from app.repositories.usuarios import UsuarioRepository
from app.services.credenciales import CredentialService
from scripts.reset_password import ResetRefused, main, reset_password

pytestmark = pytest.mark.integration

EMAIL = "administrador.demo@ecologistica.example"
OLD = "contrasena-anterior-1"
NEW = "contrasena-nueva-segura"


class Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True


@pytest.fixture
def script_database(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = session_factory(engine)
    try:
        yield factory, config.attributes["database_url"]
    finally:
        # Disposable *_test evidence; lets the protected downgrades run.
        with factory.begin() as session:
            session.execute(delete(Auditoria))


def create_user(factory, email=EMAIL):
    with factory.begin() as session:
        return (
            CredentialService(UsuarioRepository(session))
            .create(email, OLD, "ADMINISTRADOR")
            .usuario_id
        )


def client_for(url):
    return TestClient(create_app(Settings(app_env="test", database_url=url)))


def login(client, password):
    return client.post("/login", json={"email": EMAIL, "password": password})


def password_audit(factory):
    with factory() as session:
        return list(
            session.scalars(
                select(Auditoria).where(
                    Auditoria.accion == Evento.CONTRASENA_CAMBIADA.value
                )
            )
        )


def test_golden_login_works_with_new_password_and_not_the_old_one(script_database):
    factory, url = script_database
    create_user(factory)

    assert reset_password(factory, EMAIL, NEW) == 0

    with client_for(url) as client:
        assert login(client, OLD).status_code == 401
        response = login(client, NEW)
        assert response.status_code == 200
        assert response.json()["debe_cambiar_contrasena"] is False


def test_happy_sessions_are_revoked_state_cleared_and_audited(script_database):
    factory, url = script_database
    user_id = create_user(factory)
    with client_for(url) as first, client_for(url) as second:
        assert login(first, OLD).status_code == 200
        assert login(second, OLD).status_code == 200
        assert first.get("/usuarios").status_code == 200
        # Leftovers of a previous reset and failed attempts are cleared too.
        with factory.begin() as session:
            account = session.get(Usuario, user_id)
            account.debe_cambiar_contrasena = True
            account.contrasena_temporal_expira_en = datetime.now(
                timezone.utc
            ) + timedelta(hours=1)
            account.intentos_fallidos = 2

        assert reset_password(factory, EMAIL, NEW) == 2

        assert first.get("/usuarios").status_code == 401
        assert second.get("/usuarios").status_code == 401

    with factory() as session:
        account = session.get(Usuario, user_id)
        assert account.debe_cambiar_contrasena is False
        assert account.contrasena_temporal_expira_en is None
        assert account.intentos_fallidos == 0
        assert account.bloqueado_hasta is None
        assert account.password_hash.startswith("$argon2id$")
        assert NEW not in account.password_hash
        assert all(
            revoked is not None
            for revoked in session.scalars(
                select(Sesion.revocada_en).where(Sesion.usuario_id == user_id)
            )
        )
    [row] = password_audit(factory)
    assert (row.usuario_id, row.entidad, row.entidad_id) == (
        user_id,
        "usuario",
        user_id,
    )
    assert row.detalle == {"sesiones_revocadas": 2}
    assert NEW not in str(row.detalle) and OLD not in str(row.detalle)


def test_unhappy_non_local_database_is_refused_without_changes(
    script_database, monkeypatch, capsys
):
    factory, url = script_database
    user_id = create_user(factory)
    with factory() as session:
        before = session.get(Usuario, user_id).password_hash
    # The real test database ends in _test: the guard must refuse it.
    monkeypatch.setenv("DATABASE_URL", url)
    prompt = pytest.fail  # Never reached: refused before prompting.

    code = main(
        ["--email", EMAIL],
        {"APP_ENV": "development"},
        stdin=Terminal(),
        prompt=prompt,
    )

    assert code == 2
    assert "'_demo' o '_local'" in capsys.readouterr().err
    with factory() as session:
        assert session.get(Usuario, user_id).password_hash == before
    assert password_audit(factory) == []


def test_edge_unknown_email_changes_nothing(script_database):
    factory, url = script_database
    user_id = create_user(factory)
    with client_for(url) as client:
        assert login(client, OLD).status_code == 200
        with pytest.raises(ResetRefused, match="No existe una cuenta") as error:
            reset_password(factory, "nadie@ecologistica.example", NEW)
        assert NEW not in str(error.value)
        assert client.get("/usuarios").status_code == 200
    with factory() as session:
        assert (
            session.scalar(
                select(Sesion.revocada_en).where(Sesion.usuario_id == user_id)
            )
            is None
        )
    assert password_audit(factory) == []
    with client_for(url) as client:
        assert login(client, OLD).status_code == 200
