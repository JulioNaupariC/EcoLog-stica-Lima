"""Operational indicators for the home dashboard (ECL-25 / RNF-012).

Freshness decision: the figures inform the home page, not an operational
decision, so a private 30-second cache bounds staleness while avoiding repeated
aggregation on navigation. ``generado_en`` tells the reader how old they are.
"""

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.repositories.indicadores import IndicadoresRepository, IndicatorStorageError
from app.schemas.indicadores import (
    ConductoresIndicadores,
    IndicadoresOperacionResponse,
    PedidosIndicadores,
    VehiculosIndicadores,
)

LIMA = ZoneInfo("America/Lima")
VIGENCIA_SEGUNDOS = 30
PRIORIDADES = ("EXPRESS", "ESTANDAR", "ECONOMICO")


class IndicatorsUnavailable(RuntimeError):
    """Sanitized operational indicator failure."""


def _now() -> datetime:
    return datetime.now(LIMA)


class IndicadoresService:
    def __init__(
        self,
        factory: sessionmaker[Session],
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self._factory = factory
        self._clock = clock

    def operational(self) -> IndicadoresOperacionResponse:
        now = self._clock()
        try:
            with self._factory() as session:
                counts = IndicadoresRepository(session).operational_counts(now)
        except (IndicatorStorageError, SQLAlchemyError):
            raise IndicatorsUnavailable("Indicators unavailable") from None
        by_state: dict[str, int] = {}
        by_priority = dict.fromkeys(PRIORIDADES, 0)
        for estado, prioridad, count in counts.pedidos:
            by_state[estado] = by_state.get(estado, 0) + count
            by_priority[prioridad] = by_priority.get(prioridad, 0) + count
        return IndicadoresOperacionResponse(
            generado_en=now,
            vigencia_segundos=VIGENCIA_SEGUNDOS,
            vehiculos=VehiculosIndicadores(
                total=counts.vehiculos_total,
                activos=counts.vehiculos_activos,
                capacidad_kg_activa=counts.capacidad_kg_activa,
            ),
            conductores=ConductoresIndicadores(
                total=counts.conductores_total,
                habilitados_asignacion=counts.conductores_habilitados,
                no_habilitados=counts.conductores_total
                - counts.conductores_habilitados,
            ),
            pedidos=PedidosIndicadores(
                total=sum(by_state.values()),
                por_estado=by_state,
                por_prioridad=by_priority,
            ),
        )
