"""ECL-83: admit audited session extensions; number reserved with Antony."""

import sqlalchemy as sa

from alembic import op

revision = "0015_sesion_extendida"
down_revision = "0014_resolver_incidencias"
branch_labels = None
depends_on = None

_PREVIOUS = (
    "'AUTORIZACION_PERMITIDA','AUTORIZACION_DENEGADA','LOGIN_EXITOSO',"
    "'LOGIN_FALLIDO','CUENTA_BLOQUEADA','SESION_CERRADA',"
    "'VEHICULO_PARAMETROS_ACTUALIZADOS','VEHICULO_DESACTIVADO',"
    "'CONDUCTOR_REGISTRADO','CONDUCTOR_ACTUALIZADO',"
    "'CONTRASENA_RESTABLECIDA','CONTRASENA_CAMBIADA',"
    "'INCIDENCIA_REGISTRADA','INCIDENCIA_RESUELTA'"
)


def upgrade() -> None:
    op.drop_constraint("ck_auditoria_accion", "auditoria", type_="check")
    op.create_check_constraint(
        "ck_auditoria_accion",
        "auditoria",
        f"accion IN ({_PREVIOUS},'SESION_EXTENDIDA')",
    )


def downgrade() -> None:
    # Explicit rollback policy agreed with Antony for ECL-83. Other events remain.
    op.execute(sa.text("DELETE FROM auditoria WHERE accion = 'SESION_EXTENDIDA'"))
    op.drop_constraint("ck_auditoria_accion", "auditoria", type_="check")
    op.create_check_constraint(
        "ck_auditoria_accion", "auditoria", f"accion IN ({_PREVIOUS})"
    )
