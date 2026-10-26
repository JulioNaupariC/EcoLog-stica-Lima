"""ECL-73 driver incident. Catalogues and limits come from app.core.incidencias."""

from datetime import datetime
from uuid import UUID

from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.incidencias import ESTADOS, OBSERVACION_MAX, SEVERIDADES, TIPOS, sql_in
from app.db.base import Base


class Incidencia(Base):
    __tablename__ = "incidencia"
    __table_args__ = (
        UniqueConstraint("operation_id", name="uq_incidencia_operation_id"),
        CheckConstraint(f"tipo IN ({sql_in(TIPOS)})", name="ck_incidencia_tipo"),
        CheckConstraint(
            f"severidad IN ({sql_in(SEVERIDADES)})", name="ck_incidencia_severidad"
        ),
        CheckConstraint(f"estado IN ({sql_in(ESTADOS)})", name="ck_incidencia_estado"),
        CheckConstraint(
            f"observacion IS NULL OR char_length(observacion) <= {OBSERVACION_MAX}",
            name="ck_incidencia_observacion",
        ),
        Index(
            "ix_incidencia_estado_ocurrida",
            "estado",
            text("ocurrida_en DESC"),
        ),
        Index("ix_incidencia_conductor", "conductor_id"),
    )

    incidencia_id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    conductor_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "conductor.conductor_id",
            name="fk_incidencia_conductor",
            ondelete="RESTRICT",
        )
    )
    # Until the route model exists, the stop is the driver's stop assignment.
    parada_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "driver_stop_assignment.stop_id",
            name="fk_incidencia_parada",
            ondelete="RESTRICT",
        )
    )
    operation_id: Mapped[UUID] = mapped_column()
    tipo: Mapped[str] = mapped_column(String(20))
    severidad: Mapped[str] = mapped_column(String(10))
    ubicacion: Mapped[WKBElement] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    ocurrida_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    registrada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    observacion: Mapped[str | None] = mapped_column(String(OBSERVACION_MAX))
    estado: Mapped[str] = mapped_column(
        String(25), server_default=text("'PENDIENTE_VALIDACION'")
    )

    def __repr__(self) -> str:
        return "<Incidencia>"
