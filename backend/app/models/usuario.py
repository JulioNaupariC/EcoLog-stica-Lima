"""Approved usuario schema. Role is structural; no authorization is performed."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.rbac import Rol
from app.db.base import Base

ROLES = tuple(rol.value for rol in Rol)
ESTADOS = ("ACTIVO", "BLOQUEADO", "INACTIVO")


class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = (
        UniqueConstraint("email", name="uq_usuario_email"),
        CheckConstraint(
            "rol IN ('ADMINISTRADOR','OPERADOR','CONDUCTOR','ANALISTA','AUDITOR')",
            name="ck_usuario_rol",
        ),
        CheckConstraint(
            "estado IN ('ACTIVO','BLOQUEADO','INACTIVO')", name="ck_usuario_estado"
        ),
        CheckConstraint(
            "intentos_fallidos BETWEEN 0 AND 3", name="ck_usuario_intentos_fallidos"
        ),
    )

    usuario_id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(15), server_default=text("'ACTIVO'"))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    intentos_fallidos: Mapped[int] = mapped_column(
        SmallInteger, server_default=text("0")
    )
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return "<Usuario>"
