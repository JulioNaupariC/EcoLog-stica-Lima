"""ECL-95 (ST-046): persisted result of a route optimization (US-006).

``optimizacion`` keeps every run with its parameter version and the snapshot
of fleet, orders and distance matrix it used, so a later parameter change
never rewrites history (BDD US-006 v1.0.0). ``ruta`` is one vehicle's route
for an operating day (``fecha_operacion`` is the driver's *jornada*);
``parada_ruta`` orders the orders of a route and ``pedido_no_asignado`` keeps
the reason of every order left out (RN-009). Money and metrics are stored
unrounded (RNF-011); only presentation rounds.
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Double,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.incidencias import sql_in
from app.core.rutas import (
    ERROR_MAX,
    ESTADOS_OPTIMIZACION,
    ESTADOS_PARADA,
    ESTADOS_RUTA,
    MOTIVOS_NO_ASIGNADO,
    MOTIVOS_SIN_CONDUCTOR,
    PARAMETROS_VERSION_MAX,
)
from app.db.base import Base

_METRICAS = ("distancia_km", "co2_kg", "combustible_l", "costo_soles")


class Optimizacion(Base):
    __tablename__ = "optimizacion"
    __table_args__ = (
        CheckConstraint(
            f"estado IN ({sql_in(ESTADOS_OPTIMIZACION)})",
            name="ck_optimizacion_estado",
        ),
        # EN_PROCESO -> COMPLETADA | FALLIDA; only final states have an end.
        CheckConstraint(
            "(estado = 'EN_PROCESO') = (finalizada_en IS NULL)",
            name="ck_optimizacion_finalizada",
        ),
        CheckConstraint(
            "finalizada_en IS NULL OR finalizada_en >= solicitada_en",
            name="ck_optimizacion_orden_fechas",
        ),
        CheckConstraint(
            "(estado = 'FALLIDA') = (error IS NOT NULL)",
            name="ck_optimizacion_error",
        ),
        # Every completed run is reproducible with its parameter version.
        CheckConstraint(
            "estado <> 'COMPLETADA' OR parametros_version IS NOT NULL",
            name="ck_optimizacion_parametros",
        ),
        CheckConstraint(
            "duracion_s IS NULL OR duracion_s >= 0", name="ck_optimizacion_duracion"
        ),
        CheckConstraint(
            "cumplimiento_ventanas_pct IS NULL OR "
            "cumplimiento_ventanas_pct BETWEEN 0 AND 100",
            name="ck_optimizacion_cumplimiento",
        ),
        *(
            CheckConstraint(
                f"secuencial_{m} IS NULL OR secuencial_{m} >= 0",
                name=f"ck_optimizacion_secuencial_{m}",
            )
            for m in _METRICAS
        ),
        CheckConstraint(
            "jsonb_typeof(instantanea) = 'object'", name="ck_optimizacion_instantanea"
        ),
        # Listing: newest first, id ascending on ties (BDD R10).
        Index(
            "ix_optimizacion_solicitada",
            text("solicitada_en DESC"),
            "optimizacion_id",
        ),
        Index("ix_optimizacion_fecha_estado", "fecha_operacion", "estado"),
    )

    optimizacion_id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    solicitada_por: Mapped[UUID] = mapped_column(
        ForeignKey(
            "usuario.usuario_id",
            name="fk_optimizacion_usuario",
            ondelete="RESTRICT",
        )
    )
    fecha_operacion: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(12), server_default=text("'EN_PROCESO'"))
    solicitada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    finalizada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duracion_s: Mapped[float | None] = mapped_column(Double)
    # EN-008: references an existing parameter version (migration 0017).
    parametros_version: Mapped[str | None] = mapped_column(
        String(PARAMETROS_VERSION_MAX),
        ForeignKey(
            "parametro_version.version",
            name="fk_optimizacion_parametros",
            ondelete="RESTRICT",
        ),
    )
    simulado: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    error: Mapped[str | None] = mapped_column(String(ERROR_MAX))
    # Sequential reference on the same served orders (BDD US-006).
    secuencial_distancia_km: Mapped[float | None] = mapped_column(Double)
    secuencial_co2_kg: Mapped[float | None] = mapped_column(Double)
    secuencial_combustible_l: Mapped[float | None] = mapped_column(Double)
    secuencial_costo_soles: Mapped[float | None] = mapped_column(Double)
    cumplimiento_ventanas_pct: Mapped[float | None] = mapped_column(Double)
    # Fleet, orders, depot, configuration and distance matrix actually used.
    instantanea: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )

    def __repr__(self) -> str:
        return "<Optimizacion>"


class Ruta(Base):
    __tablename__ = "ruta"
    __table_args__ = (
        CheckConstraint(f"estado IN ({sql_in(ESTADOS_RUTA)})", name="ck_ruta_estado"),
        CheckConstraint(
            "(estado = 'CERRADA') = (cerrada_en IS NOT NULL)", name="ck_ruta_cerrada"
        ),
        # ECL-79: a route without driver says why; with driver, no reason.
        CheckConstraint(
            "(conductor_id IS NULL) = (motivo_sin_conductor IS NOT NULL)",
            name="ck_ruta_conductor",
        ),
        CheckConstraint(
            "motivo_sin_conductor IS NULL OR "
            f"motivo_sin_conductor IN ({sql_in(MOTIVOS_SIN_CONDUCTOR)})",
            name="ck_ruta_motivo_sin_conductor",
        ),
        CheckConstraint("regreso >= salida", name="ck_ruta_horario"),
        CheckConstraint(
            "tiempo_min >= 0 AND peso_kg >= 0 AND volumen_m3 >= 0",
            name="ck_ruta_carga",
        ),
        CheckConstraint(
            " AND ".join(f"{m} >= 0" for m in _METRICAS), name="ck_ruta_metricas"
        ),
        CheckConstraint("jsonb_typeof(descansos) = 'array'", name="ck_ruta_descansos"),
        CheckConstraint(
            " AND ".join(
                f"(secuencial_{m} IS NULL OR secuencial_{m} >= 0)" for m in _METRICAS
            ),
            name="ck_ruta_secuencial",
        ),
        # One route per vehicle and per driver inside the same optimization.
        UniqueConstraint("optimizacion_id", "vehiculo_id", name="uq_ruta_vehiculo"),
        Index(
            "uq_ruta_conductor",
            "optimizacion_id",
            "conductor_id",
            unique=True,
            postgresql_where=text("conductor_id IS NOT NULL"),
        ),
        # The driver's jornada: ECL-82 checks a stop belongs to this date.
        Index("ix_ruta_conductor_fecha", "conductor_id", "fecha_operacion"),
        Index("ix_ruta_fecha_estado", "fecha_operacion", "estado"),
        Index("ix_ruta_trazado", "trazado", postgresql_using="gist"),
        # ECL-119: US-009 filters closed routes by closing instant.
        Index(
            "ix_ruta_cerrada_en",
            "cerrada_en",
            postgresql_where=text("estado = 'CERRADA'"),
        ),
        UniqueConstraint("ruta_id", "optimizacion_id", name="uq_ruta_optimizacion"),
    )

    ruta_id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    optimizacion_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "optimizacion.optimizacion_id",
            name="fk_ruta_optimizacion",
            ondelete="RESTRICT",
        )
    )
    fecha_operacion: Mapped[date] = mapped_column(Date)
    vehiculo_id: Mapped[UUID] = mapped_column(
        ForeignKey("vehiculo.vehiculo_id", name="fk_ruta_vehiculo", ondelete="RESTRICT")
    )
    conductor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "conductor.conductor_id", name="fk_ruta_conductor", ondelete="RESTRICT"
        )
    )
    motivo_sin_conductor: Mapped[str | None] = mapped_column(String(30))
    estado: Mapped[str] = mapped_column(
        String(12), server_default=text("'PLANIFICADA'")
    )
    salida: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    regreso: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tiempo_min: Mapped[int] = mapped_column(Integer)
    peso_kg: Mapped[float] = mapped_column(Numeric(10, 2))
    volumen_m3: Mapped[float] = mapped_column(Numeric(10, 3))
    distancia_km: Mapped[float] = mapped_column(Double)
    co2_kg: Mapped[float] = mapped_column(Double)
    combustible_l: Mapped[float] = mapped_column(Double)
    costo_soles: Mapped[float] = mapped_column(Double)
    trazado: Mapped[WKBElement] = mapped_column(
        Geography(geometry_type="LINESTRING", srid=4326, spatial_index=False)
    )
    # RN-005 breaks: [{"inicio": ISO-8601, "fin": ISO-8601}, ...]
    descansos: Mapped[list[dict[str, str]]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # ECL-119: sequential reference on exactly this route's orders and vehicle.
    # Null only for routes stored before 0018; such routes cannot be closed.
    secuencial_distancia_km: Mapped[float | None] = mapped_column(Double)
    secuencial_co2_kg: Mapped[float | None] = mapped_column(Double)
    secuencial_combustible_l: Mapped[float | None] = mapped_column(Double)
    secuencial_costo_soles: Mapped[float | None] = mapped_column(Double)

    def __repr__(self) -> str:
        return "<Ruta>"


class ParadaRuta(Base):
    __tablename__ = "parada_ruta"
    __table_args__ = (
        CheckConstraint("secuencia > 0", name="ck_parada_ruta_secuencia"),
        CheckConstraint(
            f"estado IN ({sql_in(ESTADOS_PARADA)})", name="ck_parada_ruta_estado"
        ),
        CheckConstraint(
            "estado <> 'ATENDIDA' OR atendida_en IS NOT NULL",
            name="ck_parada_ruta_atendida",
        ),
        UniqueConstraint("ruta_id", "secuencia", name="uq_parada_ruta_secuencia"),
        # An order is served at most once per optimization (not only per route).
        UniqueConstraint("optimizacion_id", "pedido_id", name="uq_parada_ruta_pedido"),
        ForeignKeyConstraint(
            ["ruta_id", "optimizacion_id"],
            ["ruta.ruta_id", "ruta.optimizacion_id"],
            name="fk_parada_ruta_ruta",
            ondelete="RESTRICT",
        ),
        Index("ix_parada_ruta_pedido", "pedido_id"),
    )

    parada_id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    ruta_id: Mapped[UUID] = mapped_column()
    optimizacion_id: Mapped[UUID] = mapped_column()
    pedido_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "pedido.pedido_id", name="fk_parada_ruta_pedido", ondelete="RESTRICT"
        )
    )
    secuencia: Mapped[int] = mapped_column(Integer)
    eta: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(12), server_default=text("'PENDIENTE'"))
    atendida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return "<ParadaRuta>"


class PedidoNoAsignado(Base):
    __tablename__ = "pedido_no_asignado"
    __table_args__ = (
        PrimaryKeyConstraint(
            "optimizacion_id", "pedido_id", name="pk_pedido_no_asignado"
        ),
        CheckConstraint(
            f"motivo IN ({sql_in(MOTIVOS_NO_ASIGNADO)})",
            name="ck_pedido_no_asignado_motivo",
        ),
    )

    optimizacion_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "optimizacion.optimizacion_id",
            name="fk_pedido_no_asignado_optimizacion",
            ondelete="RESTRICT",
        )
    )
    pedido_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "pedido.pedido_id", name="fk_pedido_no_asignado_pedido", ondelete="RESTRICT"
        )
    )
    motivo: Mapped[str] = mapped_column(String(20))

    def __repr__(self) -> str:
        return "<PedidoNoAsignado>"
