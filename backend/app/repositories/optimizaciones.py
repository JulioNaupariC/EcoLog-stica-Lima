"""ST-047 (ECL-96): storage of optimization runs, routes and stops.

Reads return plain rows (no ORM hydration) with only the columns the service
needs; coordinates come out of PostGIS as numbers. Writes add whole runs: a
completed result is inserted in one transaction with its routes, stops and
unassigned orders, so a run is never published half-written.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import RowMapping, cast, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.conductor import Conductor
from app.models.pedido import Pedido
from app.models.ruta import Optimizacion, ParadaRuta, PedidoNoAsignado, Ruta
from app.models.usuario import Usuario
from app.models.vehiculo import Vehiculo


class OptimizacionStorageError(RuntimeError):
    """Sanitized storage failure."""


@dataclass(frozen=True)
class ConductorElegible:
    """Coarse candidate; only the route-specific assignment proves eligibility."""

    conductor_id: UUID
    disponible_desde: datetime | None
    disponible_hasta: datetime | None
    licencia_vigente_hasta: date


def _rows(session: Session, query: Any) -> list[RowMapping]:
    try:
        return list(session.execute(query).mappings())
    except SQLAlchemyError:
        raise OptimizacionStorageError("Optimization storage unavailable") from None


_PEDIDO_COLUMNAS = (
    Pedido.pedido_id,
    func.ST_Y(cast(Pedido.ubicacion, Geometry)).label("latitud"),
    func.ST_X(cast(Pedido.ubicacion, Geometry)).label("longitud"),
    Pedido.peso_kg,
    Pedido.volumen_m3,
    Pedido.ventana_inicio,
    Pedido.ventana_fin,
    Pedido.prioridad,
    Pedido.estado,
)


class OptimizacionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # --- selection ------------------------------------------------------
    def pedidos_por_id(self, ids: Sequence[UUID]) -> list[RowMapping]:
        return _rows(
            self._session,
            select(*_PEDIDO_COLUMNAS)
            .where(Pedido.pedido_id.in_(ids))
            .order_by(Pedido.pedido_id),
        )

    def pedidos_pendientes(
        self, desde: datetime, hasta: datetime, limite: int
    ) -> list[RowMapping]:
        """PENDIENTE orders whose window starts in [desde, hasta)."""
        return _rows(
            self._session,
            select(*_PEDIDO_COLUMNAS)
            .where(Pedido.estado == "PENDIENTE")
            .where(Pedido.ventana_inicio >= desde)
            .where(Pedido.ventana_inicio < hasta)
            .order_by(Pedido.pedido_id)
            .limit(limite),
        )

    def vehiculos(self, ids: Sequence[UUID] | None, limite: int) -> list[Vehiculo]:
        query = select(Vehiculo).order_by(Vehiculo.placa, Vehiculo.vehiculo_id)
        if ids is None:
            query = query.where(Vehiculo.estado == "ACTIVO").limit(limite)
        else:
            query = query.where(Vehiculo.vehiculo_id.in_(ids))
        try:
            return list(self._session.scalars(query).all())
        except SQLAlchemyError:
            raise OptimizacionStorageError("Optimization storage unavailable") from None

    def conductores_candidatos(self) -> list[ConductorElegible]:
        """Active candidates, including expired/unavailable ones for diagnosis.

        ECL-79 checks licence expiry over every driving interval, availability
        over the full route and RN-005 after the engine supplies the timeline.
        """
        rows = _rows(
            self._session,
            select(
                Conductor.conductor_id,
                Conductor.disponible_desde,
                Conductor.disponible_hasta,
                Conductor.licencia_vigente_hasta,
            )
            .join(Usuario, Usuario.usuario_id == Conductor.usuario_id)
            .where(Conductor.estado == "ACTIVO")
            .where(Usuario.rol == "CONDUCTOR")
            .where(Usuario.estado == "ACTIVO")
            .order_by(Conductor.disponible_desde, Conductor.conductor_id),
        )
        return [ConductorElegible(**row) for row in rows]

    # --- writes ---------------------------------------------------------
    def crear(self, optimizacion: Optimizacion) -> None:
        try:
            self._session.add(optimizacion)
            self._session.flush()
        except SQLAlchemyError:
            raise OptimizacionStorageError("Optimization storage unavailable") from None

    def completar(
        self,
        optimizacion_id: UUID,
        valores: dict[str, Any],
        rutas: Sequence[tuple[Ruta, Sequence[ParadaRuta]]],
        no_asignados: Sequence[PedidoNoAsignado],
    ) -> None:
        try:
            self._session.execute(
                update(Optimizacion)
                .where(Optimizacion.optimizacion_id == optimizacion_id)
                .where(Optimizacion.estado == "EN_PROCESO")
                .values(**valores)
            )
            for ruta, paradas in rutas:
                self._session.add(ruta)
                self._session.flush()
                for parada in paradas:
                    parada.ruta_id = ruta.ruta_id
                    parada.optimizacion_id = optimizacion_id
                self._session.add_all(paradas)
            self._session.add_all(no_asignados)
            self._session.flush()
        except SQLAlchemyError:
            raise OptimizacionStorageError("Optimization storage unavailable") from None

    def fallar(self, optimizacion_id: UUID, error: str, cuando: datetime) -> None:
        try:
            self._session.execute(
                update(Optimizacion)
                .where(Optimizacion.optimizacion_id == optimizacion_id)
                .where(Optimizacion.estado == "EN_PROCESO")
                .values(estado="FALLIDA", error=error, finalizada_en=cuando)
            )
        except SQLAlchemyError:
            raise OptimizacionStorageError("Optimization storage unavailable") from None

    # --- reads ----------------------------------------------------------
    def obtener(self, optimizacion_id: UUID) -> Optimizacion | None:
        try:
            return self._session.get(Optimizacion, optimizacion_id)
        except SQLAlchemyError:
            raise OptimizacionStorageError("Optimization storage unavailable") from None

    def rutas_de(self, optimizacion_id: UUID) -> list[RowMapping]:
        return _rows(
            self._session,
            select(
                Ruta.ruta_id,
                Ruta.estado,
                Ruta.salida,
                Ruta.regreso,
                Ruta.tiempo_min,
                Ruta.peso_kg,
                Ruta.volumen_m3,
                Ruta.distancia_km,
                Ruta.co2_kg,
                Ruta.combustible_l,
                Ruta.costo_soles,
                Ruta.descansos,
                Ruta.motivo_sin_conductor,
                func.ST_AsGeoJSON(Ruta.trazado).label("trazado"),
                Vehiculo.vehiculo_id,
                Vehiculo.placa,
                Vehiculo.tipo,
                Conductor.conductor_id,
                Conductor.nombre.label("conductor_nombre"),
            )
            .join(Vehiculo, Vehiculo.vehiculo_id == Ruta.vehiculo_id)
            .outerjoin(Conductor, Conductor.conductor_id == Ruta.conductor_id)
            .where(Ruta.optimizacion_id == optimizacion_id)
            .order_by(Ruta.salida, Vehiculo.placa),
        )

    def paradas_de(self, optimizacion_id: UUID) -> list[RowMapping]:
        return _rows(
            self._session,
            select(
                ParadaRuta.parada_id,
                ParadaRuta.ruta_id,
                ParadaRuta.secuencia,
                ParadaRuta.pedido_id,
                ParadaRuta.eta,
                ParadaRuta.estado,
                func.ST_Y(cast(Pedido.ubicacion, Geometry)).label("latitud"),
                func.ST_X(cast(Pedido.ubicacion, Geometry)).label("longitud"),
                Pedido.ventana_inicio,
                Pedido.ventana_fin,
            )
            .join(Pedido, Pedido.pedido_id == ParadaRuta.pedido_id)
            .where(ParadaRuta.optimizacion_id == optimizacion_id)
            .order_by(ParadaRuta.ruta_id, ParadaRuta.secuencia),
        )

    def no_asignados_de(self, optimizacion_id: UUID) -> list[RowMapping]:
        return _rows(
            self._session,
            select(PedidoNoAsignado.pedido_id, PedidoNoAsignado.motivo)
            .where(PedidoNoAsignado.optimizacion_id == optimizacion_id)
            .order_by(PedidoNoAsignado.pedido_id),
        )

    def pagina(
        self, fecha: date | None, page: int, page_size: int
    ) -> tuple[list[Optimizacion], int]:
        query = select(Optimizacion)
        total_query = select(func.count()).select_from(Optimizacion)
        if fecha is not None:
            query = query.where(Optimizacion.fecha_operacion == fecha)
            total_query = total_query.where(Optimizacion.fecha_operacion == fecha)
        try:
            total = self._session.scalar(total_query) or 0
            items = self._session.scalars(
                query.order_by(
                    Optimizacion.solicitada_en.desc(), Optimizacion.optimizacion_id
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        except SQLAlchemyError:
            raise OptimizacionStorageError("Optimization storage unavailable") from None
        return list(items), total

    def totales(self, ids: Sequence[UUID]) -> dict[UUID, RowMapping]:
        """Per-run route totals for the listing, in one query."""
        if not ids:
            return {}
        rows = _rows(
            self._session,
            select(
                Ruta.optimizacion_id,
                func.count().label("rutas"),
                func.sum(Ruta.distancia_km).label("distancia_km"),
                func.sum(Ruta.co2_kg).label("co2_kg"),
                func.sum(Ruta.combustible_l).label("combustible_l"),
                func.sum(Ruta.costo_soles).label("costo_soles"),
            )
            .where(Ruta.optimizacion_id.in_(ids))
            .group_by(Ruta.optimizacion_id),
        )
        return {row["optimizacion_id"]: row for row in rows}

    def conteos(self, ids: Sequence[UUID]) -> dict[UUID, tuple[int, int]]:
        """(assigned stops, unassigned orders) per run."""
        if not ids:
            return {}
        asignados = _rows(
            self._session,
            select(ParadaRuta.optimizacion_id, func.count().label("n"))
            .where(ParadaRuta.optimizacion_id.in_(ids))
            .group_by(ParadaRuta.optimizacion_id),
        )
        omitidos = _rows(
            self._session,
            select(PedidoNoAsignado.optimizacion_id, func.count().label("n"))
            .where(PedidoNoAsignado.optimizacion_id.in_(ids))
            .group_by(PedidoNoAsignado.optimizacion_id),
        )
        a = {r["optimizacion_id"]: r["n"] for r in asignados}
        o = {r["optimizacion_id"]: r["n"] for r in omitidos}
        return {i: (a.get(i, 0), o.get(i, 0)) for i in ids}


def minutos_desde_medianoche(momento: datetime, medianoche: datetime) -> int:
    """Whole minutes from the operating day's local midnight (may exceed 1440)."""
    return int((momento - medianoche) // timedelta(minutes=1))


def a_float(valor: Decimal | float | None) -> float:
    return 0.0 if valor is None else float(valor)
