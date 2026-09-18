"""Approved audit fields; append-only through the application repository."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Auditoria(Base):
    __tablename__ = "auditoria"
    __table_args__ = (
        CheckConstraint(
            "accion IN ('AUTORIZACION_PERMITIDA','AUTORIZACION_DENEGADA')",
            name="ck_auditoria_accion",
        ),
        CheckConstraint(
            "jsonb_typeof(detalle) = 'object'", name="ck_auditoria_detalle"
        ),
        Index("ix_auditoria_creado_en", "creado_en"),
        Index("ix_auditoria_usuario_fecha", "usuario_id", "creado_en"),
    )

    auditoria_id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    usuario_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "usuario.usuario_id", name="fk_auditoria_usuario", ondelete="RESTRICT"
        )
    )
    entidad: Mapped[str] = mapped_column(String(50))
    entidad_id: Mapped[UUID | None] = mapped_column()
    accion: Mapped[str] = mapped_column(String(64))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    detalle: Mapped[dict[str, str | None]] = mapped_column(JSONB)

    def __repr__(self) -> str:
        return "<Auditoria>"
