"""Persist conductor data; route eligibility belongs to future services.

Design decisions from ECL-47/ST-021 remain provisional until ratified.
"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Conductor(Base):
    __tablename__ = "conductor"
    __table_args__ = (
        UniqueConstraint("usuario_id", name="uq_conductor_usuario_id"),
        UniqueConstraint("dni", name="uq_conductor_dni"),
        CheckConstraint("dni ~ '^[0-9]{8}$'", name="ck_conductor_dni_ocho_digitos"),
        CheckConstraint("nombre ~ '[^[:space:]]'", name="ck_conductor_nombre"),
        CheckConstraint(
            "licencia_numero ~ '[^[:space:]]'", name="ck_conductor_licencia"
        ),
        CheckConstraint(
            r"telefono ~ '^\+[1-9][0-9]{7,14}$'",
            name="ck_conductor_telefono_e164",
        ),
        CheckConstraint(
            "punto_partida ~ '[^[:space:]]'", name="ck_conductor_punto_partida"
        ),
        CheckConstraint("experiencia_anios >= 0", name="ck_conductor_experiencia"),
        CheckConstraint(
            "(disponible_desde IS NULL AND disponible_hasta IS NULL) OR "
            "(disponible_desde IS NOT NULL AND disponible_hasta IS NOT NULL "
            "AND disponible_desde < disponible_hasta)",
            name="ck_conductor_disponibilidad_intervalo",
        ),
        CheckConstraint("estado IN ('ACTIVO', 'INACTIVO')", name="ck_conductor_estado"),
    )

    conductor_id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    usuario_id: Mapped[UUID] = mapped_column(
        ForeignKey("usuario.usuario_id", name="fk_conductor_usuario_id_usuario"),
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    dni: Mapped[str] = mapped_column(String(8), nullable=False)
    licencia_numero: Mapped[str] = mapped_column(String(20), nullable=False)
    licencia_vigente_hasta: Mapped[date] = mapped_column(Date, nullable=False)
    experiencia_anios: Mapped[int] = mapped_column(Integer, nullable=False)
    telefono: Mapped[str] = mapped_column(String(16), nullable=False)
    disponible_desde: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    disponible_hasta: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    punto_partida: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[str] = mapped_column(
        String(15), nullable=False, server_default=text("'ACTIVO'")
    )

    def __repr__(self) -> str:
        return "<Conductor>"
