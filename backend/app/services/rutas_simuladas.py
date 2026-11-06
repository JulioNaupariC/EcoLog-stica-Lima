"""ECL-94 (ST-045): simulated route data served until ST-047 lands.

The responses come from versioned JSON fixtures in ``app/simulacion/rutas``,
validated against the published schemas when loaded. Every response says
``simulado: true``; ST-047 swaps this service for the real optimizer without
changing the contract. Nothing here reads or writes the database.
"""

from datetime import date
from functools import cache
from pathlib import Path
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel

from app.schemas.rutas import (
    EstadoOptimizacion,
    IndicadoresSostenibilidad,
    OptimizacionAceptada,
    OptimizacionDetalle,
    OptimizacionPage,
    OptimizacionSolicitud,
    Periodo,
)

FIXTURES = Path(__file__).resolve().parent.parent / "simulacion" / "rutas"
Modelo = TypeVar("Modelo", bound=BaseModel)
DETALLES = (
    "optimizacion-completada.json",
    "optimizacion-en-proceso.json",
    "optimizacion-fallida.json",
)


def _cargar(nombre: str, modelo: type[Modelo]) -> Modelo:
    return modelo.model_validate_json((FIXTURES / nombre).read_text(encoding="utf-8"))


@cache
def detalles() -> dict[UUID, OptimizacionDetalle]:
    cargados = (_cargar(nombre, OptimizacionDetalle) for nombre in DETALLES)
    return {d.optimizacion_id: d for d in cargados}


@cache
def _sostenibilidad() -> IndicadoresSostenibilidad:
    return _cargar("sostenibilidad-con-datos.json", IndicadoresSostenibilidad)


def completada() -> OptimizacionDetalle:
    return next(
        d for d in detalles().values() if d.estado is EstadoOptimizacion.COMPLETADA
    )


class RutasSimuladasService:
    def solicitar(self, _solicitud: OptimizacionSolicitud) -> OptimizacionAceptada:
        """Accepts any valid request and points to the completed example."""
        ejemplo = completada()
        return OptimizacionAceptada(
            optimizacion_id=ejemplo.optimizacion_id,
            estado=EstadoOptimizacion.EN_PROCESO,
            solicitada_en=ejemplo.solicitada_en,
            simulado=True,
        )

    def detalle(self, optimizacion_id: UUID) -> OptimizacionDetalle | None:
        return detalles().get(optimizacion_id)

    def listar(self, fecha: date | None, page: int, page_size: int) -> OptimizacionPage:
        todos = sorted(
            (d for d in detalles().values() if fecha in (None, d.fecha_operacion)),
            key=lambda d: d.solicitada_en,
            reverse=True,
        )
        inicio = (page - 1) * page_size
        return OptimizacionPage.model_validate(
            {
                "items": [
                    d.model_dump(
                        include={
                            "optimizacion_id",
                            "estado",
                            "fecha_operacion",
                            "solicitada_en",
                            "resumen",
                        }
                    )
                    for d in todos[inicio : inicio + page_size]
                ],
                "page": page,
                "page_size": page_size,
                "total": len(todos),
                "simulado": True,
            }
        )

    def sostenibilidad(self, desde: date, hasta: date) -> IndicadoresSostenibilidad:
        """Data only when the period overlaps the example period; else no data."""
        ejemplo = _sostenibilidad()
        periodo = Periodo(desde=desde, hasta=hasta)
        if desde <= ejemplo.periodo.hasta and hasta >= ejemplo.periodo.desde:
            return ejemplo.model_copy(update={"periodo": periodo})
        return IndicadoresSostenibilidad(
            periodo=periodo,
            con_datos=False,
            rutas_cerradas=0,
            distancia_km=None,
            co2_kg=None,
            combustible_l=None,
            costo_soles=None,
            ahorro_vs_secuencial=None,
            cumplimiento_ventanas_pct=None,
            parametros_versiones=[],
            simulado=True,
        )
