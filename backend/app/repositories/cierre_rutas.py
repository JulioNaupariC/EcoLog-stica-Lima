"""ECL-119: storage for stop outcomes, route closure and the US-009 aggregate.

Writes lock the route row (``FOR UPDATE``) so two Operators cannot close the
same route twice or record a stop while it is being closed. Reads return plain
aggregates computed in SQL; no geometry or personal data leaves the database.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import RowMapping, and_, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.pedido import Pedido
from app.models.ruta import Optimizacion, ParadaRuta, Ruta


class CierreStorageError(RuntimeError):
    """Sanitized storage failure."""


def _cerradas(desde: datetime, hasta: datetime) -> Any:
    """Closed routes whose closing instant is in [desde, hasta)."""
    return and_(
        Ruta.estado == "CERRADA", Ruta.cerrada_en >= desde, Ruta.cerrada_en < hasta
    )


class CierreRutaRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _run(self, consulta: Any) -> Any:
        try:
            return self._session.execute(consulta)
        except SQLAlchemyError:
            raise CierreStorageError("Route storage unavailable") from None

    # --- writes ---------------------------------------------------------
    def ruta(self, ruta_id: UUID) -> Ruta | None:
        return self._run(
            select(Ruta).where(Ruta.ruta_id == ruta_id).with_for_update()
        ).scalar_one_or_none()

    def parada(self, ruta_id: UUID, parada_id: UUID) -> ParadaRuta | None:
        return self._run(
            select(ParadaRuta)
            .where(ParadaRuta.parada_id == parada_id)
            .where(ParadaRuta.ruta_id == ruta_id)
            .with_for_update()
        ).scalar_one_or_none()

    def conteo_paradas(self, ruta_id: UUID) -> dict[str, int]:
        filas = self._run(
            select(ParadaRuta.estado, func.count())
            .where(ParadaRuta.ruta_id == ruta_id)
            .group_by(ParadaRuta.estado)
        ).all()
        return {estado: n for estado, n in filas}

    def guardar(self) -> None:
        try:
            self._session.flush()
        except SQLAlchemyError:
            raise CierreStorageError("Route storage unavailable") from None

    # --- US-009 aggregate -------------------------------------------------
    def totales(self, desde: datetime, hasta: datetime) -> RowMapping:
        return (
            self._run(
                select(
                    func.count().label("rutas"),
                    func.count(Ruta.secuencial_distancia_km).label("con_referencia"),
                    func.sum(Ruta.distancia_km).label("distancia_km"),
                    func.sum(Ruta.co2_kg).label("co2_kg"),
                    func.sum(Ruta.combustible_l).label("combustible_l"),
                    func.sum(Ruta.costo_soles).label("costo_soles"),
                    func.sum(Ruta.secuencial_distancia_km).label("sec_distancia_km"),
                    func.sum(Ruta.secuencial_co2_kg).label("sec_co2_kg"),
                    func.sum(Ruta.secuencial_combustible_l).label("sec_combustible_l"),
                    func.sum(Ruta.secuencial_costo_soles).label("sec_costo_soles"),
                ).where(_cerradas(desde, hasta))
            )
            .mappings()
            .one()
        )

    def versiones(self, desde: datetime, hasta: datetime) -> list[str]:
        filas = self._run(
            select(Optimizacion.parametros_version)
            .join(Ruta, Ruta.optimizacion_id == Optimizacion.optimizacion_id)
            .where(_cerradas(desde, hasta))
            .where(Optimizacion.parametros_version.is_not(None))
            .distinct()
            .order_by(Optimizacion.parametros_version)
        ).scalars()
        return list(filas)

    def cumplimiento(self, desde: datetime, hasta: datetime) -> tuple[int, int]:
        """(ATENDIDA inside its window by real time, terminal stops)."""
        a_tiempo = and_(
            ParadaRuta.estado == "ATENDIDA",
            ParadaRuta.atendida_en >= Pedido.ventana_inicio,
            ParadaRuta.atendida_en <= Pedido.ventana_fin,
        )
        fila = self._run(
            select(
                func.count().filter(a_tiempo),
                func.count().filter(ParadaRuta.estado.in_(("ATENDIDA", "NO_ATENDIDA"))),
            )
            .select_from(ParadaRuta)
            .join(Ruta, Ruta.ruta_id == ParadaRuta.ruta_id)
            .join(Pedido, Pedido.pedido_id == ParadaRuta.pedido_id)
            .where(_cerradas(desde, hasta))
        ).one()
        return int(fila[0]), int(fila[1])
