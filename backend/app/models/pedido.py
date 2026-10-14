"""Order inputs approved for later route planning."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Pedido(Base):
    __tablename__ = "pedido"
    __table_args__ = (
        CheckConstraint("direccion ~ '[^[:space:]]'", name="ck_pedido_direccion"),
        CheckConstraint(
            "referencia IS NULL OR referencia ~ '[^[:space:]]'",
            name="ck_pedido_referencia",
        ),
        CheckConstraint(
            "ubicacion IS NOT NULL OR coalesce(referencia ~ '[^[:space:]]', false)",
            name="ck_pedido_ubicacion_o_referencia",
        ),
        CheckConstraint(
            "peso_kg <> 'NaN'::numeric AND peso_kg > 0", name="ck_pedido_peso_kg"
        ),
        CheckConstraint(
            "volumen_m3 <> 'NaN'::numeric AND volumen_m3 > 0",
            name="ck_pedido_volumen_m3",
        ),
        CheckConstraint("ventana_inicio < ventana_fin", name="ck_pedido_ventana"),
        CheckConstraint(
            "prioridad IN ('EXPRESS','ESTANDAR','ECONOMICO')",
            name="ck_pedido_prioridad",
        ),
        CheckConstraint(
            "tipo_producto ~ '[^[:space:]]'", name="ck_pedido_tipo_producto"
        ),
        Index("idx_pedido_pendiente_ventana", "estado", "ventana_inicio"),
        Index("idx_pedido_estado_prioridad", "estado", "prioridad"),
        Index("idx_pedido_ubicacion", "ubicacion", postgresql_using="gist"),
    )

    pedido_id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    cliente_id: Mapped[UUID] = mapped_column(
        ForeignKey("cliente.cliente_id", name="fk_pedido_cliente_id_cliente")
    )
    direccion: Mapped[str] = mapped_column(String(255))
    referencia: Mapped[str | None] = mapped_column(String(255))
    ubicacion: Mapped[WKBElement | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    peso_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    volumen_m3: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    ventana_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ventana_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    prioridad: Mapped[str] = mapped_column(String(12))
    tipo_producto: Mapped[str] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(15), server_default=text("'PENDIENTE'"))

    def __repr__(self) -> str:
        return "<Pedido>"
