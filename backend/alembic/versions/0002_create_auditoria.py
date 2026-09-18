"""Create authorization audit storage without changing usuario."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002_create_auditoria"
down_revision = "0001_create_usuario"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auditoria",
        sa.Column(
            "auditoria_id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("usuario_id", sa.UUID(), nullable=True),
        sa.Column("entidad", sa.String(50), nullable=False),
        sa.Column("entidad_id", sa.UUID(), nullable=True),
        sa.Column("accion", sa.String(64), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("detalle", postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("auditoria_id"),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.usuario_id"],
            name="fk_auditoria_usuario",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "accion IN ('AUTORIZACION_PERMITIDA','AUTORIZACION_DENEGADA')",
            name="ck_auditoria_accion",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(detalle) = 'object'", name="ck_auditoria_detalle"
        ),
    )
    op.create_index("ix_auditoria_creado_en", "auditoria", ["creado_en"])
    op.create_index(
        "ix_auditoria_usuario_fecha", "auditoria", ["usuario_id", "creado_en"]
    )


def downgrade() -> None:
    op.drop_index("ix_auditoria_usuario_fecha", table_name="auditoria")
    op.drop_index("ix_auditoria_creado_en", table_name="auditoria")
    op.drop_table("auditoria")
