"""ST-047 (ECL-96): route optimization use cases (US-006, BDD v1.0.0).

``optimizar`` validates the selection (decision 3), records the run as
EN_PROCESO, solves it with the ST-044 engine, prices it with the parameter
version in force (EN-008) and stores the whole result (ST-046) in one
transaction before answering: success is never announced before it is
persisted. A failure of the engine ends the run as FALLIDA with a safe message
and no partial routes. Unassigned orders always keep their reason (RN-009).

MVP: the engine runs in the request (RNF-001, search limited to 20 s by
default); EN-003 moves it to a worker without changing this contract.
"""

import json
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import RowMapping
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core import calculos
from app.models.ruta import Optimizacion, ParadaRuta, PedidoNoAsignado, Ruta
from app.models.vehiculo import Vehiculo
from app.optimizacion import vrptw
from app.optimizacion.modelo import (
    Configuracion,
    EstadoSolucion,
    PedidoVRP,
    Prioridad,
    Problema,
    Punto,
    Solucion,
    VehiculoVRP,
)
from app.optimizacion.modelo import Ruta as RutaVRP
from app.repositories.optimizaciones import (
    ConductorElegible,
    OptimizacionRepository,
    OptimizacionStorageError,
    a_float,
    minutos_desde_medianoche,
)
from app.schemas.rutas import (
    MAX_PEDIDOS,
    MAX_VEHICULOS,
    Ahorro,
    ConductorRef,
    Descanso,
    EstadoOptimizacion,
    LineString,
    Metricas,
    NoAsignado,
    OptimizacionAceptada,
    OptimizacionDetalle,
    OptimizacionItem,
    OptimizacionPage,
    OptimizacionSolicitud,
    Parada,
    Resumen,
    VehiculoRef,
)
from app.schemas.rutas import Ruta as RutaRespuesta
from app.services.parametros import (
    ConjuntoParametros,
    ParametroService,
    ParametrosNoEncontrados,
    ParametrosUnavailable,
)

LIMA = ZoneInfo("America/Lima")
ERROR_CALCULO = "No se pudo calcular la solución de rutas"
MATRIZ = "Haversine x factor de desvío a velocidad constante; sin red vial ni tráfico"


class SeleccionInvalida(ValueError):
    """422: the request cannot start a run. Never echoes the sent values."""

    def __init__(self, campo: str, motivo: str) -> None:
        super().__init__(motivo)
        self.campo = campo
        self.motivo = motivo


class OptimizacionFallida(RuntimeError):
    """The run was stored as FALLIDA; the caller can still consult it."""

    def __init__(self, optimizacion_id: UUID) -> None:
        super().__init__(ERROR_CALCULO)
        self.optimizacion_id = optimizacion_id


class OptimizacionUnavailable(RuntimeError):
    """Sanitized operational failure."""


@dataclass(frozen=True)
class Seleccion:
    pedidos: list[RowMapping]
    vehiculos: list[Vehiculo]


def medianoche(fecha: date) -> datetime:
    return datetime.combine(fecha, time(0), LIMA)


def _ahorro(base: float, nuevo: float) -> float | None:
    """BDD decisions 4 and 7: exact, signed, null with a zero baseline."""
    return None if base == 0 else (base - nuevo) / base * 100


def _costo(km: float, litros: float, parametros: dict[str, Decimal]) -> float:
    """Fuel by the gallon with the versioned factor, plus maintenance per km."""
    return calculos.costo_combustible_soles(
        litros,
        parametros["PRECIO_COMBUSTIBLE_GALON"],
        parametros["LITROS_POR_GALON"],
    ) + calculos.costo_mantenimiento_soles(km, parametros["COSTO_MANTENIMIENTO_KM"])


def asignar_conductores(
    rutas: Sequence[tuple[datetime, datetime]], conductores: Sequence[ConductorElegible]
) -> list[UUID | None]:
    """ECL-79: each route gets the first free driver whose availability covers
    it; a driver drives at most one route of a run (RN-004)."""
    libres = list(conductores)
    asignados: list[UUID | None] = []
    for salida, regreso in rutas:
        elegido = next(
            (
                c
                for c in libres
                if c.disponible_desde <= salida and c.disponible_hasta >= regreso
            ),
            None,
        )
        if elegido is not None:
            libres.remove(elegido)
        asignados.append(None if elegido is None else elegido.conductor_id)
    return asignados


class OptimizacionService:
    def __init__(
        self,
        factory: sessionmaker[Session],
        deposito: Punto,
        tiempo_limite_s: int = 20,
        resolver: Callable[[Problema], Solucion] = vrptw.resolver,
        reloj: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._factory = factory
        self._deposito = deposito
        self._configuracion = Configuracion(tiempo_limite_s=tiempo_limite_s)
        self._resolver = resolver
        self._reloj = reloj

    # --- POST /optimizaciones ----------------------------------------------
    def optimizar(
        self, solicitud: OptimizacionSolicitud, actor: UUID
    ) -> OptimizacionAceptada:
        ahora = self._reloj()
        parametros = self._parametros(ahora)
        try:
            with self._factory() as session:
                repository = OptimizacionRepository(session)
                seleccion = self._seleccionar(repository, solicitud)
                conductores = repository.conductores_elegibles(
                    solicitud.fecha_operacion
                )
            problema = self._problema(seleccion, solicitud.fecha_operacion)
            optimizacion = Optimizacion(
                solicitada_por=actor,
                fecha_operacion=solicitud.fecha_operacion,
                estado="EN_PROCESO",
                solicitada_en=ahora,
                instantanea=self._instantanea(
                    seleccion, parametros.valores, len(conductores)
                ),
            )
            with self._factory.begin() as session:
                OptimizacionRepository(session).crear(optimizacion)
        except (OptimizacionStorageError, SQLAlchemyError):
            raise OptimizacionUnavailable("Optimization service unavailable") from None
        run_id = optimizacion.optimizacion_id
        try:
            solucion = self._resolver(problema)
            if solucion.estado is not EstadoSolucion.COMPLETADA:
                # No assignment found: the time limit proves no infeasibility.
                raise RuntimeError("engine returned no solution")
            self._guardar(
                run_id,
                solicitud.fecha_operacion,
                seleccion,
                problema,
                solucion,
                parametros.version,
                parametros.valores,
                conductores,
            )
        except Exception:  # noqa: BLE001 - every engine/storage failure is FALLIDA
            self._fallar(run_id)
            raise OptimizacionFallida(run_id) from None
        return OptimizacionAceptada(
            optimizacion_id=run_id,
            estado=EstadoOptimizacion.COMPLETADA,
            solicitada_en=ahora.astimezone(LIMA),
            simulado=False,
        )

    def _parametros(self, ahora: datetime) -> ConjuntoParametros:
        """EN-008: the run is priced with the version in force when requested."""
        servicio = ParametroService(self._factory)
        try:
            return servicio.conjunto(servicio.vigente(ahora).version)
        except ParametrosNoEncontrados:
            raise SeleccionInvalida(
                "parametros", "No hay una versión de parámetros vigente (EN-008)"
            ) from None
        except ParametrosUnavailable:
            raise OptimizacionUnavailable("Optimization service unavailable") from None

    def _seleccionar(
        self, repository: OptimizacionRepository, solicitud: OptimizacionSolicitud
    ) -> Seleccion:
        inicio = medianoche(solicitud.fecha_operacion)
        fin = medianoche(solicitud.fecha_operacion + timedelta(days=1))
        if solicitud.pedido_ids is None:
            pedidos = repository.pedidos_pendientes(inicio, fin, MAX_PEDIDOS + 1)
            if not pedidos:
                raise SeleccionInvalida(
                    "pedido_ids", "No hay pedidos PENDIENTE para la fecha"
                )
            if len(pedidos) > MAX_PEDIDOS:
                raise SeleccionInvalida(
                    "pedido_ids",
                    f"La fecha tiene más de {MAX_PEDIDOS} pedidos PENDIENTE; "
                    "indica cuáles optimizar",
                )
        else:
            pedidos = repository.pedidos_por_id(solicitud.pedido_ids)
            validos = [
                p
                for p in pedidos
                if p["estado"] == "PENDIENTE" and inicio <= p["ventana_inicio"] < fin
            ]
            if len(validos) != len(solicitud.pedido_ids):
                raise SeleccionInvalida(
                    "pedido_ids",
                    "Hay pedidos inexistentes, de otra fecha o que no están PENDIENTE",
                )
        vehiculos = repository.vehiculos(solicitud.vehiculo_ids, MAX_VEHICULOS + 1)
        if solicitud.vehiculo_ids is None:
            if not vehiculos:
                raise SeleccionInvalida("vehiculo_ids", "No hay vehículos ACTIVO")
            if len(vehiculos) > MAX_VEHICULOS:
                raise SeleccionInvalida(
                    "vehiculo_ids",
                    f"Hay más de {MAX_VEHICULOS} vehículos ACTIVO; indica cuáles usar",
                )
        elif len(vehiculos) != len(solicitud.vehiculo_ids) or any(
            v.estado != "ACTIVO" for v in vehiculos
        ):
            raise SeleccionInvalida(
                "vehiculo_ids", "Hay vehículos inexistentes o que no están ACTIVO"
            )
        return Seleccion(pedidos, vehiculos)

    def _problema(self, seleccion: Seleccion, fecha: date) -> Problema:
        base = medianoche(fecha)
        pedidos = tuple(
            PedidoVRP(
                pedido_id=str(p["pedido_id"]),
                ubicacion=(
                    None
                    if p["latitud"] is None
                    else Punto(float(p["latitud"]), float(p["longitud"]))
                ),
                peso_kg=float(p["peso_kg"]),
                volumen_m3=float(p["volumen_m3"]),
                ventana_inicio_min=minutos_desde_medianoche(p["ventana_inicio"], base),
                ventana_fin_min=minutos_desde_medianoche(p["ventana_fin"], base),
                prioridad=Prioridad(p["prioridad"]),
            )
            for p in seleccion.pedidos
        )
        vehiculos = tuple(
            VehiculoVRP(
                vehiculo_id=str(v.vehiculo_id),
                capacidad_kg=float(v.capacidad_kg),
                capacidad_m3=float(v.capacidad_m3),
                rendimiento_km_l=float(v.rendimiento_km_l),
                factor_co2_kg_km=float(v.factor_co2_kg_km),
            )
            for v in seleccion.vehiculos
        )
        return Problema(self._deposito, pedidos, vehiculos, self._configuracion)

    def _instantanea(
        self, seleccion: Seleccion, parametros: dict[str, Decimal], conductores: int
    ) -> dict[str, Any]:
        """What the run used, to reproduce it (BDD US-006). No personal data."""
        return {
            "deposito": asdict(self._deposito),
            "configuracion": asdict(self._configuracion),
            "matriz": MATRIZ,
            "parametros": {codigo: str(valor) for codigo, valor in parametros.items()},
            "pedidos": [str(p["pedido_id"]) for p in seleccion.pedidos],
            "vehiculos": [
                {
                    "vehiculo_id": str(v.vehiculo_id),
                    "capacidad_kg": str(v.capacidad_kg),
                    "capacidad_m3": str(v.capacidad_m3),
                    "rendimiento_km_l": str(v.rendimiento_km_l),
                    "factor_co2_kg_km": str(v.factor_co2_kg_km),
                }
                for v in seleccion.vehiculos
            ],
            "conductores_elegibles": conductores,
        }

    def _guardar(  # noqa: PLR0913 - one call that stores a whole result
        self,
        run_id: UUID,
        fecha: date,
        seleccion: Seleccion,
        problema: Problema,
        solucion: Solucion,
        version: str,
        parametros: dict[str, Decimal],
        conductores: Sequence[ConductorElegible],
    ) -> None:
        base = medianoche(fecha)
        vehiculos = {str(v.vehiculo_id): v for v in seleccion.vehiculos}
        pedidos = {str(p.pedido_id): p for p in problema.pedidos}
        ventanas = {str(p["pedido_id"]): p for p in seleccion.pedidos}
        horarios = [
            (
                base + timedelta(minutes=r.salida_min),
                base + timedelta(minutes=r.regreso_min),
            )
            for r in solucion.rutas
        ]
        choferes = asignar_conductores(horarios, conductores)
        rutas: list[tuple[Ruta, list[ParadaRuta]]] = []
        a_tiempo = 0
        for ruta, (salida, regreso), conductor in zip(
            solucion.rutas, horarios, choferes, strict=True
        ):
            paradas = [
                ParadaRuta(
                    pedido_id=UUID(p.pedido_id),
                    secuencia=p.secuencia,
                    eta=base + timedelta(minutes=p.eta_min),
                )
                for p in ruta.paradas
            ]
            a_tiempo += sum(
                ventanas[p.pedido_id]["ventana_inicio"]
                <= base + timedelta(minutes=p.eta_min)
                <= ventanas[p.pedido_id]["ventana_fin"]
                for p in ruta.paradas
            )
            rutas.append(
                (
                    self._ruta(
                        run_id,
                        fecha,
                        ruta,
                        vehiculos[ruta.vehiculo_id],
                        pedidos,
                        (salida, regreso),
                        conductor,
                        parametros,
                        base,
                    ),
                    paradas,
                )
            )
        asignados = sum(len(r.paradas) for r in solucion.rutas)
        secuencial = solucion.comparacion.secuencial if solucion.comparacion else None
        valores: dict[str, Any] = {
            "estado": "COMPLETADA",
            "finalizada_en": self._reloj(),
            "duracion_s": solucion.duracion_s,
            "parametros_version": version,
            "secuencial_distancia_km": secuencial.distancia_km if secuencial else 0.0,
            "secuencial_co2_kg": secuencial.co2_kg if secuencial else 0.0,
            "secuencial_combustible_l": secuencial.combustible_l if secuencial else 0.0,
            "secuencial_costo_soles": (
                _costo(secuencial.distancia_km, secuencial.combustible_l, parametros)
                if secuencial
                else 0.0
            ),
            "cumplimiento_ventanas_pct": (
                a_tiempo / asignados * 100 if asignados else 0.0
            ),
        }
        no_asignados = [
            PedidoNoAsignado(
                optimizacion_id=run_id,
                pedido_id=UUID(n.pedido_id),
                motivo=n.motivo.value,
            )
            for n in solucion.no_asignados
        ]
        with self._factory.begin() as session:
            OptimizacionRepository(session).completar(
                run_id, valores, rutas, no_asignados
            )

    def _ruta(  # noqa: PLR0913 - maps one engine route to its row
        self,
        run_id: UUID,
        fecha: date,
        ruta: RutaVRP,
        vehiculo: Vehiculo,
        pedidos: dict[str, PedidoVRP],
        horario: tuple[datetime, datetime],
        conductor: UUID | None,
        parametros: dict[str, Decimal],
        base: datetime,
    ) -> Ruta:
        km = ruta.metricas.distancia_km
        litros = ruta.metricas.combustible_l
        return Ruta(
            optimizacion_id=run_id,
            fecha_operacion=fecha,
            vehiculo_id=vehiculo.vehiculo_id,
            conductor_id=conductor,
            motivo_sin_conductor=None if conductor else "SIN_CONDUCTOR_ELEGIBLE",
            salida=horario[0],
            regreso=horario[1],
            tiempo_min=ruta.duracion_min,
            peso_kg=Decimal(str(ruta.peso_kg)),
            volumen_m3=Decimal(str(ruta.volumen_m3)),
            distancia_km=km,
            co2_kg=ruta.metricas.co2_kg,
            combustible_l=litros,
            costo_soles=_costo(km, litros, parametros),
            trazado=trazado(
                self._deposito, [pedidos[p.pedido_id].ubicacion for p in ruta.paradas]
            ),
            descansos=[
                {
                    "inicio": (base + timedelta(minutes=d.inicio_min)).isoformat(),
                    "fin": (
                        base + timedelta(minutes=d.inicio_min + d.duracion_min)
                    ).isoformat(),
                }
                for d in ruta.descansos
            ],
        )

    def _fallar(self, run_id: UUID) -> None:
        try:
            with self._factory.begin() as session:
                OptimizacionRepository(session).fallar(
                    run_id, ERROR_CALCULO, self._reloj()
                )
        except (OptimizacionStorageError, SQLAlchemyError):
            raise OptimizacionUnavailable("Optimization service unavailable") from None

    # --- GET /optimizaciones/{id} -------------------------------------------
    def detalle(self, optimizacion_id: UUID) -> OptimizacionDetalle | None:
        try:
            with self._factory() as session:
                repository = OptimizacionRepository(session)
                run = repository.obtener(optimizacion_id)
                if run is None:
                    return None
                if run.estado != "COMPLETADA":
                    return _detalle(run, None, [], [])
                rutas = repository.rutas_de(optimizacion_id)
                paradas = repository.paradas_de(optimizacion_id)
                omitidos = repository.no_asignados_de(optimizacion_id)
        except (OptimizacionStorageError, SQLAlchemyError):
            raise OptimizacionUnavailable("Optimization service unavailable") from None
        respuestas = [_ruta_respuesta(r, paradas) for r in rutas]
        no_asignados = [
            NoAsignado(pedido_id=o["pedido_id"], motivo=o["motivo"]) for o in omitidos
        ]
        resumen = _resumen(
            run,
            [r.metricas for r in respuestas],
            sum(len(r.paradas) for r in respuestas),
            len(no_asignados),
        )
        return _detalle(run, resumen, respuestas, no_asignados)

    # --- GET /optimizaciones ------------------------------------------------
    def listar(self, fecha: date | None, page: int, page_size: int) -> OptimizacionPage:
        try:
            with self._factory() as session:
                repository = OptimizacionRepository(session)
                runs, total = repository.pagina(fecha, page, page_size)
                ids = [r.optimizacion_id for r in runs if r.estado == "COMPLETADA"]
                totales = repository.totales(ids)
                conteos = repository.conteos(ids)
        except (OptimizacionStorageError, SQLAlchemyError):
            raise OptimizacionUnavailable("Optimization service unavailable") from None
        items = []
        for run in runs:
            resumen = None
            if run.estado == "COMPLETADA":
                fila = totales.get(run.optimizacion_id)
                metricas = [] if fila is None else [_metricas(fila)]
                asignados, omitidos = conteos[run.optimizacion_id]
                resumen = _resumen(
                    run,
                    metricas,
                    asignados,
                    omitidos,
                    rutas=(0 if fila is None else int(fila["rutas"])),
                )
            items.append(
                OptimizacionItem(
                    optimizacion_id=run.optimizacion_id,
                    estado=EstadoOptimizacion(run.estado),
                    fecha_operacion=run.fecha_operacion,
                    solicitada_en=run.solicitada_en.astimezone(LIMA),
                    resumen=resumen,
                )
            )
        return OptimizacionPage(
            items=items, page=page, page_size=page_size, total=total, simulado=False
        )


def trazado(deposito: Punto, paradas: Sequence[Punto | None]) -> str:
    """EWKT line depot -> stops -> depot in visiting order.

    Straight segments between stops, not the road network: the map shows the
    order of the visit; distances come from the engine's matrix (MATRIZ).
    """
    puntos = [deposito, *(p for p in paradas if p is not None), deposito]
    coordenadas = ", ".join(f"{p.longitud} {p.latitud}" for p in puntos)
    return f"SRID=4326;LINESTRING({coordenadas})"


def _metricas(fila: RowMapping) -> Metricas:
    return Metricas(
        distancia_km=a_float(fila["distancia_km"]),
        co2_kg=a_float(fila["co2_kg"]),
        combustible_l=a_float(fila["combustible_l"]),
        costo_soles=a_float(fila["costo_soles"]),
    )


def _resumen(
    run: Optimizacion,
    metricas: Sequence[Metricas],
    asignados: int,
    omitidos: int,
    rutas: int | None = None,
) -> Resumen:
    optimizada = Metricas(
        distancia_km=sum(m.distancia_km for m in metricas),
        co2_kg=sum(m.co2_kg for m in metricas),
        combustible_l=sum(m.combustible_l for m in metricas),
        costo_soles=sum(m.costo_soles for m in metricas),
    )
    secuencial = Metricas(
        distancia_km=a_float(run.secuencial_distancia_km),
        co2_kg=a_float(run.secuencial_co2_kg),
        combustible_l=a_float(run.secuencial_combustible_l),
        costo_soles=a_float(run.secuencial_costo_soles),
    )
    return Resumen(
        rutas=len(metricas) if rutas is None else rutas,
        pedidos_asignados=asignados,
        pedidos_no_asignados=omitidos,
        optimizada=optimizada,
        secuencial=secuencial,
        ahorro_pct=Ahorro(
            distancia=_ahorro(secuencial.distancia_km, optimizada.distancia_km),
            co2=_ahorro(secuencial.co2_kg, optimizada.co2_kg),
            combustible=_ahorro(secuencial.combustible_l, optimizada.combustible_l),
            costo=_ahorro(secuencial.costo_soles, optimizada.costo_soles),
        ),
        cumplimiento_ventanas_pct=a_float(run.cumplimiento_ventanas_pct),
    )


def _ruta_respuesta(fila: RowMapping, paradas: Sequence[RowMapping]) -> RutaRespuesta:
    propias = [p for p in paradas if p["ruta_id"] == fila["ruta_id"]]
    trazado = json.loads(fila["trazado"])
    return RutaRespuesta(
        ruta_id=fila["ruta_id"],
        vehiculo=VehiculoRef(
            vehiculo_id=fila["vehiculo_id"], placa=fila["placa"], tipo=fila["tipo"]
        ),
        conductor=(
            None
            if fila["conductor_id"] is None
            else ConductorRef(
                conductor_id=fila["conductor_id"], nombre=fila["conductor_nombre"]
            )
        ),
        motivo_sin_conductor=fila["motivo_sin_conductor"],
        estado=fila["estado"],
        salida=fila["salida"].astimezone(LIMA),
        regreso=fila["regreso"].astimezone(LIMA),
        tiempo_min=fila["tiempo_min"],
        peso_kg=a_float(fila["peso_kg"]),
        volumen_m3=a_float(fila["volumen_m3"]),
        metricas=_metricas(fila),
        trazado=LineString(type="LineString", coordinates=trazado["coordinates"]),
        paradas=[
            Parada(
                parada_id=p["parada_id"],
                secuencia=p["secuencia"],
                pedido_id=p["pedido_id"],
                latitud=p["latitud"],
                longitud=p["longitud"],
                ventana_inicio=p["ventana_inicio"].astimezone(LIMA),
                ventana_fin=p["ventana_fin"].astimezone(LIMA),
                eta=p["eta"].astimezone(LIMA),
                estado=p["estado"],
            )
            for p in propias
        ],
        descansos=[
            Descanso(inicio=d["inicio"], fin=d["fin"]) for d in fila["descansos"]
        ],
    )


def _detalle(
    run: Optimizacion,
    resumen: Resumen | None,
    rutas: list[RutaRespuesta],
    no_asignados: list[NoAsignado],
) -> OptimizacionDetalle:
    return OptimizacionDetalle(
        optimizacion_id=run.optimizacion_id,
        estado=EstadoOptimizacion(run.estado),
        fecha_operacion=run.fecha_operacion,
        solicitada_en=run.solicitada_en.astimezone(LIMA),
        finalizada_en=(
            None if run.finalizada_en is None else run.finalizada_en.astimezone(LIMA)
        ),
        duracion_s=run.duracion_s,
        parametros_version=run.parametros_version,
        simulado=run.simulado,
        resumen=resumen,
        rutas=rutas,
        no_asignados=no_asignados,
        error=run.error,
    )
