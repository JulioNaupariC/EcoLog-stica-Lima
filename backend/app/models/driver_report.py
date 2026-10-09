"""Idempotently persisted, minimal driver delivery events."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DriverReport(Base):
    __tablename__ = "driver_report"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ENTREGADO','NO_ENTREGADO')",
            name="ck_driver_report_status",
        ),
        Index("ix_driver_report_owner_created", "owner_id", "created_at"),
    )

    operation_id: Mapped[UUID] = mapped_column(primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "usuario.usuario_id",
            name="fk_driver_report_owner",
            ondelete="RESTRICT",
        )
    )
    stop_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "driver_stop_assignment.stop_id",
            name="fk_driver_report_stop_assignment",
            ondelete="RESTRICT",
        )
    )
    status: Mapped[str] = mapped_column(String(15))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )

    def __repr__(self) -> str:
        return "<DriverReport>"
