import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text

from alembic import command
from app.db.base import Base
from app.models import Vehiculo  # noqa: F401

pytestmark = pytest.mark.integration


def test_vehicle_upgrade_constraints_downgrade_and_metadata(migration_database):
    engine, config = migration_database
    command.upgrade(config, "0003_create_login_sessions")
    with engine.connect() as connection:
        assert not inspect(connection).has_table("vehiculo")

    command.upgrade(config, "0004_create_vehiculo")
    command.check(config)
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert inspector.has_table("vehiculo")
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0004_create_vehiculo"
        )
        assert {column["name"] for column in inspector.get_columns("vehiculo")} == {
            "vehiculo_id",
            "placa",
            "tipo",
            "capacidad_kg",
            "capacidad_m3",
            "rendimiento_km_l",
            "factor_co2_kg_km",
            "anio_fabricacion",
            "estado",
        }
        assert inspector.get_pk_constraint("vehiculo")["constrained_columns"] == [
            "vehiculo_id"
        ]
        assert {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("vehiculo")
        } == {"uq_vehiculo_placa"}
        assert {
            constraint["name"]
            for constraint in inspector.get_check_constraints("vehiculo")
        } == {
            "ck_vehiculo_placa_canonica",
            "ck_vehiculo_tipo",
            "ck_vehiculo_capacidad_kg",
            "ck_vehiculo_capacidad_m3",
            "ck_vehiculo_rendimiento_km_l",
            "ck_vehiculo_factor_co2_kg_km",
            "ck_vehiculo_anio_fabricacion",
        }
        indexes = {
            index["name"]: index["column_names"]
            for index in inspector.get_indexes("vehiculo")
        }
        assert indexes["ix_vehiculo_estado"] == ["estado"]
        context = MigrationContext.configure(
            connection,
            opts={
                "include_object": lambda obj, name, type_, reflected, compare_to: (
                    not (type_ == "table" and name == "spatial_ref_sys" and reflected)
                )
            },
        )
        assert compare_metadata(context, Base.metadata) == []

    command.downgrade(config, "0003_create_login_sessions")
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert not inspector.has_table("vehiculo")
        assert all(
            inspector.has_table(table) for table in ("usuario", "auditoria", "sesion")
        )
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0003_create_login_sessions"
        )

    command.upgrade(config, "head")
    command.check(config)
