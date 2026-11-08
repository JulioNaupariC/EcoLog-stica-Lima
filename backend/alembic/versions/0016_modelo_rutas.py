"""Route model: optimization runs, routes, stops and unassigned orders (ECL-95).

ST-046 for US-006. Tables follow document 11 (Base de datos V_1_2_0) and the
ratified US-006 BDD v1.0.0: each run keeps its parameter version and snapshot,
metrics are stored unrounded (RNF-011), a route without driver states why
(ECL-79) and every unassigned order keeps its reason (RN-009). Incidents gain a
nullable ``ruta_id`` and a driver stop assignment may point to its planned stop,
which gives it a jornada for ECL-82. Once in ``main``, changes need a new
revision.
"""

import sqlalchemy as sa
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.incidencias import sql_in
from app.core.rutas import (
    ERROR_MAX,
    ESTADOS_OPTIMIZACION,
    ESTADOS_PARADA,
    ESTADOS_RUTA,
    MOTIVOS_NO_ASIGNADO,
    MOTIVOS_SIN_CONDUCTOR,
    PARAMETROS_VERSION_MAX,
)

revision = "0016_modelo_rutas"
down_revision = "0015_sesion_extendida"
branch_labels = None
depends_on = None

_METRICAS = ("distancia_km", "co2_kg", "combustible_l", "costo_soles")


def _optimizacion() -> None:
    op.create_table(
        "optimizacion",
        sa.Column(
            "optimizacion_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("solicitada_por", sa.Uuid(), nullable=False),
        sa.Column("fecha_operacion", sa.Date(), nullable=False),
        sa.Column(
            "estado",
            sa.String(12),
            server_default=sa.text("'EN_PROCESO'"),
            nullable=False,
        ),
        sa.Column(
            "solicitada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("finalizada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duracion_s", sa.Double(), nullable=True),
        sa.Column(
            "parametros_version", sa.String(PARAMETROS_VERSION_MAX), nullable=True
        ),
        sa.Column(
            "simulado", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("error", sa.String(ERROR_MAX), nullable=True),
        *(sa.Column(f"secuencial_{m}", sa.Double(), nullable=True) for m in _METRICAS),
        sa.Column("cumplimiento_ventanas_pct", sa.Double(), nullable=True),
        sa.Column(
            "instantanea",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("optimizacion_id"),
        sa.ForeignKeyConstraint(
            ["solicitada_por"],
            ["usuario.usuario_id"],
            name="fk_optimizacion_usuario",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            f"estado IN ({sql_in(ESTADOS_OPTIMIZACION)})",
            name="ck_optimizacion_estado",
        ),
        sa.CheckConstraint(
            "(estado = 'EN_PROCESO') = (finalizada_en IS NULL)",
            name="ck_optimizacion_finalizada",
        ),
        sa.CheckConstraint(
            "finalizada_en IS NULL OR finalizada_en >= solicitada_en",
            name="ck_optimizacion_orden_fechas",
        ),
        sa.CheckConstraint(
            "(estado = 'FALLIDA') = (error IS NOT NULL)",
            name="ck_optimizacion_error",
        ),
        sa.CheckConstraint(
            "estado <> 'COMPLETADA' OR parametros_version IS NOT NULL",
            name="ck_optimizacion_parametros",
        ),
        sa.CheckConstraint(
            "duracion_s IS NULL OR duracion_s >= 0", name="ck_optimizacion_duracion"
        ),
        sa.CheckConstraint(
            "cumplimiento_ventanas_pct IS NULL OR "
            "cumplimiento_ventanas_pct BETWEEN 0 AND 100",
            name="ck_optimizacion_cumplimiento",
        ),
        *(
            sa.CheckConstraint(
                f"secuencial_{m} IS NULL OR secuencial_{m} >= 0",
                name=f"ck_optimizacion_secuencial_{m}",
            )
            for m in _METRICAS
        ),
        sa.CheckConstraint(
            "jsonb_typeof(instantanea) = 'object'", name="ck_optimizacion_instantanea"
        ),
    )
    op.create_index(
        "ix_optimizacion_solicitada",
        "optimizacion",
        [sa.text("solicitada_en DESC"), "optimizacion_id"],
    )
    op.create_index(
        "ix_optimizacion_fecha_estado", "optimizacion", ["fecha_operacion", "estado"]
    )


def _ruta() -> None:
    op.create_table(
        "ruta",
        sa.Column(
            "ruta_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("optimizacion_id", sa.Uuid(), nullable=False),
        sa.Column("fecha_operacion", sa.Date(), nullable=False),
        sa.Column("vehiculo_id", sa.Uuid(), nullable=False),
        sa.Column("conductor_id", sa.Uuid(), nullable=True),
        sa.Column("motivo_sin_conductor", sa.String(30), nullable=True),
        sa.Column(
            "estado",
            sa.String(12),
            server_default=sa.text("'PLANIFICADA'"),
            nullable=False,
        ),
        sa.Column("salida", sa.DateTime(timezone=True), nullable=False),
        sa.Column("regreso", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tiempo_min", sa.Integer(), nullable=False),
        sa.Column("peso_kg", sa.Numeric(10, 2), nullable=False),
        sa.Column("volumen_m3", sa.Numeric(10, 3), nullable=False),
        *(sa.Column(m, sa.Double(), nullable=False) for m in _METRICAS),
        sa.Column(
            "trazado",
            Geography(geometry_type="LINESTRING", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column(
            "descansos",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("cerrada_en", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("ruta_id"),
        sa.ForeignKeyConstraint(
            ["optimizacion_id"],
            ["optimizacion.optimizacion_id"],
            name="fk_ruta_optimizacion",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["vehiculo_id"],
            ["vehiculo.vehiculo_id"],
            name="fk_ruta_vehiculo",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["conductor_id"],
            ["conductor.conductor_id"],
            name="fk_ruta_conductor",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            f"estado IN ({sql_in(ESTADOS_RUTA)})", name="ck_ruta_estado"
        ),
        sa.CheckConstraint(
            "(estado = 'CERRADA') = (cerrada_en IS NOT NULL)", name="ck_ruta_cerrada"
        ),
        sa.CheckConstraint(
            "(conductor_id IS NULL) = (motivo_sin_conductor IS NOT NULL)",
            name="ck_ruta_conductor",
        ),
        sa.CheckConstraint(
            "motivo_sin_conductor IS NULL OR "
            f"motivo_sin_conductor IN ({sql_in(MOTIVOS_SIN_CONDUCTOR)})",
            name="ck_ruta_motivo_sin_conductor",
        ),
        sa.CheckConstraint("regreso >= salida", name="ck_ruta_horario"),
        sa.CheckConstraint(
            "tiempo_min >= 0 AND peso_kg >= 0 AND volumen_m3 >= 0",
            name="ck_ruta_carga",
        ),
        sa.CheckConstraint(
            " AND ".join(f"{m} >= 0" for m in _METRICAS), name="ck_ruta_metricas"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(descansos) = 'array'", name="ck_ruta_descansos"
        ),
        sa.UniqueConstraint("optimizacion_id", "vehiculo_id", name="uq_ruta_vehiculo"),
        sa.UniqueConstraint("ruta_id", "optimizacion_id", name="uq_ruta_optimizacion"),
    )
    op.create_index(
        "uq_ruta_conductor",
        "ruta",
        ["optimizacion_id", "conductor_id"],
        unique=True,
        postgresql_where=sa.text("conductor_id IS NOT NULL"),
    )
    op.create_index(
        "ix_ruta_conductor_fecha", "ruta", ["conductor_id", "fecha_operacion"]
    )
    op.create_index("ix_ruta_fecha_estado", "ruta", ["fecha_operacion", "estado"])
    op.create_index("ix_ruta_trazado", "ruta", ["trazado"], postgresql_using="gist")


def _paradas_y_no_asignados() -> None:
    op.create_table(
        "parada_ruta",
        sa.Column(
            "parada_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("ruta_id", sa.Uuid(), nullable=False),
        sa.Column("optimizacion_id", sa.Uuid(), nullable=False),
        sa.Column("pedido_id", sa.Uuid(), nullable=False),
        sa.Column("secuencia", sa.Integer(), nullable=False),
        sa.Column("eta", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "estado",
            sa.String(12),
            server_default=sa.text("'PENDIENTE'"),
            nullable=False,
        ),
        sa.Column("atendida_en", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("parada_id"),
        sa.ForeignKeyConstraint(
            ["ruta_id", "optimizacion_id"],
            ["ruta.ruta_id", "ruta.optimizacion_id"],
            name="fk_parada_ruta_ruta",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["pedido_id"],
            ["pedido.pedido_id"],
            name="fk_parada_ruta_pedido",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("secuencia > 0", name="ck_parada_ruta_secuencia"),
        sa.CheckConstraint(
            f"estado IN ({sql_in(ESTADOS_PARADA)})", name="ck_parada_ruta_estado"
        ),
        sa.CheckConstraint(
            "estado <> 'ATENDIDA' OR atendida_en IS NOT NULL",
            name="ck_parada_ruta_atendida",
        ),
        sa.UniqueConstraint("ruta_id", "secuencia", name="uq_parada_ruta_secuencia"),
        sa.UniqueConstraint(
            "optimizacion_id", "pedido_id", name="uq_parada_ruta_pedido"
        ),
    )
    op.create_index("ix_parada_ruta_pedido", "parada_ruta", ["pedido_id"])
    op.create_table(
        "pedido_no_asignado",
        sa.Column("optimizacion_id", sa.Uuid(), nullable=False),
        sa.Column("pedido_id", sa.Uuid(), nullable=False),
        sa.Column("motivo", sa.String(20), nullable=False),
        sa.PrimaryKeyConstraint(
            "optimizacion_id", "pedido_id", name="pk_pedido_no_asignado"
        ),
        sa.ForeignKeyConstraint(
            ["optimizacion_id"],
            ["optimizacion.optimizacion_id"],
            name="fk_pedido_no_asignado_optimizacion",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["pedido_id"],
            ["pedido.pedido_id"],
            name="fk_pedido_no_asignado_pedido",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            f"motivo IN ({sql_in(MOTIVOS_NO_ASIGNADO)})",
            name="ck_pedido_no_asignado_motivo",
        ),
    )


def upgrade() -> None:
    _optimizacion()
    _ruta()
    _paradas_y_no_asignados()
    op.add_column("incidencia", sa.Column("ruta_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_incidencia_ruta",
        "incidencia",
        "ruta",
        ["ruta_id"],
        ["ruta_id"],
        ondelete="RESTRICT",
    )
    op.add_column(
        "driver_stop_assignment",
        sa.Column("parada_ruta_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_driver_stop_parada_ruta",
        "driver_stop_assignment",
        "parada_ruta",
        ["parada_ruta_id"],
        ["parada_id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_driver_stop_parada_ruta", "driver_stop_assignment", ["parada_ruta_id"]
    )


def downgrade() -> None:
    # Routes are operational history: never dropped silently (as 0013 does).
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM optimizacion) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = 'check_violation',
                        MESSAGE = 'Cannot downgrade to 0015: ECL-95 optimizations '
                                  'and routes require manual treatment';
                END IF;
            END
            $$;
            """
        )
    )
    op.drop_constraint(
        "uq_driver_stop_parada_ruta", "driver_stop_assignment", type_="unique"
    )
    op.drop_constraint(
        "fk_driver_stop_parada_ruta", "driver_stop_assignment", type_="foreignkey"
    )
    op.drop_column("driver_stop_assignment", "parada_ruta_id")
    op.drop_constraint("fk_incidencia_ruta", "incidencia", type_="foreignkey")
    op.drop_column("incidencia", "ruta_id")
    op.drop_table("pedido_no_asignado")
    op.drop_index("ix_parada_ruta_pedido", table_name="parada_ruta")
    op.drop_table("parada_ruta")
    for index in (
        "ix_ruta_trazado",
        "ix_ruta_fecha_estado",
        "ix_ruta_conductor_fecha",
        "uq_ruta_conductor",
    ):
        op.drop_index(index, table_name="ruta")
    op.drop_table("ruta")
    op.drop_index("ix_optimizacion_fecha_estado", table_name="optimizacion")
    op.drop_index("ix_optimizacion_solicitada", table_name="optimizacion")
    op.drop_table("optimizacion")
