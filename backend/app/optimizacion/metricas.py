"""Route metrics and the sequential baseline used to measure savings.

RN-013: emissions = distance x the vehicle's emission factor.
RN-011: fuel litres = distance / vehicle efficiency (the price is applied later
with the versioned parameters of EN-008, so this module returns litres).
"""

from collections.abc import Callable, Sequence

from app.optimizacion.modelo import Metricas, PedidoVRP, VehiculoVRP

DistanciaKm = Callable[[int, int], float]


def metricas_vehiculo(distancia_km: float, vehiculo: VehiculoVRP) -> Metricas:
    return Metricas(
        distancia_km=distancia_km,
        co2_kg=distancia_km * vehiculo.factor_co2_kg_km,
        combustible_l=distancia_km / vehiculo.rendimiento_km_l,
    )


def sumar(metricas: Sequence[Metricas]) -> Metricas:
    return Metricas(
        distancia_km=round(sum(m.distancia_km for m in metricas), 3),
        co2_kg=round(sum(m.co2_kg for m in metricas), 3),
        combustible_l=round(sum(m.combustible_l for m in metricas), 3),
    )


def _cabe(pedido: PedidoVRP, vehiculo: VehiculoVRP, kg: float, m3: float) -> bool:
    return (
        kg + pedido.peso_kg <= vehiculo.capacidad_kg
        and m3 + pedido.volumen_m3 <= vehiculo.capacidad_m3
    )


def ruta_secuencial(
    pedidos: Sequence[tuple[int, PedidoVRP]],
    vehiculos: Sequence[VehiculoVRP],
    distancia: DistanciaKm,
) -> Metricas:
    """Manual practice before EcoLogística: orders in registration order.

    Each vehicle, in fleet order, loads the next orders until the next one no
    longer fits, drives depot -> orders in that order -> depot, and hands over
    to the next vehicle (cycling through the fleet when needed). Windows are
    ignored, as in the manual process. ``pedidos`` pairs each order with its
    node index in ``distancia`` (the depot is node 0).
    """
    if not pedidos or not vehiculos:
        return Metricas(0.0, 0.0, 0.0)
    tramos: list[Metricas] = []
    actual = 0
    viaje: list[int] = []
    kg = m3 = 0.0

    def cerrar() -> None:
        nodos = [0, *viaje, 0]
        km = sum(distancia(a, b) for a, b in zip(nodos, nodos[1:], strict=False))
        tramos.append(metricas_vehiculo(km, vehiculos[actual]))

    for nodo, pedido in pedidos:
        intentos = 0
        while not _cabe(pedido, vehiculos[actual], kg, m3):
            if viaje:
                cerrar()
                viaje, kg, m3 = [], 0.0, 0.0
            else:
                intentos += 1
                if intentos > len(vehiculos):
                    raise ValueError("El pedido no cabe en ningún vehículo")
            actual = (actual + 1) % len(vehiculos)
        viaje.append(nodo)
        kg += pedido.peso_kg
        m3 += pedido.volumen_m3
    if viaje:
        cerrar()
    return sumar(tramos)
