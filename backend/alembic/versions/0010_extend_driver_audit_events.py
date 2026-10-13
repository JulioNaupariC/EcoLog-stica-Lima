"""Extend audit actions for driver registration and updates (RN-015)."""

import sqlalchemy as sa

from alembic import op

revision = "0010_extend_driver_audit_events"
down_revision = "0009_driver_stop_order"
branch_labels = None
depends_on = None

_PREVIOUS_ACTIONS = (
    "'AUTORIZACION_PERMITIDA','AUTORIZACION_DENEGADA','LOGIN_EXITOSO',"
    "'LOGIN_FALLIDO','CUENTA_BLOQUEADA','SESION_CERRADA',"
    "'VEHICULO_PARAMETROS_ACTUALIZADOS','VEHICULO_DESACTIVADO'"
)
_DRIVER_ACTIONS = "'CONDUCTOR_REGISTRADO','CONDUCTOR_ACTUALIZADO'"


def upgrade() -> None:
    op.drop_constraint("ck_auditoria_accion", "auditoria", type_="check")
    op.create_check_constraint(
        "ck_auditoria_accion",
        "auditoria",
        f"accion IN ({_PREVIOUS_ACTIONS},{_DRIVER_ACTIONS})",
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM auditoria WHERE accion IN ({_DRIVER_ACTIONS})
                ) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = 'check_violation',
                        MESSAGE = 'Cannot downgrade to 0009: ECL-48 driver audit '
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
