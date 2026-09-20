import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from alembic import command

pytestmark = pytest.mark.integration


def test_audit_upgrade_check_downgrade_preserves_usuario(migration_database):
    engine, config = migration_database
    heads = ScriptDirectory.from_config(config).get_heads()
    assert len(heads) == 1, f"Expected one Alembic head, found {heads}"
    expected_head = heads[0]
    command.upgrade(config, "0001_create_usuario")
    with engine.begin() as connection:
        identifier = connection.scalar(
            text(
                "INSERT INTO usuario (email, password_hash, rol) "
                "VALUES ('migration@example.test', 'test-placeholder', 'AUDITOR') "
                "RETURNING usuario_id"
            )
        )
        spatial_before = inspect(connection).has_table("spatial_ref_sys")
    command.upgrade(config, "head")
    command.check(config)
    with engine.connect() as connection:
        assert inspect(connection).has_table("auditoria")
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == expected_head
        )
    command.downgrade(config, "0001_create_usuario")
    with engine.connect() as connection:
        assert not inspect(connection).has_table("auditoria")
        assert connection.scalar(text("SELECT usuario_id FROM usuario")) == identifier
        assert inspect(connection).has_table("spatial_ref_sys") == spatial_before
    command.upgrade(config, "head")
    command.check(config)
