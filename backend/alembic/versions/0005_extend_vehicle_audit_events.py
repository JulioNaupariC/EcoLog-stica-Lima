"""Extend audit actions for atomic vehicle changes."""

import sqlalchemy as sa

from alembic import op

revision = "0005_extend_vehicle_audit_events"
down_revision = "0004_create_vehiculo"
branch_labels = None
depends_on = None

_PREVIOUS_ACTIONS = (
    "'AUTORIZACION_PERMITIDA','AUTORIZACION_DENEGADA','LOGIN_EXITOSO',"
    "'LOGIN_FALLIDO','CUENTA_BLOQUEADA','SESION_CERRADA'"
)
_VEHICLE_ACTIONS = "'VEHICULO_PARAMETROS_ACTUALIZADOS','VEHICULO_DESACTIVADO'"


def upgrade() -> None:
    op.drop_constraint("ck_auditoria_accion", "auditoria", type_="check")
    op.create_check_constraint(
        "ck_auditoria_accion",
        "auditoria",
        f"accion IN ({_PREVIOUS_ACTIONS},{_VEHICLE_ACTIONS})",
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM auditoria WHERE accion IN ({_VEHICLE_ACTIONS})
                ) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = 'check_violation',
                        MESSAGE = 'Cannot downgrade to 0004: ECL-40 vehicle audit '
                                  'records require manual treatment';
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
