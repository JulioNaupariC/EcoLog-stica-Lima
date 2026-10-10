"""Trusted driver-to-stop assignments supplied by the route-planning workflow."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

STOP_STATES = ("PENDIENTE", "EN_RUTA", "ENTREGADO", "NO_ENTREGADO")


class DriverStopAssignment(Base):
    __tablename__ = "driver_stop_assignment"
    __table_args__ = (
        UniqueConstraint("pedido_id", name="uq_driver_stop_pedido"),
        CheckConstraint("position > 0", name="ck_driver_stop_position"),
        CheckConstraint(
            "status IN ('PENDIENTE','EN_RUTA','ENTREGADO','NO_ENTREGADO')",
            name="ck_driver_stop_status",
        ),
        Index("ix_driver_stop_owner_position", "owner_id", "position"),
    )

    stop_id: Mapped[UUID] = mapped_column(primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "usuario.usuario_id",
            name="fk_driver_stop_owner",
            ondelete="RESTRICT",
        )
    )
    position: Mapped[int] = mapped_column(Integer)
    pedido_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "pedido.pedido_id", name="fk_driver_stop_pedido", ondelete="RESTRICT"
        ),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(15), server_default=text("'PENDIENTE'"))
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )

    def __repr__(self) -> str:
        return "<DriverStopAssignment>"
