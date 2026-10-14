"""Index orders by state and priority for the home aggregates (ECL-25).

The GROUP BY estado, prioridad of /indicadores/operacion becomes an index-only
scan: 721 -> 28 shared buffers and ~12 -> ~4 ms on 30 000 orders (evidence in
backend/evidencias/ECL-25-inicio). Cost: 224 kB and one B-tree entry per order.
"""

from alembic import op

revision = "0011_pedido_prioridad_index"
down_revision = "0010_extend_driver_audit_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("idx_pedido_estado_prioridad", "pedido", ["estado", "prioridad"])


def downgrade() -> None:
    op.drop_index("idx_pedido_estado_prioridad", table_name="pedido")
