"""Add temporary login lockout, opaque sessions and access audit events."""

import sqlalchemy as sa

from alembic import op

revision = "0003_create_login_sessions"
down_revision = "0002_create_auditoria"
branch_labels = None
depends_on = None

_AUTH_ACTIONS = "'AUTORIZACION_PERMITIDA','AUTORIZACION_DENEGADA'"
_ACCESS_ACTIONS = "'LOGIN_EXITOSO','LOGIN_FALLIDO','CUENTA_BLOQUEADA','SESION_CERRADA'"


def upgrade() -> None:
    op.add_column(
        "usuario",
        sa.Column(
            "intentos_fallidos",
            sa.SmallInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column("usuario", sa.Column("bloqueado_hasta", sa.DateTime(timezone=True)))
    op.create_check_constraint(
        "ck_usuario_intentos_fallidos",
        "usuario",
        "intentos_fallidos BETWEEN 0 AND 3",
    )
    op.create_table(
        "sesion",
        sa.Column(
            "sesion_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revocada_en", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("sesion_id"),
        sa.UniqueConstraint("token_hash", name="uq_sesion_token_hash"),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.usuario_id"],
            name="fk_sesion_usuario",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("expira_en > creado_en", name="ck_sesion_expiracion"),
    )
    op.create_index("ix_sesion_usuario", "sesion", ["usuario_id"])
    op.drop_constraint("ck_auditoria_accion", "auditoria", type_="check")
    op.create_check_constraint(
        "ck_auditoria_accion",
        "auditoria",
        f"accion IN ({_AUTH_ACTIONS},{_ACCESS_ACTIONS})",
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM auditoria WHERE accion IN ({_ACCESS_ACTIONS})
                ) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = 'check_violation',
                        MESSAGE = 'Cannot downgrade to 0002: ECL-36 audit records '
                                  'require manual treatment';
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
        f"accion IN ({_AUTH_ACTIONS})",
    )
    op.drop_index("ix_sesion_usuario", table_name="sesion")
    op.drop_table("sesion")
    op.drop_constraint("ck_usuario_intentos_fallidos", "usuario", type_="check")
    op.drop_column("usuario", "bloqueado_hasta")
    op.drop_column("usuario", "intentos_fallidos")
