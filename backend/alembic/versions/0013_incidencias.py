"""Driver incidents and their registration audit (ECL-73 / ST-040).

Catalogues and the observation limit come from app.core.incidencias, the single
source while the ECL-72 BDD is pending. Once this revision is in ``main``, any
catalogue change needs a new revision instead of editing this one.
"""

import sqlalchemy as sa
from geoalchemy2 import Geography

from alembic import op
from app.core.incidencias import ESTADOS, OBSERVACION_MAX, SEVERIDADES, TIPOS, sql_in

revision = "0013_incidencias"
down_revision = "0012_password_reset"
branch_labels = None
depends_on = None

_PREVIOUS_ACTIONS = (
    "'AUTORIZACION_PERMITIDA','AUTORIZACION_DENEGADA','LOGIN_EXITOSO',"
    "'LOGIN_FALLIDO','CUENTA_BLOQUEADA','SESION_CERRADA',"
    "'VEHICULO_PARAMETROS_ACTUALIZADOS','VEHICULO_DESACTIVADO',"
    "'CONDUCTOR_REGISTRADO','CONDUCTOR_ACTUALIZADO',"
    "'CONTRASENA_RESTABLECIDA','CONTRASENA_CAMBIADA'"
)
_INCIDENT_ACTIONS = "'INCIDENCIA_REGISTRADA'"


def upgrade() -> None:
    op.create_table(
        "incidencia",
        sa.Column(
            "incidencia_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("conductor_id", sa.Uuid(), nullable=False),
        sa.Column("parada_id", sa.Uuid(), nullable=True),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("severidad", sa.String(10), nullable=False),
        sa.Column(
            "ubicacion",
            Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("ocurrida_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "registrada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("observacion", sa.String(OBSERVACION_MAX), nullable=True),
        sa.Column(
            "estado",
            sa.String(25),
            server_default=sa.text("'PENDIENTE_VALIDACION'"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("incidencia_id"),
        sa.ForeignKeyConstraint(
            ["conductor_id"],
            ["conductor.conductor_id"],
            name="fk_incidencia_conductor",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parada_id"],
            ["driver_stop_assignment.stop_id"],
            name="fk_incidencia_parada",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("operation_id", name="uq_incidencia_operation_id"),
        sa.CheckConstraint(f"tipo IN ({sql_in(TIPOS)})", name="ck_incidencia_tipo"),
        sa.CheckConstraint(
            f"severidad IN ({sql_in(SEVERIDADES)})", name="ck_incidencia_severidad"
        ),
        sa.CheckConstraint(
            f"estado IN ({sql_in(ESTADOS)})", name="ck_incidencia_estado"
        ),
        sa.CheckConstraint(
            f"observacion IS NULL OR char_length(observacion) <= {OBSERVACION_MAX}",
            name="ck_incidencia_observacion",
        ),
    )
    op.create_index(
        "ix_incidencia_estado_ocurrida",
        "incidencia",
        ["estado", sa.text("ocurrida_en DESC")],
    )
    op.create_index("ix_incidencia_conductor", "incidencia", ["conductor_id"])
    op.drop_constraint("ck_auditoria_accion", "auditoria", type_="check")
    op.create_check_constraint(
        "ck_auditoria_accion",
        "auditoria",
        f"accion IN ({_PREVIOUS_ACTIONS},{_INCIDENT_ACTIONS})",
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM auditoria WHERE accion IN ({_INCIDENT_ACTIONS})
                ) OR EXISTS (SELECT 1 FROM incidencia) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = 'check_violation',
                        MESSAGE = 'Cannot downgrade to 0012: ECL-73 incidents and '
                                  'their audit records require manual treatment';
                END IF;
            END
            $$;
            """
        )
    )
    op.drop_constraint("ck_auditoria_accion", "auditoria", type_="check")
    op.create_check_constraint(
        "ck_auditoria_accion",
        "auditoria",
        f"accion IN ({_PREVIOUS_ACTIONS})",
    )
    op.drop_index("ix_incidencia_conductor", table_name="incidencia")
    op.drop_index("ix_incidencia_estado_ocurrida", table_name="incidencia")
    op.drop_table("incidencia")
