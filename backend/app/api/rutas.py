"""ECL-94 (ST-045): route optimization and sustainability endpoints.

Contract first, with simulated data: every response carries ``simulado: true``
and the ``X-Datos-Simulados: true`` header until ST-047 connects the optimizer.
RBAC follows the static matrix (``app.core.rbac``) without changing it:

- request an optimization: ``optimizaciones.ejecutar`` (Operador);
- list optimizations (summaries, no personal data): ``optimizaciones.consultar``
  general scope (Administrador, Operador, Analista, Auditor);
- one optimization with routes, stops and driver names: ``rutas.consultar``
  general scope (Administrador, Operador);
- sustainability dashboard: ``indicadores.consultar`` general scope
  (Administrador, Operador, Analista, Auditor).
"""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.dependencies import require_permission
from app.api.validation import SanitizedRoute
from app.core.rbac import Identidad, Permiso
from app.schemas.rutas import (
    PAGE_SIZE_DEFAULT,
    PAGE_SIZE_MAX,
    IndicadoresSostenibilidad,
    OptimizacionAceptada,
    OptimizacionDetalle,
    OptimizacionPage,
    OptimizacionSolicitud,
)
from app.services.rutas_simuladas import RutasSimuladasService

router = APIRouter(prefix="/optimizaciones", tags=["rutas"], route_class=SanitizedRoute)
indicadores_router = APIRouter(
    prefix="/indicadores", tags=["rutas"], route_class=SanitizedRoute
)

SIMULADO = "X-Datos-Simulados"
_ERRORS = {
    401: {"description": "Sin sesión"},
    403: {"description": "Rol sin permiso o cambio de contraseña requerido"},
    422: {"description": "Entrada inválida (sin repetir los valores enviados)"},
}


def get_route_service() -> RutasSimuladasService:
    return RutasSimuladasService()


Servicio = Annotated[RutasSimuladasService, Depends(get_route_service)]


def _marcar(response: Response) -> None:
    response.headers[SIMULADO] = "true"
    response.headers["Cache-Control"] = "no-store"


@router.post(
    "",
    response_model=OptimizacionAceptada,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Solicitar una optimización de rutas",
    description=(
        "Toma los pedidos PENDIENTE de la fecha (o los indicados) y los vehículos "
        "ACTIVO (o los indicados), hasta 150 pedidos y 15 vehículos (RNF-001). "
        "Responde 202 y la solución se consulta con GET /optimizaciones/{id}. "
        "Simulado: siempre apunta a la optimización de ejemplo."
    ),
    responses=_ERRORS,
)
def request_optimization(
    payload: OptimizacionSolicitud,
    response: Response,
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.OPTIMIZACIONES_EJECUTAR))
    ],
    service: Servicio,
) -> OptimizacionAceptada:
    _marcar(response)
    return service.solicitar(payload)


@router.get(
    "",
    response_model=OptimizacionPage,
    summary="Listar optimizaciones",
    description="Resúmenes sin datos personales, de la más reciente a la más antigua.",
    responses=_ERRORS,
)
def list_optimizations(
    response: Response,
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.OPTIMIZACIONES_CONSULTAR))
    ],
    service: Servicio,
    fecha: date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=PAGE_SIZE_MAX)] = PAGE_SIZE_DEFAULT,
) -> OptimizacionPage:
    _marcar(response)
    return service.listar(fecha, page, page_size)


@router.get(
    "/{optimizacion_id}",
    response_model=OptimizacionDetalle,
    summary="Consultar una optimización con sus rutas",
    description=(
        "Rutas con paradas ordenadas, ETA, descansos (RN-005), trazado GeoJSON, "
        "métricas frente a la ruta secuencial y pedidos no asignados con motivo "
        "(RN-009). Mientras el estado es EN_PROCESO, rutas y resumen van vacíos."
    ),
    responses={**_ERRORS, 404: {"description": "Optimización inexistente"}},
)
def get_optimization(
    optimizacion_id: UUID,
    response: Response,
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.RUTAS_CONSULTAR))
    ],
    service: Servicio,
) -> OptimizacionDetalle:
    detalle = service.detalle(optimizacion_id)
    if detalle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Optimización no encontrada")
    _marcar(response)
    return detalle


@indicadores_router.get(
    "/sostenibilidad",
    response_model=IndicadoresSostenibilidad,
    summary="Indicadores de sostenibilidad del periodo",
    description=(
        "Solo rutas CERRADA del periodo (US-009). Sin rutas cerradas responde "
        "con_datos=false y los indicadores en null, nunca ceros inventados."
    ),
    responses=_ERRORS,
)
def sustainability_indicators(
    response: Response,
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.INDICADORES_CONSULTAR))
    ],
    service: Servicio,
    desde: date,
    hasta: date,
) -> IndicadoresSostenibilidad:
    if desde > hasta:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "El inicio del periodo es posterior al fin",
        )
    _marcar(response)
    return service.sostenibilidad(desde, hasta)
