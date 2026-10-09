import pytest
from sqlalchemy import inspect, text

from alembic import command

pytestmark = pytest.mark.integration


def test_driver_assignment_and_report_migration(migration_database):
    engine, config = migration_database
    command.upgrade(config, "0006_create_cliente_pedido")
    command.upgrade(config, "0008_driver_assignments_and_reports")

    with engine.connect() as connection:
        inspector = inspect(connection)
        assert set(inspector.get_table_names()) >= {
            "driver_stop_assignment",
            "driver_report",
        }
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0008_driver_assignments_and_reports"
        )
        assert {
            column["name"] for column in inspector.get_columns("driver_stop_assignment")
        } == {"stop_id", "owner_id", "position", "status", "assigned_at"}
        assert {
            column["name"] for column in inspector.get_columns("driver_report")
        } == {"operation_id", "owner_id", "stop_id", "status", "created_at"}
        assert {
            foreign_key["referred_table"]
            for foreign_key in inspector.get_foreign_keys("driver_report")
        } == {"usuario", "driver_stop_assignment"}
        assert {
            index["name"] for index in inspector.get_indexes("driver_stop_assignment")
        } == {"ix_driver_stop_owner_position"}
        assert {index["name"] for index in inspector.get_indexes("driver_report")} == {
            "ix_driver_report_owner_created"
        }
        assert {
            constraint["name"]
            for constraint in inspector.get_check_constraints("driver_stop_assignment")
        } == {"ck_driver_stop_position", "ck_driver_stop_status"}
        assert {
            constraint["name"]
            for constraint in inspector.get_check_constraints("driver_report")
        } == {"ck_driver_report_status"}

    command.downgrade(config, "0006_create_cliente_pedido")
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert not inspector.has_table("driver_report")
        assert not inspector.has_table("driver_stop_assignment")

    command.upgrade(config, "head")
    command.check(config)
