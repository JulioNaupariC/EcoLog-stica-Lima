"""Resolve pending incidents and audit the decision (ECL-98)."""

import sqlalchemy as sa

from alembic import op

revision = "0014_resolver_incidencias"
down_revision = "0013_incidencias"
branch_labels = None
depends_on = None

_PREVIOUS = (
    "'AUTORIZACION_PERMITIDA','AUTORIZACION_DENEGADA','LOGIN_EXITOSO',"
    "'LOGIN_FALLIDO','CUENTA_BLOQUEADA','SESION_CERRADA',"
    "'VEHICULO_PARAMETROS_ACTUALIZADOS','VEHICULO_DESACTIVADO',"
    "'CONDUCTOR_REGISTRADO','CONDUCTOR_ACTUALIZADO',"
    "'CONTRASENA_RESTABLECIDA','CONTRASENA_CAMBIADA','INCIDENCIA_REGISTRADA'"
)


def upgrade() -> None:
    op.add_column("incidencia", sa.Column("resuelta_por", sa.Uuid(), nullable=True))
    op.add_column(
        "incidencia",
        sa.Column("resuelta_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("incidencia", sa.Column("motivo", sa.String(300), nullable=True))
    op.create_foreign_key(
        "fk_incidencia_resuelta_por",
        "incidencia",
        "usuario",
        ["resuelta_por"],
        ["usuario_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_incidencia_motivo", "incidencia", "char_length(motivo) <= 300"
    )
    op.drop_constraint("ck_auditoria_accion", "auditoria", type_="check")
    op.create_check_constraint(
        "ck_auditoria_accion",
        "auditoria",
        f"accion IN ({_PREVIOUS},'INCIDENCIA_RESUELTA')",
    )


def downgrade() -> None:
    # Preserve decisions and append-only audit: refuse destructive downgrades.
    op.execute(
        sa.text("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM incidencia WHERE resuelta_por IS NOT NULL)
               OR EXISTS (SELECT 1 FROM auditoria WHERE accion = 'INCIDENCIA_RESUELTA')
            THEN RAISE EXCEPTION USING
                ERRCODE = 'check_violation',
                MESSAGE = 'ECL-98 resolutions require manual treatment';
            END IF;
        END $$;
    """)
    )
    op.drop_constraint("ck_auditoria_accion", "auditoria", type_="check")
    op.create_check_constraint(
        "ck_auditoria_accion", "auditoria", f"accion IN ({_PREVIOUS})"
    )
    op.drop_constraint("ck_incidencia_motivo", "incidencia", type_="check")
    op.drop_constraint("fk_incidencia_resuelta_por", "incidencia", type_="foreignkey")
    for column in ("motivo", "resuelta_en", "resuelta_por"):
        op.drop_column("incidencia", column)
