import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text

from alembic import command
from app.db.base import Base
from app.models import Usuario  # noqa: F401

pytestmark = pytest.mark.integration


def test_upgrade_downgrade_and_metadata(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert inspect(connection).has_table("usuario")
        assert connection.scalar(text("SELECT gen_random_uuid()")) is not None
        context = MigrationContext.configure(
            connection,
            opts={
                "include_object": lambda obj, name, type_, reflected, compare_to: (
                    not (type_ == "table" and name == "spatial_ref_sys" and reflected)
                )
            },
        )
        assert compare_metadata(context, Base.metadata) == []
    command.downgrade(config, "base")
    with engine.connect() as connection:
        assert not inspect(connection).has_table("usuario")
    command.upgrade(config, "head")
    command.downgrade(config, "base")
