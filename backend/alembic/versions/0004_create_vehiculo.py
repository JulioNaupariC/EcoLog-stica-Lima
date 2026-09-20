"""Create the approved vehicle planning resource."""

import sqlalchemy as sa

from alembic import op

revision = "0004_create_vehiculo"
down_revision = "0003_create_login_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehiculo",
        sa.Column(
            "vehiculo_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("placa", sa.String(10), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("capacidad_kg", sa.Numeric(10, 2), nullable=False),
        sa.Column("capacidad_m3", sa.Numeric(10, 2), nullable=False),
        sa.Column("rendimiento_km_l", sa.Numeric(10, 3), nullable=False),
        sa.Column("factor_co2_kg_km", sa.Numeric(10, 5), nullable=False),
        sa.Column("anio_fabricacion", sa.SmallInteger(), nullable=False),
        sa.Column(
            "estado",
            sa.String(15),
            server_default=sa.text("'ACTIVO'"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("vehiculo_id"),
        sa.UniqueConstraint("placa", name="uq_vehiculo_placa"),
        sa.CheckConstraint(
            "placa = upper(btrim(placa)) AND length(placa) > 0",
            name="ck_vehiculo_placa_canonica",
        ),
        sa.CheckConstraint(
            "tipo IN ('CAMIONETA','FURGON','MOTO')", name="ck_vehiculo_tipo"
        ),
        sa.CheckConstraint("capacidad_kg > 0", name="ck_vehiculo_capacidad_kg"),
        sa.CheckConstraint("capacidad_m3 > 0", name="ck_vehiculo_capacidad_m3"),
        sa.CheckConstraint("rendimiento_km_l > 0", name="ck_vehiculo_rendimiento_km_l"),
        sa.CheckConstraint(
            "factor_co2_kg_km >= 0", name="ck_vehiculo_factor_co2_kg_km"
        ),
        sa.CheckConstraint(
            "anio_fabricacion BETWEEN 1980 AND 2100",
            name="ck_vehiculo_anio_fabricacion",
        ),
    )
    op.create_index("ix_vehiculo_estado", "vehiculo", ["estado"])


def downgrade() -> None:
    op.drop_index("ix_vehiculo_estado", table_name="vehiculo")
    op.drop_table("vehiculo")
