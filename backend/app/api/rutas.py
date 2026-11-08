"""ECL-94 (ST-045), ECL-96 (ST-047), ECL-119: routes and sustainability.

Optimizations are real since ST-047: the request is solved and stored before
answering (``simulado: false``). Since ECL-119 the Operator records stop
outcomes and closes routes, and the sustainability dashboard adds only closed
routes (US-009). RBAC follows the static matrix (``app.core.rbac``) without
changing it:

- request an optimization: ``optimizaciones.ejecutar`` (Operador);
- list optimizations (summaries, no personal data): ``optimizaciones.consultar``
  general scope (Administrador, Operador, Analista, Auditor);
- one optimization with routes, stops and driver names: ``rutas.consultar``
  general scope (Administrador, Operador);
- sustainability dashboard: ``indicadores.consultar`` general scope
  (Administrador, Operador, Analista, Auditor);
- stop outcomes and route closure: ``rutas.actualizar_estado`` general scope,
  narrowed to the Operador as the ratified US-009 BDD says.
"""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.api.dependencies import require_permission
from app.api.validation import SanitizedRoute
from app.core.rbac import Identidad, Permiso, Rol
from app.optimizacion.modelo import Punto
from app.schemas.rutas import (
    PAGE_SIZE_DEFAULT,
    PAGE_SIZE_MAX,
    IndicadoresSostenibilidad,
    OptimizacionAceptada,
    OptimizacionDetalle,
    OptimizacionPage,
    OptimizacionSolicitud,
    ParadaActualizada,
    ResultadoParadaSolicitud,
    RutaCerrada,
)
from app.services.cierre_rutas import (
    CierreConflicto,
    CierreRutaService,
    CierreUnavailable,
    IndicadoresIncompletos,
    ResultadoInvalido,
    RutaNoEncontrada,
)
from app.services.optimizaciones import (
    OptimizacionFallida,
    OptimizacionService,
    OptimizacionUnavailable,
    SeleccionInvalida,
)

router = APIRouter(prefix="/optimizaciones", tags=["rutas"], route_class=SanitizedRoute)
indicadores_router = APIRouter(
    prefix="/indicadores", tags=["rutas"], route_class=SanitizedRoute
)
rutas_router = APIRouter(prefix="/rutas", tags=["rutas"], route_class=SanitizedRoute)

SIMULADO = "X-Datos-Simulados"
_ERRORS = {
    401: {"description": "Sin sesión"},
    403: {"description": "Rol sin permiso o cambio de contraseña requerido"},
    422: {"description": "Entrada inválida (sin repetir los valores enviados)"},
}


NO_DISPONIBLE = "Servicio no disponible"


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


def get_closure_service(request: Request) -> CierreRutaService:
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NO_DISPONIBLE)
    return CierreRutaService(factory)


Cierres = Annotated[CierreRutaService, Depends(get_closure_service)]
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
        "Solo rutas CERRADA cuyo cierre cae en el periodo, días inclusivos de "
        "Lima (US-009). Sin rutas cerradas responde con_datos=false y los "
        "indicadores en null, nunca ceros inventados. Ahorros desde sumas, con "
        "signo; pct null si la base secuencial es 0. Cumplimiento con la hora "
        "real de atención; NO_ATENDIDA cuenta como incumplida."
    ),
    responses={**_ERRORS, 503: {"description": "Servicio no disponible"}},
)
def sustainability_indicators(
    response: Response,
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.INDICADORES_CONSULTAR))
    ],
    service: Cierres,
    desde: date,
    hasta: date,
) -> IndicadoresSostenibilidad:
    if desde > hasta:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "El inicio del periodo es posterior al fin",
        )
    try:
        indicadores = service.indicadores(desde, hasta)
    except (CierreUnavailable, IndicadoresIncompletos):
        raise _no_disponible() from None
    _marcar(response, indicadores.simulado)
    return indicadores


_RUTA_ERRORS = {
    **_ERRORS,
    404: {"description": "Ruta o parada inexistente"},
    409: {"description": "El estado de la ruta o la parada no permite el cambio"},
    503: {"description": "Servicio no disponible"},
}
_OPERADOR = require_permission(
    Permiso.RUTAS_ACTUALIZAR_ESTADO, roles=frozenset({Rol.OPERADOR})
)


@rutas_router.patch(
    "/{ruta_id}/paradas/{parada_id}",
    response_model=ParadaActualizada,
    summary="Registrar el resultado de una parada",
    description=(
        "El Operador registra ATENDIDA (con la hora real atendida_en, no futura "
        "ni anterior a la jornada) o NO_ATENDIDA. Una parada con resultado final "
        "no se sobrescribe (409); repetir el mismo resultado responde 200. El "
        "primer resultado pasa la ruta de PLANIFICADA a EN_CURSO."
    ),
    responses=_RUTA_ERRORS,
)
def record_stop_outcome(
    ruta_id: UUID,
    parada_id: UUID,
    payload: ResultadoParadaSolicitud,
    response: Response,
    _identity: Annotated[Identidad, Depends(_OPERADOR)],
    service: Cierres,
) -> ParadaActualizada:
    try:
        resultado = service.registrar_parada(ruta_id, parada_id, payload)
    except RutaNoEncontrada as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from None
    except CierreConflicto as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None
    except ResultadoInvalido as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"campo": error.campo, "motivo": error.motivo},
        ) from None
    except CierreUnavailable:
        raise _no_disponible() from None
    _marcar(response, simulado=False)
    return resultado


@rutas_router.post(
    "/{ruta_id}/cierre",
    response_model=RutaCerrada,
    summary="Cerrar una ruta",
    description=(
        "Solo el Operador. Exige todas las paradas en ATENDIDA o NO_ATENDIDA; "
        "registra cerrada_en y audita el cierre sin datos personales. Repetir "
        "el cierre devuelve el ya guardado, sin duplicarlo. Una optimización "
        "COMPLETADA o una ETA alcanzada no cierran la ruta."
    ),
    responses=_RUTA_ERRORS,
)
def close_route(
    ruta_id: UUID,
    response: Response,
    identity: Annotated[Identidad, Depends(_OPERADOR)],
    service: Cierres,
) -> RutaCerrada:
    try:
        cierre = service.cerrar(ruta_id, identity.usuario_id)
    except RutaNoEncontrada as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from None
    except CierreConflicto as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None
    except CierreUnavailable:
        raise _no_disponible() from None
    _marcar(response, simulado=False)
    return cierre
