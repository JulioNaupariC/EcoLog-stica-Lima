"""Reproducible synthetic scenarios for the spike and the performance tests.

Synthetic data, not company data: coordinates are random points inside rough
boxes of the four pilot districts, and the fleet figures are typical values
for the vehicle types allowed by ``vehiculo.tipo``. Emission factors derive
from 2.68 kg CO2/L (diesel) and 2.31 kg CO2/L (gasoline) divided by the
efficiency; EN-008 replaces them with versioned, sourced parameters.
"""

from random import Random

from app.optimizacion.modelo import (
    Configuracion,
    PedidoVRP,
    Prioridad,
    Problema,
    Punto,
    VehiculoVRP,
)

# (lat_min, lat_max, lon_min, lon_max), approximate urban area of each district.
DISTRITOS = {
    "San Juan de Lurigancho": (-12.000, -11.950, -77.015, -76.975),
    "El Agustino": (-12.055, -12.030, -77.000, -76.980),
    "Santa Anita": (-12.060, -12.035, -76.980, -76.955),
    "Ate": (-12.060, -12.020, -76.950, -76.890),
}
DEPOSITO = Punto(-12.0470, -76.9680)  # assumed depot in Santa Anita

# tipo: (capacidad_kg, capacidad_m3, rendimiento_km_l, factor_co2_kg_km)
FLOTA = {
    "FURGON": (1500.0, 12.0, 9.0, round(2.68 / 9.0, 5)),
    "CAMIONETA": (800.0, 4.0, 11.0, round(2.68 / 11.0, 5)),
    "MOTO": (40.0, 0.15, 35.0, round(2.31 / 35.0, 5)),
}
MEZCLA_FLOTA = ("FURGON",) * 6 + ("CAMIONETA",) * 7 + ("MOTO",) * 2
PRIORIDADES = (
    (Prioridad.EXPRESS, 0.15),
    (Prioridad.ESTANDAR, 0.60),
    (Prioridad.ECONOMICO, 0.25),
)


def flota(cantidad: int) -> tuple[VehiculoVRP, ...]:
    vehiculos = []
    for i in range(cantidad):
        tipo = MEZCLA_FLOTA[i % len(MEZCLA_FLOTA)]
        kg, m3, rendimiento, factor = FLOTA[tipo]
        vehiculos.append(
            VehiculoVRP(f"V{i + 1:02d}-{tipo}", kg, m3, rendimiento, factor)
        )
    return tuple(vehiculos)


def _prioridad(azar: Random) -> Prioridad:
    x = azar.random()
    acumulado = 0.0
    for prioridad, peso in PRIORIDADES:
        acumulado += peso
        if x < acumulado:
            return prioridad
    return Prioridad.ESTANDAR


def pedidos(
    cantidad: int, azar: Random, inicio_jornada_min: int = 8 * 60
) -> tuple[PedidoVRP, ...]:
    nombres = sorted(DISTRITOS)
    resultado = []
    for i in range(cantidad):
        lat_min, lat_max, lon_min, lon_max = DISTRITOS[azar.choice(nombres)]
        peso = round(min(azar.lognormvariate(3.2, 0.8), 400.0), 2)
        inicio = inicio_jornada_min + 30 + azar.randrange(0, 360, 15)
        resultado.append(
            PedidoVRP(
                pedido_id=f"P{i + 1:03d}",
                ubicacion=Punto(
                    round(azar.uniform(lat_min, lat_max), 6),
                    round(azar.uniform(lon_min, lon_max), 6),
                ),
                peso_kg=peso,
                volumen_m3=round(peso * azar.uniform(0.003, 0.009), 3),
                ventana_inicio_min=inicio,
                ventana_fin_min=inicio + azar.choice((90, 120, 180, 240)),
                prioridad=_prioridad(azar),
            )
        )
    return tuple(resultado)


def inviables(inicio_jornada_min: int = 8 * 60) -> tuple[PedidoVRP, ...]:
    """Two orders that must come back unassigned with their reason."""
    lat_min, lat_max, lon_min, lon_max = DISTRITOS["Ate"]
    punto = Punto((lat_min + lat_max) / 2, (lon_min + lon_max) / 2)
    return (
        PedidoVRP(
            "X-CAPACIDAD",
            punto,
            3500.0,
            20.0,
            inicio_jornada_min + 60,
            inicio_jornada_min + 300,
            Prioridad.EXPRESS,
        ),
        PedidoVRP(
            "X-VENTANA",
            punto,
            10.0,
            0.05,
            inicio_jornada_min - 180,
            inicio_jornada_min - 120,
            Prioridad.EXPRESS,
        ),
    )


def escenario(
    total_pedidos: int,
    total_vehiculos: int,
    semilla: int,
    configuracion: Configuracion | None = None,
    con_inviables: bool = True,
) -> Problema:
    """``total_pedidos`` includes the two infeasible orders when requested."""
    config = configuracion or Configuracion()
    azar = Random(semilla)
    extra = inviables(config.inicio_jornada_min) if con_inviables else ()
    normales = pedidos(total_pedidos - len(extra), azar, config.inicio_jornada_min)
    return Problema(
        deposito=DEPOSITO,
        pedidos=normales + extra,
        vehiculos=flota(total_vehiculos),
        configuracion=config,
    )
