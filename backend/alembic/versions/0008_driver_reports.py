"""Persist current driver stop assignments and idempotent delivery reports."""

import sqlalchemy as sa

from alembic import op

revision = "0008_driver_reports"
down_revision = "0007_create_conductor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "driver_stop_assignment",
        sa.Column("stop_id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=15),
            server_default=sa.text("'PENDIENTE'"),
            nullable=False,
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("position > 0", name="ck_driver_stop_position"),
        sa.CheckConstraint(
            "status IN ('PENDIENTE','EN_RUTA','ENTREGADO','NO_ENTREGADO')",
            name="ck_driver_stop_status",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["usuario.usuario_id"],
            name="fk_driver_stop_owner",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("stop_id"),
    )
    op.create_index(
        "ix_driver_stop_owner_position",
        "driver_stop_assignment",
        ["owner_id", "position"],
    )
    op.create_table(
        "driver_report",
        sa.Column("operation_id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("stop_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=15), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('ENTREGADO','NO_ENTREGADO')",
            name="ck_driver_report_status",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["usuario.usuario_id"],
            name="fk_driver_report_owner",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["stop_id"],
            ["driver_stop_assignment.stop_id"],
            name="fk_driver_report_stop_assignment",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("operation_id"),
    )
    op.create_index(
        "ix_driver_report_owner_created",
        "driver_report",
        ["owner_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_driver_report_owner_created", table_name="driver_report")
    op.drop_table("driver_report")
    op.drop_index(
        "ix_driver_stop_owner_position",
        table_name="driver_stop_assignment",
    )
    op.drop_table("driver_stop_assignment")
