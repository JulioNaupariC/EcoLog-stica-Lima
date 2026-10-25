"""Administrator password reset with mandatory change (ECL-77 / US-013).

Coordination with ECL-73: both tickets create a 0012 revision and extend
ck_auditoria_accion. Whichever merges second must point its down_revision to the
other one and include its actions in _PREVIOUS_ACTIONS, keeping a single head.
"""

import sqlalchemy as sa

from alembic import op

revision = "0012_password_reset"
down_revision = "0011_pedido_prioridad_index"
branch_labels = None
depends_on = None

_PREVIOUS_ACTIONS = (
    "'AUTORIZACION_PERMITIDA','AUTORIZACION_DENEGADA','LOGIN_EXITOSO',"
    "'LOGIN_FALLIDO','CUENTA_BLOQUEADA','SESION_CERRADA',"
    "'VEHICULO_PARAMETROS_ACTUALIZADOS','VEHICULO_DESACTIVADO',"
    "'CONDUCTOR_REGISTRADO','CONDUCTOR_ACTUALIZADO'"
)
_PASSWORD_ACTIONS = "'CONTRASENA_RESTABLECIDA','CONTRASENA_CAMBIADA'"


def upgrade() -> None:
    op.add_column(
        "usuario",
        sa.Column(
            "debe_cambiar_contrasena",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "usuario",
        sa.Column(
            "contrasena_temporal_expira_en",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.drop_constraint("ck_auditoria_accion", "auditoria", type_="check")
    op.create_check_constraint(
        "ck_auditoria_accion",
        "auditoria",
        f"accion IN ({_PREVIOUS_ACTIONS},{_PASSWORD_ACTIONS})",
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM auditoria WHERE accion IN ({_PASSWORD_ACTIONS})
                ) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = 'check_violation',
                        MESSAGE = 'Cannot downgrade to 0011: ECL-77 password audit '
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
    op.drop_column("usuario", "contrasena_temporal_expira_en")
    op.drop_column("usuario", "debe_cambiar_contrasena")
