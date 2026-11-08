"""Route closure and real sustainability aggregate (ECL-119, US-009).

Each route keeps its own sequential reference (the manual practice on exactly
its orders and vehicle), so the dashboard compares closed routes with the same
coverage. A partial index serves the period filter on ``cerrada_en``. Adds the
RUTA_CERRADA audit action. Once in ``main``, changes need a new revision.
"""

import sqlalchemy as sa

from alembic import op

revision = "0018_cierre_rutas"
down_revision = "0017_parametros_versionados"
branch_labels = None
depends_on = None

_METRICAS = ("distancia_km", "co2_kg", "combustible_l", "costo_soles")
_PREVIOUS = (
    "'AUTORIZACION_PERMITIDA','AUTORIZACION_DENEGADA','LOGIN_EXITOSO',"
    "'LOGIN_FALLIDO','CUENTA_BLOQUEADA','SESION_CERRADA',"
    "'VEHICULO_PARAMETROS_ACTUALIZADOS','VEHICULO_DESACTIVADO',"
    "'CONDUCTOR_REGISTRADO','CONDUCTOR_ACTUALIZADO',"
    "'CONTRASENA_RESTABLECIDA','CONTRASENA_CAMBIADA',"
    "'INCIDENCIA_REGISTRADA','INCIDENCIA_RESUELTA','SESION_EXTENDIDA',"
    "'PARAMETROS_VERSIONADOS'"
)


def upgrade() -> None:
    for m in _METRICAS:
        op.add_column("ruta", sa.Column(f"secuencial_{m}", sa.Double(), nullable=True))
    op.create_check_constraint(
        "ck_ruta_secuencial",
        "ruta",
        " AND ".join(
            f"(secuencial_{m} IS NULL OR secuencial_{m} >= 0)" for m in _METRICAS
        ),
    )
    op.create_index(
        "ix_ruta_cerrada_en",
        "ruta",
        ["cerrada_en"],
        postgresql_where=sa.text("estado = 'CERRADA'"),
    )
    op.drop_constraint("ck_auditoria_accion", "auditoria", type_="check")
    op.create_check_constraint(
        "ck_auditoria_accion", "auditoria", f"accion IN ({_PREVIOUS},'RUTA_CERRADA')"
    )


def downgrade() -> None:
    # Closed routes and their references feed historical indicators.
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM ruta
                    WHERE estado = 'CERRADA' OR secuencial_distancia_km IS NOT NULL
                ) OR EXISTS (
                    SELECT 1 FROM auditoria WHERE accion = 'RUTA_CERRADA'
                ) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = 'check_violation',
                        MESSAGE = 'Cannot downgrade to 0017: ECL-119 route '
                                  'closures require manual treatment';
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
    op.drop_index("ix_ruta_cerrada_en", table_name="ruta")
    op.drop_constraint("ck_ruta_secuencial", "ruta", type_="check")
    for m in reversed(_METRICAS):
        op.drop_column("ruta", f"secuencial_{m}")
