"""Vehicle capacity and sustainability inputs approved for route planning."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Index,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

TIPOS_VEHICULO = ("CAMIONETA", "FURGON", "MOTO")


class Vehiculo(Base):
    __tablename__ = "vehiculo"
    __table_args__ = (
        UniqueConstraint("placa", name="uq_vehiculo_placa"),
        CheckConstraint(
            "placa = upper(btrim(placa)) AND length(placa) > 0",
            name="ck_vehiculo_placa_canonica",
        ),
        CheckConstraint(
            "tipo IN ('CAMIONETA','FURGON','MOTO')", name="ck_vehiculo_tipo"
        ),
        CheckConstraint("capacidad_kg > 0", name="ck_vehiculo_capacidad_kg"),
        CheckConstraint("capacidad_m3 > 0", name="ck_vehiculo_capacidad_m3"),
        CheckConstraint("rendimiento_km_l > 0", name="ck_vehiculo_rendimiento_km_l"),
        CheckConstraint("factor_co2_kg_km >= 0", name="ck_vehiculo_factor_co2_kg_km"),
        CheckConstraint(
            "anio_fabricacion BETWEEN 1980 AND 2100",
            name="ck_vehiculo_anio_fabricacion",
        ),
        Index("ix_vehiculo_estado", "estado"),
    )

    vehiculo_id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    placa: Mapped[str] = mapped_column(String(10))
    tipo: Mapped[str] = mapped_column(String(20))
    capacidad_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    capacidad_m3: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    rendimiento_km_l: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    factor_co2_kg_km: Mapped[Decimal] = mapped_column(Numeric(10, 5))
    anio_fabricacion: Mapped[int] = mapped_column(SmallInteger)
    estado: Mapped[str] = mapped_column(String(15), server_default=text("'ACTIVO'"))

    def __repr__(self) -> str:
        return "<Vehiculo>"
