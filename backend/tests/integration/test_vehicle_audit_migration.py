import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.db.base import Base
from app.models import Vehiculo  # noqa: F401

pytestmark = pytest.mark.integration


def test_0005_clean_downgrade_and_metadata(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    command.check(config)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0005_extend_vehicle_audit_events"
        )
        context = MigrationContext.configure(
            connection,
            opts={
                "include_object": lambda obj, name, type_, reflected, compare_to: (
                    not (type_ == "table" and name == "spatial_ref_sys" and reflected)
                )
            },
        )
        assert compare_metadata(context, Base.metadata) == []
    command.downgrade(config, "0004_create_vehiculo")
    command.upgrade(config, "head")


@pytest.mark.parametrize(
    "action",
    ["VEHICULO_PARAMETROS_ACTUALIZADOS", "VEHICULO_DESACTIVADO"],
)
def test_0005_downgrade_rejects_and_preserves_vehicle_audit(migration_database, action):
    engine, config = migration_database
    command.upgrade(config, "head")
    with engine.begin() as connection:
        user_id = connection.scalar(
            text(
                "INSERT INTO usuario (email, password_hash, rol) "
                "VALUES ('vehicle-audit@example.test', 'placeholder', 'ADMINISTRADOR') "
                "RETURNING usuario_id"
            )
        )
        vehicle_id = connection.scalar(
            text(
                """
                INSERT INTO vehiculo (
                    placa, tipo, capacidad_kg, capacidad_m3,
                    rendimiento_km_l, factor_co2_kg_km, anio_fabricacion
                ) VALUES ('AUD-1', 'CAMIONETA', 1000, 8, 10, 0.3, 2024)
                RETURNING vehiculo_id
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO auditoria (
                    usuario_id, entidad, entidad_id, accion, detalle
                ) VALUES (
                    :user_id, 'vehiculo', :vehicle_id,
                    :action, '{}'::jsonb
                )
                """
            ),
            {"user_id": user_id, "vehicle_id": vehicle_id, "action": action},
        )
    with pytest.raises(IntegrityError, match="require manual treatment"):
        command.downgrade(config, "0004_create_vehiculo")
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM auditoria WHERE accion = :action"),
                {"action": action},
            )
            == 1
        )
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0005_extend_vehicle_audit_events"
        )

    # Explicit cleanup applies only to the disposable test database.
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM auditoria"))
    command.downgrade(config, "0004_create_vehiculo")
    command.upgrade(config, "head")
