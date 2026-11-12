"""VRPTW solver on OR-Tools (ECL-93 / ST-044, risk R-01).

Model:
- one depot, heterogeneous fleet;
- hard constraints: weight and volume capacity (RN-003), order time windows
  (RN-006), working day and a one-hour break after four continuous hours
  (RN-005, conservative: service and waiting count as driving);
- objective: kilograms of CO2 (distance x each vehicle's factor, a Green VRP)
  plus a priority-based penalty for every order left out (RF-006 "Ruta feliz",
  RN-007), so the solver drops low-priority orders first;
- orders that cannot be served are reported with a reason (RN-009) and never
  invalidate the routes that are feasible (RF-006 "Ruta infeliz").
"""

from dataclasses import dataclass
from time import perf_counter

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app.optimizacion.distancias import matriz_km, minutos_viaje
from app.optimizacion.metricas import metricas_vehiculo, ruta_secuencial, sumar
from app.optimizacion.modelo import (
    Comparacion,
    Descanso,
    EstadoSolucion,
    MotivoNoAsignado,
    NoAsignado,
    Parada,
    PedidoVRP,
    Prioridad,
    Problema,
    Ruta,
    Solucion,
    VehiculoVRP,
)

ESCALA_KG = 100  # 0.01 kg, the precision of pedido.peso_kg
ESCALA_M3 = 1000  # 0.001 m3, the precision of pedido.volumen_m3
ESCALA_COSTO = 1000  # objective in grams of CO2
PENALIDAD = {
    Prioridad.EXPRESS: 10_000_000,
    Prioridad.ESTANDAR: 1_000_000,
    Prioridad.ECONOMICO: 300_000,
}


@dataclass(frozen=True)
class _Red:
    """Located candidate orders; node 0 is the depot."""

    pedidos: tuple[PedidoVRP, ...]
    km: list[list[float]]
    minutos: list[list[int]]


def _fin_jornada(problema: Problema) -> int:
    c = problema.configuracion
    return c.inicio_jornada_min + c.jornada_max_min + c.descanso_min


def _cabe_en_alguno(pedido: PedidoVRP, vehiculos: tuple[VehiculoVRP, ...]) -> bool:
    return any(
        pedido.peso_kg <= v.capacidad_kg and pedido.volumen_m3 <= v.capacidad_m3
        for v in vehiculos
    )


def _filtrar(
    problema: Problema,
) -> tuple[_Red, list[NoAsignado]]:
    """Separate orders no vehicle could ever serve, with their reason."""
    c = problema.configuracion
    no_asignados: list[NoAsignado] = []
    ubicados: list[PedidoVRP] = []
    for pedido in problema.pedidos:
        if pedido.ubicacion is None:
            no_asignados.append(
                NoAsignado(pedido.pedido_id, MotivoNoAsignado.SIN_UBICACION)
            )
        elif not problema.vehiculos:
            no_asignados.append(
                NoAsignado(pedido.pedido_id, MotivoNoAsignado.SIN_VEHICULO)
            )
        elif not _cabe_en_alguno(pedido, problema.vehiculos):
            no_asignados.append(
                NoAsignado(pedido.pedido_id, MotivoNoAsignado.EXCEDE_CAPACIDAD)
            )
        else:
            ubicados.append(pedido)

    puntos = [problema.deposito, *(p.ubicacion for p in ubicados)]
    km = matriz_km(puntos, c.factor_desvio)  # type: ignore[arg-type]
    minutos = [[minutos_viaje(d, c.velocidad_kmh) for d in fila] for fila in km]
    fin = _fin_jornada(problema)
    candidatos: list[int] = []
    for i, pedido in enumerate(ubicados, start=1):
        llegada = c.inicio_jornada_min + minutos[0][i]
        inicio = max(llegada, pedido.ventana_inicio_min)
        regreso = inicio + c.servicio_min + minutos[i][0]
        if (
            pedido.ventana_inicio_min >= pedido.ventana_fin_min
            or llegada > pedido.ventana_fin_min
            or regreso > fin
        ):
            no_asignados.append(
                NoAsignado(pedido.pedido_id, MotivoNoAsignado.VENTANA_INVIABLE)
            )
        else:
            candidatos.append(i)

    nodos = [0, *candidatos]
    red = _Red(
        pedidos=tuple(ubicados[i - 1] for i in candidatos),
        km=[[km[a][b] for b in nodos] for a in nodos],
        minutos=[[minutos[a][b] for b in nodos] for a in nodos],
    )
    return red, no_asignados


class _Modelo:
    """OR-Tools routing model for the located, feasible candidates."""

    def __init__(self, problema: Problema, red: _Red) -> None:
        self.problema = problema
        self.red = red
        self.config = problema.configuracion
        vehiculos = problema.vehiculos
        self.manager = pywrapcp.RoutingIndexManager(
            len(red.pedidos) + 1, len(vehiculos), 0
        )
        self.routing = pywrapcp.RoutingModel(self.manager)
        self._callbacks: list[object] = []  # keep Python callbacks alive
        self.descansos: list[pywrapcp.IntervalVar] = []
        self._costos()
        self._capacidades()
        self._tiempo()
        self._omisiones()

    def _registrar(self, funcion) -> int:
        self._callbacks.append(funcion)
        return self.routing.RegisterTransitCallback(funcion)

    def _nodo(self, indice: int) -> int:
        return self.manager.IndexToNode(indice)

    def _costos(self) -> None:
        km = self.red.km
        por_factor: dict[float, int] = {}
        for v, vehiculo in enumerate(self.problema.vehiculos):
            factor = vehiculo.factor_co2_kg_km
            if factor not in por_factor:

                def costo(i: int, j: int, f: float = factor) -> int:
                    return round(km[self._nodo(i)][self._nodo(j)] * f * ESCALA_COSTO)

                por_factor[factor] = self._registrar(costo)
            self.routing.SetArcCostEvaluatorOfVehicle(por_factor[factor], v)

    def _capacidades(self) -> None:
        pedidos = self.red.pedidos
        for nombre, escala, demanda, capacidad in (
            ("Peso", ESCALA_KG, "peso_kg", "capacidad_kg"),
            ("Volumen", ESCALA_M3, "volumen_m3", "capacidad_m3"),
        ):
            cargas = [0] + [round(getattr(p, demanda) * escala) for p in pedidos]

            def carga(i: int, cargas: list[int] = cargas) -> int:
                return cargas[self._nodo(i)]

            self._callbacks.append(carga)
            indice = self.routing.RegisterUnaryTransitCallback(carga)
            self.routing.AddDimensionWithVehicleCapacity(
                indice,
                0,
                [int(getattr(v, capacidad) * escala) for v in self.problema.vehiculos],
                True,
                nombre,
            )

    def _tiempo(self) -> None:
        c = self.config
        minutos = self.red.minutos
        servicio = [0] + [c.servicio_min] * len(self.red.pedidos)

        def transito(i: int, j: int) -> int:
            a, b = self._nodo(i), self._nodo(j)
            return servicio[a] + minutos[a][b]

        fin = _fin_jornada(self.problema)
        self.routing.AddDimension(self._registrar(transito), fin, fin, False, "Tiempo")
        tiempo = self.routing.GetDimensionOrDie("Tiempo")
        for nodo, pedido in enumerate(self.red.pedidos, start=1):
            tiempo.CumulVar(self.manager.NodeToIndex(nodo)).SetRange(
                pedido.ventana_inicio_min, pedido.ventana_fin_min
            )
        visita = [servicio[self._nodo(i)] for i in range(self.routing.Size())]
        solver = self.routing.solver()
        for v in range(len(self.problema.vehiculos)):
            inicio = self.routing.Start(v)
            tiempo.CumulVar(inicio).SetRange(c.inicio_jornada_min, fin)
            tiempo.CumulVar(self.routing.End(v)).SetRange(c.inicio_jornada_min, fin)
            tiempo.SetSpanUpperBoundForVehicle(c.jornada_max_min + c.descanso_min, v)
            descanso = solver.FixedDurationIntervalVar(
                c.inicio_jornada_min,
                fin - c.descanso_min,
                c.descanso_min,
                False,  # mandatory: an optional break defeats the distance rule
                f"descanso_{v}",
            )
            self.descansos.append(descanso)
            tiempo.SetBreakIntervalsOfVehicle([descanso], v, visita)
            tiempo.SetBreakDistanceDurationOfVehicle(
                c.conduccion_continua_max_min, c.descanso_min, v
            )
            self.routing.AddVariableMaximizedByFinalizer(tiempo.CumulVar(inicio))
            self.routing.AddVariableMinimizedByFinalizer(
                tiempo.CumulVar(self.routing.End(v))
            )
        # Tie-breaker: one cost unit (1 g CO2) per minute of working day, so
        # equal-distance plans prefer shorter days with less idle waiting.
        tiempo.SetSpanCostCoefficientForAllVehicles(1)
        self.tiempo = tiempo

    def _omisiones(self) -> None:
        for nodo, pedido in enumerate(self.red.pedidos, start=1):
            self.routing.AddDisjunction(
                [self.manager.NodeToIndex(nodo)], PENALIDAD[pedido.prioridad]
            )

    def resolver(self) -> pywrapcp.Assignment | None:
        params = pywrapcp.DefaultRoutingSearchParameters()
        params.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        if self.config.metaheuristica:
            params.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            )
        params.time_limit.FromSeconds(self.config.tiempo_limite_s)
        return self.routing.SolveWithParameters(params)

    def rutas(self, solucion: pywrapcp.Assignment) -> list[Ruta]:
        rutas: list[Ruta] = []
        for v, vehiculo in enumerate(self.problema.vehiculos):
            indice = self.routing.Start(v)
            if self.routing.IsEnd(solucion.Value(self.routing.NextVar(indice))):
                continue
            salida = solucion.Value(self.tiempo.CumulVar(indice))
            paradas: list[Parada] = []
            km = 0.0
            nodo_previo = 0
            indice = solucion.Value(self.routing.NextVar(indice))
            while not self.routing.IsEnd(indice):
                nodo = self._nodo(indice)
                km += self.red.km[nodo_previo][nodo]
                paradas.append(
                    Parada(
                        secuencia=len(paradas) + 1,
                        pedido_id=self.red.pedidos[nodo - 1].pedido_id,
                        eta_min=solucion.Value(self.tiempo.CumulVar(indice)),
                    )
                )
                nodo_previo = nodo
                indice = solucion.Value(self.routing.NextVar(indice))
            km += self.red.km[nodo_previo][0]
            regreso = solucion.Value(self.tiempo.CumulVar(indice))
            ids = {p.pedido_id for p in paradas}
            cargados = [p for p in self.red.pedidos if p.pedido_id in ids]
            propios = [
                (nodo, pedido)
                for nodo, pedido in enumerate(self.red.pedidos, start=1)
                if pedido.pedido_id in ids
            ]
            rutas.append(
                Ruta(
                    vehiculo_id=vehiculo.vehiculo_id,
                    paradas=tuple(paradas),
                    salida_min=salida,
                    regreso_min=regreso,
                    peso_kg=round(sum(p.peso_kg for p in cargados), 2),
                    volumen_m3=round(sum(p.volumen_m3 for p in cargados), 3),
                    metricas=metricas_vehiculo(km, vehiculo),
                    descansos=self._descanso(solucion, v, salida, regreso),
                    secuencial=ruta_secuencial(
                        propios, (vehiculo,), lambda a, b: self.red.km[a][b]
                    ),
                )
            )
        return rutas

    def _descanso(
        self, solucion: pywrapcp.Assignment, v: int, salida: int, regreso: int
    ) -> tuple[Descanso, ...]:
        # A single return path: SonarCloud flags helpers that return tuples of
        # different lengths. Each vehicle has at most one break interval, so
        # the first match is kept, as before.
        contenedor = solucion.IntervalVarContainer()
        elementos = (contenedor.Element(i) for i in range(contenedor.Size()))
        dentro = (
            Descanso(e.StartValue(), e.DurationValue())
            for e in elementos
            if e.Var().Name() == f"descanso_{v}"
            and e.StartValue() < regreso
            and e.StartValue() + e.DurationValue() > salida
        )
        return tuple(dentro)[:1]

    def omitidos(self, solucion: pywrapcp.Assignment) -> list[NoAsignado]:
        return [
            NoAsignado(pedido.pedido_id, MotivoNoAsignado.SIN_VEHICULO)
            for nodo, pedido in enumerate(self.red.pedidos, start=1)
            if solucion.Value(self.routing.NextVar(self.manager.NodeToIndex(nodo)))
            == self.manager.NodeToIndex(nodo)
        ]


def _comparar(red: _Red, rutas: list[Ruta], problema: Problema) -> Comparacion:
    """Compare with the sequential baseline on exactly the served orders."""
    servidos = {p.pedido_id for r in rutas for p in r.paradas}
    pedidos = [
        (nodo, pedido)
        for nodo, pedido in enumerate(red.pedidos, start=1)
        if pedido.pedido_id in servidos
    ]
    return Comparacion(
        optimizada=sumar([r.metricas for r in rutas]),
        secuencial=ruta_secuencial(
            pedidos, problema.vehiculos, lambda a, b: red.km[a][b]
        ),
    )


def resolver(problema: Problema) -> Solucion:
    """Solve the VRPTW. Never raises for infeasible orders: they are reported."""
    inicio = perf_counter()
    red, no_asignados = _filtrar(problema)
    if not red.pedidos:
        return Solucion(
            estado=EstadoSolucion.COMPLETADA,
            rutas=(),
            no_asignados=tuple(no_asignados),
            comparacion=None,
            duracion_s=round(perf_counter() - inicio, 3),
        )
    modelo = _Modelo(problema, red)
    asignacion = modelo.resolver()
    if asignacion is None:
        faltantes = [
            NoAsignado(p.pedido_id, MotivoNoAsignado.SIN_VEHICULO) for p in red.pedidos
        ]
        return Solucion(
            estado=EstadoSolucion.SIN_SOLUCION,
            rutas=(),
            no_asignados=tuple(no_asignados + faltantes),
            comparacion=None,
            duracion_s=round(perf_counter() - inicio, 3),
        )
    rutas = modelo.rutas(asignacion)
    return Solucion(
        estado=EstadoSolucion.COMPLETADA,
        rutas=tuple(rutas),
        no_asignados=tuple(no_asignados + modelo.omitidos(asignacion)),
        comparacion=_comparar(red, rutas, problema) if rutas else None,
        duracion_s=round(perf_counter() - inicio, 3),
    )
