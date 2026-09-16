"""Create the approved usuario credential table."""

import sqlalchemy as sa

from alembic import op

revision = "0001_create_usuario"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuario",
        sa.Column(
            "usuario_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("rol", sa.String(20), nullable=False),
        sa.Column(
            "estado", sa.String(15), server_default=sa.text("'ACTIVO'"), nullable=False
        ),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("usuario_id"),
        sa.UniqueConstraint("email", name="uq_usuario_email"),
        sa.CheckConstraint(
            "rol IN ('ADMINISTRADOR','OPERADOR','CONDUCTOR','ANALISTA','AUDITOR')",
            name="ck_usuario_rol",
        ),
        sa.CheckConstraint(
            "estado IN ('ACTIVO','BLOQUEADO','INACTIVO')", name="ck_usuario_estado"
        ),
    )


def downgrade() -> None:
    op.drop_table("usuario")
