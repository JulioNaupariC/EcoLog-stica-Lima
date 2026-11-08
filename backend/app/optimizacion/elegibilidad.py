"""ECL-79: planned driving, separated from service, waiting and explicit rest.

Travel uses the engine's distance/time assumptions. Within each ETA envelope,
drive as early as possible, interrupting travel at declared breaks. Service
and ordinary waiting never count as driving or automatically become rest.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.optimizacion.distancias import haversine_km, minutos_viaje
from app.optimizacion.modelo import Problema, Ruta

Intervalo = tuple[datetime, datetime]


@dataclass(frozen=True)
class PlanRuta:
    salida: datetime
    regreso: datetime
    conduccion: tuple[Intervalo, ...]
    descansos: tuple[Intervalo, ...] = ()


def cumple_rn005(plan: PlanRuta) -> bool:
    """At most 8 h driving and 4 h between explicit rests of at least 1 h."""
    if plan.regreso <= plan.salida:
        return False
    for intervals in (plan.conduccion, plan.descansos):
        anterior = plan.salida
        for inicio, fin in intervals:
            if inicio < anterior or fin <= inicio or fin > plan.regreso:
                return False
            anterior = fin
    total = continuo = timedelta()
    anterior = plan.salida
    for inicio, fin in plan.conduccion:
        if any(a < fin and b > inicio for a, b in plan.descansos):
            return False
        if any(
            a >= anterior and b <= inicio and b - a >= timedelta(hours=1)
            for a, b in plan.descansos
        ):
            continuo = timedelta()
        total += fin - inicio
        continuo += fin - inicio
        if total > timedelta(hours=8) or continuo > timedelta(hours=4):
            return False
        anterior = fin
    return True


def _viajar(
    inicio: int, minutos: int, limite: int, descansos: list[tuple[int, int]]
) -> list[tuple[int, int]] | None:
    tramos = []
    momento = inicio
    for desde, hasta in descansos:
        if hasta <= momento or minutos == 0:
            continue
        if desde > momento:
            avance = min(minutos, desde - momento)
            tramos.append((momento, momento + avance))
            momento += avance
            minutos -= avance
        if minutos:
            momento = max(momento, hasta)
    if minutos:
        tramos.append((momento, momento + minutos))
        momento += minutos
    return None if momento > limite else tramos


def plan_de_ruta(problema: Problema, ruta: Ruta, base: datetime) -> PlanRuta | None:
    """Build a feasible driving timeline within the solver's ETA/break slots.

    A malformed or impossible timeline cannot authorize an assignment. The
    caller keeps the generated route without a driver instead of discarding it.
    """
    c = problema.configuracion
    pausas = sorted(
        (d.inicio_min, d.inicio_min + d.duracion_min) for d in ruta.descansos
    )
    anterior = ruta.salida_min
    for inicio, fin in pausas:
        if inicio < anterior or fin <= inicio or fin > ruta.regreso_min:
            return None
        anterior = fin
    pedidos = {p.pedido_id: p for p in problema.pedidos}
    punto = problema.deposito
    momento = ruta.salida_min
    conduccion: list[tuple[int, int]] = []
    for parada in ruta.paradas:
        pedido = pedidos.get(parada.pedido_id)
        if pedido is None or pedido.ubicacion is None or parada.eta_min < momento:
            return None
        fin_servicio = parada.eta_min + c.servicio_min
        if fin_servicio > ruta.regreso_min or any(
            a < fin_servicio and b > parada.eta_min for a, b in pausas
        ):
            return None
        minutos = minutos_viaje(
            haversine_km(punto, pedido.ubicacion) * c.factor_desvio, c.velocidad_kmh
        )
        tramos = _viajar(momento, minutos, parada.eta_min, pausas)
        if tramos is None:
            return None
        conduccion.extend(tramos)
        momento, punto = fin_servicio, pedido.ubicacion
    regreso = minutos_viaje(
        haversine_km(punto, problema.deposito) * c.factor_desvio, c.velocidad_kmh
    )
    tramos = _viajar(momento, regreso, ruta.regreso_min, pausas)
    if tramos is None:
        return None
    conduccion.extend(tramos)

    def instante(minutos: int) -> datetime:
        return base + timedelta(minutes=minutos)

    return PlanRuta(
        salida=instante(ruta.salida_min),
        regreso=instante(ruta.regreso_min),
        conduccion=tuple((instante(a), instante(b)) for a, b in conduccion),
        descansos=tuple((instante(a), instante(b)) for a, b in pausas),
    )
