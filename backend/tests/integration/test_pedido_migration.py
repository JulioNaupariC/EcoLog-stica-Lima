import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text

from alembic import command
from app.db.base import Base
from app.models import Cliente, Pedido  # noqa: F401

pytestmark = pytest.mark.integration


def test_client_order_revision_and_metadata(migration_database):
    engine, config = migration_database
    command.upgrade(config, "0005_extend_vehicle_audit_events")
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert not inspector.has_table("cliente")
        assert not inspector.has_table("pedido")

    command.upgrade(config, "0006_create_cliente_pedido")
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert {column["name"] for column in inspector.get_columns("cliente")} == {
            "cliente_id",
            "nombre",
            "horario_preferido",
            "referencia",
            "restriccion_acceso",
        }
        assert {column["name"] for column in inspector.get_columns("pedido")} == {
            "pedido_id",
            "cliente_id",
            "direccion",
            "referencia",
            "ubicacion",
            "peso_kg",
            "volumen_m3",
            "ventana_inicio",
            "ventana_fin",
            "prioridad",
            "tipo_producto",
            "estado",
        }
        foreign_keys = inspector.get_foreign_keys("pedido")
        assert len(foreign_keys) == 1
        assert foreign_keys[0]["name"] == "fk_pedido_cliente_id_cliente"
        assert foreign_keys[0]["referred_table"] == "cliente"
        checks = {item["name"] for item in inspector.get_check_constraints("pedido")}
        assert checks == {
            "ck_pedido_direccion",
            "ck_pedido_referencia",
            "ck_pedido_ubicacion_o_referencia",
            "ck_pedido_peso_kg",
            "ck_pedido_volumen_m3",
            "ck_pedido_ventana",
            "ck_pedido_prioridad",
            "ck_pedido_tipo_producto",
        }
        indexes = {item["name"]: item for item in inspector.get_indexes("pedido")}
        assert indexes["idx_pedido_pendiente_ventana"]["column_names"] == [
            "estado",
            "ventana_inicio",
        ]
        assert (
            indexes["idx_pedido_ubicacion"]["dialect_options"]["postgresql_using"]
            == "gist"
        )
        spatial_type = connection.scalar(
            text(
                """
                SELECT format_type(a.atttypid, a.atttypmod)
                FROM pg_attribute AS a
                WHERE a.attrelid = 'pedido'::regclass AND a.attname = 'ubicacion'
                """
            )
        )
        assert spatial_type.lower() == "geography(point,4326)"
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0006_create_cliente_pedido"
        )

    # This test verifies the 0006 shape above. Upgrade to the current head
    # before comparing the entire ORM metadata (including conductor/0007).
    command.upgrade(config, "head")
    command.check(config)
    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={
                "include_object": lambda obj, name, type_, reflected, compare_to: (
                    not (type_ == "table" and name == "spatial_ref_sys" and reflected)
                )
            },
        )
        assert compare_metadata(context, Base.metadata) == []

    command.downgrade(config, "0005_extend_vehicle_audit_events")
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert not inspector.has_table("pedido")
        assert not inspector.has_table("cliente")
        assert inspector.has_table("vehiculo")
