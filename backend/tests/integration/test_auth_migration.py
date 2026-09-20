import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command

pytestmark = pytest.mark.integration


def test_upgrade_check_downgrade_and_upgrade_login_schema(migration_database):
    engine, config = migration_database
    command.upgrade(config, "0002_create_auditoria")
    command.upgrade(config, "head")
    command.check(config)


def test_downgrade_rejects_access_audit_and_preserves_it(migration_database):
    engine, config = migration_database
    heads = ScriptDirectory.from_config(config).get_heads()
    assert len(heads) == 1, f"Expected one Alembic head, found {heads}"
    expected_head = heads[0]
    command.upgrade(config, "head")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO auditoria (entidad, accion, detalle)
                VALUES ('usuario', 'LOGIN_FALLIDO',
                        CAST('{"resultado":"CREDENCIALES_INVALIDAS"}' AS jsonb))
                """
            )
        )

    with pytest.raises(IntegrityError, match="require manual treatment"):
        command.downgrade(config, "0002_create_auditoria")

    with engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM auditoria WHERE accion = 'LOGIN_FALLIDO'")
            )
            == 1
        )
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            expected_head
        )

    # Explicit manual treatment for this disposable test database only.
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM auditoria WHERE accion = 'LOGIN_FALLIDO'"))
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert inspector.has_table("sesion")
        columns = {column["name"] for column in inspector.get_columns("usuario")}
        assert {"intentos_fallidos", "bloqueado_hasta"} <= columns
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            expected_head
        )
    command.downgrade(config, "0002_create_auditoria")
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert not inspector.has_table("sesion")
        columns = {column["name"] for column in inspector.get_columns("usuario")}
        assert "intentos_fallidos" not in columns
        assert "bloqueado_hasta" not in columns
    command.upgrade(config, "head")
    command.check(config)
