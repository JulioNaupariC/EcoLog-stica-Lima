"""Distance and travel-time matrices without external map services.

Great-circle (Haversine) distance multiplied by a detour factor approximates
the street network; travel time uses a configurable urban average speed. A
traffic provider can replace this module later without touching the solver.
"""

from math import asin, cos, radians, sin, sqrt

from app.optimizacion.modelo import Punto

RADIO_TIERRA_KM = 6371.0088


def haversine_km(a: Punto, b: Punto) -> float:
    lat1, lon1, lat2, lon2 = map(
        radians, (a.latitud, a.longitud, b.latitud, b.longitud)
    )
    h = (
        sin((lat2 - lat1) / 2) ** 2
        + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * RADIO_TIERRA_KM * asin(sqrt(h))


def matriz_km(puntos: list[Punto], factor_desvio: float) -> list[list[float]]:
    """Road-distance estimate in km between every pair of points."""
    n = len(puntos)
    matriz = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            km = haversine_km(puntos[i], puntos[j]) * factor_desvio
            matriz[i][j] = km
            matriz[j][i] = km
    return matriz


def minutos_viaje(km: float, velocidad_kmh: float) -> int:
    """Travel minutes rounded up so the plan is never optimistic."""
    if km <= 0:
        return 0
    minutos = km / velocidad_kmh * 60
    return int(minutos) + (0 if minutos == int(minutos) else 1)
