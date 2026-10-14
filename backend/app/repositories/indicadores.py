"""Operational aggregates computed in SQL (ECL-25 / RNF-012).

Three fixed statements regardless of row counts: no rows are loaded into
Python, only COUNT/SUM with FILTER and one GROUP BY over a bounded domain.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Select, and_, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.conductor import Conductor
from app.models.pedido import Pedido
from app.models.usuario import Usuario
from app.models.vehiculo import Vehiculo


class IndicatorStorageError(RuntimeError):
    """Sanitized indicator storage failure."""


@dataclass(frozen=True)
class OperationalCounts:
    vehiculos_total: int
    vehiculos_activos: int
    capacidad_kg_activa: Decimal
    conductores_total: int
    conductores_habilitados: int
    pedidos: list[tuple[str, str, int]]


def eligible_driver(now: datetime):
    """SQL form of ``habilitado_asignacion`` in ``services.conductores._response``.

    ``now`` is America/Lima: the licence is valid through its date in Lima and
    the availability window must not have ended.
    """
    return and_(
        Conductor.estado == "ACTIVO",
        Usuario.rol == "CONDUCTOR",
        Usuario.estado == "ACTIVO",
        Conductor.licencia_vigente_hasta >= now.date(),
        Conductor.disponible_desde.is_not(None),
        Conductor.disponible_hasta.is_not(None),
        Conductor.disponible_hasta > now,
    )


def aggregate_statements(now: datetime) -> dict[str, Select]:
    active = Vehiculo.estado == "ACTIVO"
    return {
        "vehiculos": select(
            func.count().label("total"),
            func.count().filter(active).label("activos"),
            func.coalesce(func.sum(Vehiculo.capacidad_kg).filter(active), 0).label(
                "capacidad_kg_activa"
            ),
        ).select_from(Vehiculo),
        "conductores": select(
            func.count().label("total"),
            func.count().filter(eligible_driver(now)).label("habilitados"),
        )
        .select_from(Conductor)
        .outerjoin(Usuario, Usuario.usuario_id == Conductor.usuario_id),
        "pedidos": select(Pedido.estado, Pedido.prioridad, func.count())
        .group_by(Pedido.estado, Pedido.prioridad)
        .order_by(Pedido.estado, Pedido.prioridad),
    }


class IndicadoresRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def operational_counts(self, now: datetime) -> OperationalCounts:
        statements = aggregate_statements(now)
        try:
            vehicles = self._session.execute(statements["vehiculos"]).one()
            drivers = self._session.execute(statements["conductores"]).one()
            orders = self._session.execute(statements["pedidos"]).all()
        except SQLAlchemyError:
            raise IndicatorStorageError("Indicator storage unavailable") from None
        return OperationalCounts(
            vehiculos_total=vehicles.total,
            vehiculos_activos=vehicles.activos,
            capacidad_kg_activa=Decimal(vehicles.capacidad_kg_activa),
            conductores_total=drivers.total,
            conductores_habilitados=drivers.habilitados,
            pedidos=[(estado, prioridad, count) for estado, prioridad, count in orders],
        )
