"""ECL-94 (ST-045): API contract for route optimization and sustainability.

Published before the optimizer (ST-047) so the map (US-008) and the dashboard
(US-009) can be built in parallel. While ``simulado`` is true the data comes
from versioned fixtures; ST-047 replaces them without changing these shapes.
Distances in km, emissions in kg CO2, fuel in litres, money in soles (PEN),
times in America/Lima with offset, coordinates WGS84 (SRID 4326).
"""

from datetime import date
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    model_validator,
)

MAX_PEDIDOS = 150
MAX_VEHICULOS = 15
PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100

Latitud = Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
Longitud = Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]
# BDD US-006 v1.0.0, decision 4: savings may be negative without an artificial
# floor (a worse route keeps its sign); at most 100 % is saved.
Porcentaje = Annotated[float, Field(le=100, allow_inf_nan=False)]


class EstadoOptimizacion(str, Enum):
    EN_PROCESO = "EN_PROCESO"
    COMPLETADA = "COMPLETADA"
    FALLIDA = "FALLIDA"


class EstadoRuta(str, Enum):
    PLANIFICADA = "PLANIFICADA"
    EN_CURSO = "EN_CURSO"
    CERRADA = "CERRADA"


class EstadoParada(str, Enum):
    PENDIENTE = "PENDIENTE"
    ATENDIDA = "ATENDIDA"
    NO_ATENDIDA = "NO_ATENDIDA"


class MotivoNoAsignado(str, Enum):
    """RN-009: an unassigned order always keeps an explicit reason."""

    SIN_UBICACION = "SIN_UBICACION"
    EXCEDE_CAPACIDAD = "EXCEDE_CAPACIDAD"
    VENTANA_INVIABLE = "VENTANA_INVIABLE"
    SIN_VEHICULO = "SIN_VEHICULO"


class MotivoSinConductor(str, Enum):
    """ECL-79: a route may have no eligible driver without being invalid."""

    SIN_CONDUCTOR_ELEGIBLE = "SIN_CONDUCTOR_ELEGIBLE"


# --- requests ----------------------------------------------------------------


class OptimizacionSolicitud(BaseModel):
    """Omitted lists mean every PENDIENTE order of the date / every ACTIVO vehicle."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    fecha_operacion: date
    pedido_ids: list[UUID] | None = Field(
        default=None, min_length=1, max_length=MAX_PEDIDOS
    )
    vehiculo_ids: list[UUID] | None = Field(
        default=None, min_length=1, max_length=MAX_VEHICULOS
    )

    @model_validator(mode="after")
    def sin_repetidos(self) -> "OptimizacionSolicitud":
        for ids in (self.pedido_ids, self.vehiculo_ids):
            if ids is not None and len(set(ids)) != len(ids):
                raise ValueError("Identificadores repetidos")
        return self


# --- responses ---------------------------------------------------------------


class Metricas(BaseModel):
    distancia_km: NonNegativeFloat
    co2_kg: NonNegativeFloat
    combustible_l: NonNegativeFloat
    costo_soles: NonNegativeFloat


class Ahorro(BaseModel):
    """Percentage saved against the sequential route on the same orders.

    ``None`` when the sequential baseline is zero ("No calculable"): the value
    is never invented as 0 % (BDD US-006 v1.0.0, R10 and decision 4).
    """

    distancia: Porcentaje | None
    co2: Porcentaje | None
    combustible: Porcentaje | None
    costo: Porcentaje | None


class Resumen(BaseModel):
    rutas: NonNegativeInt
    pedidos_asignados: NonNegativeInt
    pedidos_no_asignados: NonNegativeInt
    optimizada: Metricas
    secuencial: Metricas
    ahorro_pct: Ahorro
    cumplimiento_ventanas_pct: Annotated[float, Field(ge=0, le=100)]

    @model_validator(mode="after")
    def ahorro_nulo_solo_con_base_cero(self) -> "Resumen":
        """A percentage is null exactly when its sequential baseline is zero."""
        pares = (
            ("distancia", self.secuencial.distancia_km),
            ("co2", self.secuencial.co2_kg),
            ("combustible", self.secuencial.combustible_l),
            ("costo", self.secuencial.costo_soles),
        )
        for campo, base in pares:
            if (getattr(self.ahorro_pct, campo) is None) != (base == 0):
                raise ValueError(
                    f"ahorro_pct.{campo} es null solo si la base secuencial es 0"
                )
        return self


class OptimizacionAceptada(BaseModel):
    optimizacion_id: UUID
    estado: EstadoOptimizacion
    solicitada_en: AwareDatetime
    simulado: bool


class VehiculoRef(BaseModel):
    vehiculo_id: UUID
    placa: str
    tipo: Literal["CAMIONETA", "FURGON", "MOTO"]


class ConductorRef(BaseModel):
    """Identifier and name only: no DNI, phone or licence."""

    conductor_id: UUID
    nombre: str


class LineString(BaseModel):
    """GeoJSON geometry; each position is [longitud, latitud]."""

    type: Literal["LineString"]
    coordinates: list[tuple[Longitud, Latitud]] = Field(min_length=2)


class Parada(BaseModel):
    parada_id: UUID
    secuencia: Annotated[int, Field(ge=1)]
    pedido_id: UUID
    latitud: Latitud
    longitud: Longitud
    ventana_inicio: AwareDatetime
    ventana_fin: AwareDatetime
    eta: AwareDatetime
    estado: EstadoParada


class Descanso(BaseModel):
    """RN-005: one hour after four continuous hours."""

    inicio: AwareDatetime
    fin: AwareDatetime


class Ruta(BaseModel):
    ruta_id: UUID
    vehiculo: VehiculoRef
    conductor: ConductorRef | None
    motivo_sin_conductor: MotivoSinConductor | None = None
    estado: EstadoRuta
    salida: AwareDatetime
    regreso: AwareDatetime
    tiempo_min: NonNegativeInt
    peso_kg: NonNegativeFloat
    volumen_m3: NonNegativeFloat
    metricas: Metricas
    trazado: LineString
    paradas: list[Parada] = Field(min_length=1)
    descansos: list[Descanso]


class NoAsignado(BaseModel):
    pedido_id: UUID
    motivo: MotivoNoAsignado


class OptimizacionDetalle(BaseModel):
    optimizacion_id: UUID
    estado: EstadoOptimizacion
    fecha_operacion: date
    solicitada_en: AwareDatetime
    finalizada_en: AwareDatetime | None
    duracion_s: NonNegativeFloat | None
    parametros_version: str | None
    simulado: bool
    resumen: Resumen | None
    rutas: list[Ruta]
    no_asignados: list[NoAsignado]
    error: str | None


class OptimizacionItem(BaseModel):
    optimizacion_id: UUID
    estado: EstadoOptimizacion
    fecha_operacion: date
    solicitada_en: AwareDatetime
    resumen: Resumen | None


class OptimizacionPage(BaseModel):
    items: list[OptimizacionItem]
    page: Annotated[int, Field(ge=1)]
    page_size: Annotated[int, Field(ge=1, le=PAGE_SIZE_MAX)]
    total: NonNegativeInt
    simulado: bool


class Periodo(BaseModel):
    desde: date
    hasta: date


class AhorroPeriodo(BaseModel):
    distancia_km: float
    co2_kg: float
    combustible_l: float
    costo_soles: float
    pct: Porcentaje | None


class IndicadoresSostenibilidad(BaseModel):
    """US-009. Without closed routes every indicator is null, never zero."""

    periodo: Periodo
    con_datos: bool
    rutas_cerradas: NonNegativeInt
    distancia_km: NonNegativeFloat | None
    co2_kg: NonNegativeFloat | None
    combustible_l: NonNegativeFloat | None
    costo_soles: NonNegativeFloat | None
    ahorro_vs_secuencial: AhorroPeriodo | None
    cumplimiento_ventanas_pct: Annotated[float, Field(ge=0, le=100)] | None
    parametros_versiones: list[str]
    simulado: bool

    @model_validator(mode="after")
    def nulos_sin_datos(self) -> "IndicadoresSostenibilidad":
        valores = (
            self.distancia_km,
            self.co2_kg,
            self.combustible_l,
            self.costo_soles,
            self.ahorro_vs_secuencial,
            self.cumplimiento_ventanas_pct,
        )
        if self.con_datos and any(v is None for v in valores):
            raise ValueError("Con datos, todos los indicadores tienen valor")
        if not self.con_datos and (
            self.rutas_cerradas or any(v is not None for v in valores)
        ):
            raise ValueError("Sin datos, los indicadores van en null")
        return self


# --- ECL-119: stop outcomes and route closure (US-009) -------------------------


class EstadoFinalParada(str, Enum):
    ATENDIDA = "ATENDIDA"
    NO_ATENDIDA = "NO_ATENDIDA"


class ResultadoParadaSolicitud(BaseModel):
    """Outcome the Operator records; ATENDIDA needs the real service time."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    estado: EstadoFinalParada
    atendida_en: AwareDatetime | None = None

    @model_validator(mode="after")
    def hora_si_atendida(self) -> "ResultadoParadaSolicitud":
        if self.estado is EstadoFinalParada.ATENDIDA and self.atendida_en is None:
            raise ValueError("ATENDIDA requiere atendida_en")
        return self


class ParadaActualizada(BaseModel):
    parada_id: UUID
    ruta_id: UUID
    estado: EstadoParada
    atendida_en: AwareDatetime | None
    ruta_estado: EstadoRuta


class RutaCerrada(BaseModel):
    ruta_id: UUID
    estado: EstadoRuta
    cerrada_en: AwareDatetime
    paradas_atendidas: NonNegativeInt
    paradas_no_atendidas: NonNegativeInt
