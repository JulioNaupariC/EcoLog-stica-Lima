"""Link driver stops to existing orders without inventing route data."""

import sqlalchemy as sa

from alembic import op

revision = "0009_driver_stop_order"
down_revision = "0008_driver_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "driver_stop_assignment", sa.Column("pedido_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_driver_stop_pedido",
        "driver_stop_assignment",
        "pedido",
        ["pedido_id"],
        ["pedido_id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_driver_stop_pedido", "driver_stop_assignment", ["pedido_id"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_driver_stop_pedido", "driver_stop_assignment", type_="unique"
    )
    op.drop_constraint(
        "fk_driver_stop_pedido", "driver_stop_assignment", type_="foreignkey"
    )
    op.drop_column("driver_stop_assignment", "pedido_id")
