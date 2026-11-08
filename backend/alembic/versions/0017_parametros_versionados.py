"""Versioned calculation parameters (EN-008 / ECL-26, RNF-011).

``parametro_version`` keeps each complete set with its validity window and
``parametro`` each value with a fixed unit and a verifiable source. An
optimization's ``parametros_version`` now references an existing version, so a
completed run is always reproducible. Adds the PARAMETROS_VERSIONADOS audit
action. Once in ``main``, changes need a new revision.
"""

import sqlalchemy as sa

from alembic import op
from app.core.parametros import (
    FUENTE_MAX,
    NOTA_MAX,
    UNIDADES,
    VERSION_MAX,
    sql_in,
    unidad_valida_sql,
)

revision = "0017_parametros_versionados"
down_revision = "0016_modelo_rutas"
branch_labels = None
depends_on = None

_PREVIOUS = (
    "'AUTORIZACION_PERMITIDA','AUTORIZACION_DENEGADA','LOGIN_EXITOSO',"
    "'LOGIN_FALLIDO','CUENTA_BLOQUEADA','SESION_CERRADA',"
    "'VEHICULO_PARAMETROS_ACTUALIZADOS','VEHICULO_DESACTIVADO',"
    "'CONDUCTOR_REGISTRADO','CONDUCTOR_ACTUALIZADO',"
    "'CONTRASENA_RESTABLECIDA','CONTRASENA_CAMBIADA',"
    "'INCIDENCIA_REGISTRADA','INCIDENCIA_RESUELTA','SESION_EXTENDIDA'"
)


def upgrade() -> None:
    op.create_table(
        "parametro_version",
        sa.Column(
            "version_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("version", sa.String(VERSION_MAX), nullable=False),
        sa.Column("vigente_desde", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vigente_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creada_por", sa.Uuid(), nullable=False),
        sa.Column(
            "creada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("nota", sa.String(NOTA_MAX), nullable=True),
        sa.PrimaryKeyConstraint("version_id"),
        sa.UniqueConstraint("version", name="uq_parametro_version_codigo"),
        sa.ForeignKeyConstraint(
            ["creada_por"],
            ["usuario.usuario_id"],
            name="fk_parametro_version_usuario",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "vigente_hasta IS NULL OR vigente_hasta > vigente_desde",
            name="ck_parametro_version_vigencia",
        ),
        sa.CheckConstraint(
            "version ~ '^[A-Z0-9][A-Z0-9._-]*$'", name="ck_parametro_version_formato"
        ),
    )
    op.create_index(
        "uq_parametro_version_abierta",
        "parametro_version",
        [sa.text("(vigente_hasta IS NULL)")],
        unique=True,
        postgresql_where=sa.text("vigente_hasta IS NULL"),
    )
    op.create_index(
        "ix_parametro_version_vigencia", "parametro_version", ["vigente_desde"]
    )
    op.create_table(
        "parametro",
        sa.Column(
            "parametro_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("codigo", sa.String(30), nullable=False),
        sa.Column("valor", sa.Numeric(18, 9), nullable=False),
        sa.Column("unidad", sa.String(20), nullable=False),
        sa.Column("fuente", sa.String(FUENTE_MAX), nullable=False),
        sa.PrimaryKeyConstraint("parametro_id"),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["parametro_version.version_id"],
            name="fk_parametro_version",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "version_id", "codigo", name="uq_parametro_version_codigo_valor"
        ),
        sa.CheckConstraint(
            f"codigo IN ({sql_in(tuple(UNIDADES))})", name="ck_parametro_codigo"
        ),
        sa.CheckConstraint(unidad_valida_sql(), name="ck_parametro_unidad"),
        sa.CheckConstraint(
            "valor <> 'NaN'::numeric AND valor > 0", name="ck_parametro_valor"
        ),
        sa.CheckConstraint("fuente ~ '[^[:space:]]'", name="ck_parametro_fuente"),
    )
    op.create_foreign_key(
        "fk_optimizacion_parametros",
        "optimizacion",
        "parametro_version",
        ["parametros_version"],
        ["version"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("ck_auditoria_accion", "auditoria", type_="check")
    op.create_check_constraint(
        "ck_auditoria_accion",
        "auditoria",
        f"accion IN ({_PREVIOUS},'PARAMETROS_VERSIONADOS')",
    )


def downgrade() -> None:
    # Parameter history backs reproducible results: never dropped silently.
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM parametro_version) OR EXISTS (
                    SELECT 1 FROM auditoria WHERE accion = 'PARAMETROS_VERSIONADOS'
                ) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = 'check_violation',
                        MESSAGE = 'Cannot downgrade to 0016: EN-008 parameter '
                                  'versions require manual treatment';
                END IF;
            END
            $$;
            """
        )
    )
    op.drop_constraint("ck_auditoria_accion", "auditoria", type_="check")
    op.create_check_constraint(
        "ck_auditoria_accion", "auditoria", f"accion IN ({_PREVIOUS})"
    )
    op.drop_constraint("fk_optimizacion_parametros", "optimizacion", type_="foreignkey")
    op.drop_table("parametro")
    op.drop_index("ix_parametro_version_vigencia", table_name="parametro_version")
    op.drop_index("uq_parametro_version_abierta", table_name="parametro_version")
    op.drop_table("parametro_version")
