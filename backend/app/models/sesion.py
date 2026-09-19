"""Revocable opaque login session. The clear token is never persisted."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Sesion(Base):
    __tablename__ = "sesion"
    __table_args__ = (
        CheckConstraint("expira_en > creado_en", name="ck_sesion_expiracion"),
        Index("ix_sesion_usuario", "usuario_id"),
    )

    sesion_id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    usuario_id: Mapped[UUID] = mapped_column(
        ForeignKey("usuario.usuario_id", name="fk_sesion_usuario", ondelete="RESTRICT")
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revocada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return "<Sesion>"
