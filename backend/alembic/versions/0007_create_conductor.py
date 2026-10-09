"""Create conductor persistence with named constraints (ST-020)."""

import sqlalchemy as sa

from alembic import op

revision = "0007_create_conductor"
down_revision = "0006_create_cliente_pedido"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conductor",
        sa.Column(
            "conductor_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.UUID(), nullable=False),
        sa.Column("nombre", sa.String(160), nullable=False),
        sa.Column("dni", sa.String(8), nullable=False),
        sa.Column("licencia_numero", sa.String(20), nullable=False),
        sa.Column("licencia_vigente_hasta", sa.Date(), nullable=False),
        sa.Column("experiencia_anios", sa.Integer(), nullable=False),
        sa.Column("telefono", sa.String(16), nullable=False),
        sa.Column("disponible_desde", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disponible_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("punto_partida", sa.String(255), nullable=False),
        sa.Column(
            "estado",
            sa.String(15),
            nullable=False,
            server_default=sa.text("'ACTIVO'"),
        ),
        sa.PrimaryKeyConstraint("conductor_id"),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.usuario_id"],
            name="fk_conductor_usuario_id_usuario",
        ),
        sa.UniqueConstraint("usuario_id", name="uq_conductor_usuario_id"),
        sa.UniqueConstraint("dni", name="uq_conductor_dni"),
        sa.CheckConstraint("dni ~ '^[0-9]{8}$'", name="ck_conductor_dni_ocho_digitos"),
        sa.CheckConstraint("nombre ~ '[^[:space:]]'", name="ck_conductor_nombre"),
        sa.CheckConstraint(
            "licencia_numero ~ '[^[:space:]]'", name="ck_conductor_licencia"
        ),
        sa.CheckConstraint(
            r"telefono ~ '^\+[1-9][0-9]{7,14}$'",
            name="ck_conductor_telefono_e164",
        ),
        sa.CheckConstraint(
            "punto_partida ~ '[^[:space:]]'", name="ck_conductor_punto_partida"
        ),
        sa.CheckConstraint("experiencia_anios >= 0", name="ck_conductor_experiencia"),
        sa.CheckConstraint(
            "(disponible_desde IS NULL AND disponible_hasta IS NULL) OR "
            "(disponible_desde IS NOT NULL AND disponible_hasta IS NOT NULL "
            "AND disponible_desde < disponible_hasta)",
            name="ck_conductor_disponibilidad_intervalo",
        ),
        sa.CheckConstraint(
            "estado IN ('ACTIVO', 'INACTIVO')", name="ck_conductor_estado"
        ),
    )


def downgrade() -> None:
    op.drop_table("conductor")
