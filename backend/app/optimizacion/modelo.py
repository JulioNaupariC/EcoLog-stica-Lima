"""Typed input and output of the VRPTW optimizer (ECL-93 / ST-044).

Pure domain objects: no FastAPI, no database. Times are minutes from local
midnight (America/Lima) so the solver works with integers; the service layer
(ST-047) converts them to datetimes. Distances are kilometres, loads are
kilograms and cubic metres, exactly as stored in ``pedido`` and ``vehiculo``.
"""

from dataclasses import dataclass, field
from enum import Enum


class Prioridad(str, Enum):
    EXPRESS = "EXPRESS"
    ESTANDAR = "ESTANDAR"
    ECONOMICO = "ECONOMICO"


class MotivoNoAsignado(str, Enum):
    """RN-009: an unassigned order keeps an explicit reason."""

    SIN_UBICACION = "SIN_UBICACION"
    EXCEDE_CAPACIDAD = "EXCEDE_CAPACIDAD"
    VENTANA_INVIABLE = "VENTANA_INVIABLE"
    SIN_VEHICULO = "SIN_VEHICULO"


class EstadoSolucion(str, Enum):
    COMPLETADA = "COMPLETADA"
    SIN_SOLUCION = "SIN_SOLUCION"


@dataclass(frozen=True)
class Punto:
    latitud: float
    longitud: float


@dataclass(frozen=True)
class PedidoVRP:
    pedido_id: str
    ubicacion: Punto | None
    peso_kg: float
    volumen_m3: float
    ventana_inicio_min: int
    ventana_fin_min: int
    prioridad: Prioridad = Prioridad.ESTANDAR


@dataclass(frozen=True)
class VehiculoVRP:
    vehiculo_id: str
    capacidad_kg: float
    capacidad_m3: float
    rendimiento_km_l: float
    factor_co2_kg_km: float


@dataclass(frozen=True)
class Configuracion:
    """Solver parameters. Defaults are the spike's working assumptions.

    ``velocidad_kmh`` and ``factor_desvio`` approximate Lima urban travel
    without an external traffic API (Haversine distance x detour factor).
    ``jornada_max_min`` and the break rule implement RN-005 conservatively:
    service and waiting time count as driving time.
    """

    inicio_jornada_min: int = 8 * 60
    jornada_max_min: int = 8 * 60
    conduccion_continua_max_min: int = 4 * 60
    descanso_min: int = 60
    servicio_min: int = 5
    velocidad_kmh: float = 20.0
    factor_desvio: float = 1.35
    tiempo_limite_s: int = 20
    metaheuristica: bool = True


@dataclass(frozen=True)
class Problema:
    deposito: Punto
    pedidos: tuple[PedidoVRP, ...]
    vehiculos: tuple[VehiculoVRP, ...]
    configuracion: Configuracion = field(default_factory=Configuracion)


@dataclass(frozen=True)
class Metricas:
    distancia_km: float
    co2_kg: float
    combustible_l: float


@dataclass(frozen=True)
class Parada:
    """``eta_min`` is the planned start of service, inside the order window."""

    secuencia: int
    pedido_id: str
    eta_min: int


@dataclass(frozen=True)
class Descanso:
    inicio_min: int
    duracion_min: int


@dataclass(frozen=True)
class Ruta:
    vehiculo_id: str
    paradas: tuple[Parada, ...]
    salida_min: int
    regreso_min: int
    peso_kg: float
    volumen_m3: float
    metricas: Metricas
    descansos: tuple[Descanso, ...] = ()

    @property
    def duracion_min(self) -> int:
        return self.regreso_min - self.salida_min


@dataclass(frozen=True)
class NoAsignado:
    pedido_id: str
    motivo: MotivoNoAsignado


@dataclass(frozen=True)
class Comparacion:
    """Optimized routes against the sequential baseline on the same orders."""

    optimizada: Metricas
    secuencial: Metricas

    @staticmethod
    def _ahorro(base: float, nuevo: float) -> float | None:
        """BDD US-006 v1.0.0 (decisiones 4 y 7, RNF-011).

        Exact value, never rounded here: rounding is for presentation only.
        A zero baseline gives ``None`` ("No calculable"), never an invented 0 %.
        A worse optimized route keeps its negative sign.
        """
        if base == 0:
            return None
        return (base - nuevo) / base * 100

    @property
    def ahorro_distancia_pct(self) -> float | None:
        return self._ahorro(self.secuencial.distancia_km, self.optimizada.distancia_km)

    @property
    def ahorro_co2_pct(self) -> float | None:
        return self._ahorro(self.secuencial.co2_kg, self.optimizada.co2_kg)

    @property
    def ahorro_combustible_pct(self) -> float | None:
        return self._ahorro(
            self.secuencial.combustible_l, self.optimizada.combustible_l
        )


@dataclass(frozen=True)
class Solucion:
    estado: EstadoSolucion
    rutas: tuple[Ruta, ...]
    no_asignados: tuple[NoAsignado, ...]
    comparacion: Comparacion | None
    duracion_s: float
