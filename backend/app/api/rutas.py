"""ECL-94 (ST-045) / ECL-96 (ST-047): route optimization and sustainability.

Optimizations are real since ST-047: the request is solved and stored before
answering (``simulado: false``). The sustainability dashboard keeps the
simulated fixtures (``simulado: true`` plus the ``X-Datos-Simulados: true``
header) until it reads closed routes (US-009). RBAC follows the static matrix
(``app.core.rbac``) without changing it:

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

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.api.dependencies import require_permission
from app.api.validation import SanitizedRoute
from app.core.rbac import Identidad, Permiso
from app.optimizacion.modelo import Punto
from app.schemas.rutas import (
    PAGE_SIZE_DEFAULT,
    PAGE_SIZE_MAX,
    IndicadoresSostenibilidad,
    OptimizacionAceptada,
    OptimizacionDetalle,
    OptimizacionPage,
    OptimizacionSolicitud,
)
from app.services.optimizaciones import (
    OptimizacionFallida,
    OptimizacionService,
    OptimizacionUnavailable,
    SeleccionInvalida,
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


NO_DISPONIBLE = "Servicio no disponible"


def get_route_service() -> RutasSimuladasService:
    return RutasSimuladasService()


def get_optimization_service(request: Request) -> OptimizacionService:
    factory = getattr(request.app.state, "session_factory", None)
    settings = request.app.state.settings
    if factory is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NO_DISPONIBLE)
    return OptimizacionService(
        factory,
        Punto(settings.deposito_latitud, settings.deposito_longitud),
        settings.optimizacion_tiempo_limite_s,
    )


Servicio = Annotated[RutasSimuladasService, Depends(get_route_service)]
Optimizador = Annotated[OptimizacionService, Depends(get_optimization_service)]


def _marcar(response: Response, simulado: bool = True) -> None:
    if simulado:
        response.headers[SIMULADO] = "true"
    response.headers["Cache-Control"] = "no-store"


def _no_disponible() -> HTTPException:
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NO_DISPONIBLE)


@router.post(
    "",
    response_model=OptimizacionAceptada,
    status_code=status.HTTP_201_CREATED,
    summary="Optimizar las rutas de una fecha",
    description=(
        "Toma los pedidos PENDIENTE de la fecha (o los indicados) y los vehículos "
        "ACTIVO (o los indicados), de 1 a 150 pedidos y de 1 a 15 vehículos "
        "(RNF-001), y responde 201 solo cuando la solución quedó guardada "
        "(COMPLETADA). El detalle se consulta con GET /optimizaciones/{id}. Una "
        "selección vacía, de otra fecha o no elegible es 422 y no crea corrida. "
        "Si el cálculo falla, la corrida queda FALLIDA y responde 503 con su "
        "optimizacion_id."
    ),
    responses={
        **_ERRORS,
        503: {"description": "Cálculo fallido (corrida FALLIDA) o servicio caído"},
    },
)
def request_optimization(
    payload: OptimizacionSolicitud,
    response: Response,
    identity: Annotated[
        Identidad, Depends(require_permission(Permiso.OPTIMIZACIONES_EJECUTAR))
    ],
    service: Optimizador,
) -> OptimizacionAceptada:
    try:
        aceptada = service.optimizar(payload, identity.usuario_id)
    except SeleccionInvalida as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"campo": error.campo, "motivo": error.motivo},
        ) from None
    except OptimizacionFallida as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            {
                "optimizacion_id": str(error.optimizacion_id),
                "estado": "FALLIDA",
                "motivo": str(error),
            },
        ) from None
    except OptimizacionUnavailable:
        raise _no_disponible() from None
    _marcar(response, aceptada.simulado)
    return aceptada


@router.get(
    "",
    response_model=OptimizacionPage,
    summary="Listar optimizaciones",
    description="Resúmenes sin datos personales, de la más reciente a la más antigua.",
    responses={**_ERRORS, 503: {"description": "Servicio no disponible"}},
)
def list_optimizations(
    response: Response,
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.OPTIMIZACIONES_CONSULTAR))
    ],
    service: Optimizador,
    fecha: date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=PAGE_SIZE_MAX)] = PAGE_SIZE_DEFAULT,
) -> OptimizacionPage:
    try:
        pagina = service.listar(fecha, page, page_size)
    except OptimizacionUnavailable:
        raise _no_disponible() from None
    _marcar(response, pagina.simulado)
    return pagina


@router.get(
    "/{optimizacion_id}",
    response_model=OptimizacionDetalle,
    summary="Consultar una optimización con sus rutas",
    description=(
        "Rutas con paradas ordenadas, ETA, descansos (RN-005), trazado GeoJSON, "
        "métricas frente a la ruta secuencial y pedidos no asignados con motivo "
        "(RN-009). Mientras el estado es EN_PROCESO o FALLIDA, rutas y resumen "
        "van vacíos; FALLIDA trae un error seguro."
    ),
    responses={
        **_ERRORS,
        404: {"description": "Optimización inexistente"},
        503: {"description": "Servicio no disponible"},
    },
)
def get_optimization(
    optimizacion_id: UUID,
    response: Response,
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.RUTAS_CONSULTAR))
    ],
    service: Optimizador,
) -> OptimizacionDetalle:
    try:
        detalle = service.detalle(optimizacion_id)
    except OptimizacionUnavailable:
        raise _no_disponible() from None
    if detalle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Optimización no encontrada")
    _marcar(response, detalle.simulado)
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
