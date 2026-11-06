"""Independent check of a solution against the hard constraints.

It does not trust the solver: it recomputes loads, windows, working day and
breaks from the solution itself. Used by the tests and by the spike script.
"""

from app.optimizacion.modelo import (
    Configuracion,
    PedidoVRP,
    Problema,
    Ruta,
    Solucion,
    VehiculoVRP,
)

TOLERANCIA = 1e-9


def _carga(ruta: Ruta, vehiculo: VehiculoVRP, cargados: list[PedidoVRP]) -> list[str]:
    errores = []
    kg = sum(p.peso_kg for p in cargados)
    m3 = sum(p.volumen_m3 for p in cargados)
    if kg > vehiculo.capacidad_kg + TOLERANCIA:
        errores.append(f"{ruta.vehiculo_id}: {kg:.2f} kg > capacidad")
    if m3 > vehiculo.capacidad_m3 + TOLERANCIA:
        errores.append(f"{ruta.vehiculo_id}: {m3:.3f} m3 > capacidad")
    return errores


def _ventanas(ruta: Ruta, pedidos: dict[str, PedidoVRP]) -> list[str]:
    errores = [
        f"{p.pedido_id}: llegada fuera de ventana"
        for p in ruta.paradas
        if not (
            pedidos[p.pedido_id].ventana_inicio_min
            <= p.eta_min
            <= pedidos[p.pedido_id].ventana_fin_min
        )
    ]
    etas = [p.eta_min for p in ruta.paradas]
    if etas != sorted(etas):
        errores.append(f"{ruta.vehiculo_id}: secuencia no cronológica")
    return errores


def _tramo_largo(ruta: Ruta, c: Configuracion) -> bool:
    d = ruta.descansos[0]
    antes = d.inicio_min - ruta.salida_min
    despues = ruta.regreso_min - (d.inicio_min + d.duracion_min)
    return (
        d.duracion_min < c.descanso_min
        or max(antes, despues) > c.conduccion_continua_max_min
    )


def _jornada(ruta: Ruta, c: Configuracion) -> list[str]:
    """RN-005: working day and one hour of rest after four continuous hours."""
    errores = []
    if ruta.salida_min < c.inicio_jornada_min:
        errores.append(f"{ruta.vehiculo_id}: sale antes del inicio de jornada")
    descanso = sum(d.duracion_min for d in ruta.descansos)
    if ruta.duracion_min - descanso > c.jornada_max_min:
        errores.append(f"{ruta.vehiculo_id}: excede la jornada")
    if ruta.duracion_min <= c.conduccion_continua_max_min:
        return errores
    if not ruta.descansos:
        errores.append(f"{ruta.vehiculo_id}: más de 4 h sin descanso")
    elif _tramo_largo(ruta, c):
        errores.append(f"{ruta.vehiculo_id}: tramo continuo > 4 h")
    return errores


def _cobertura(problema: Problema, solucion: Solucion) -> list[str]:
    errores = []
    vistos = [p.pedido_id for r in solucion.rutas for p in r.paradas]
    no_asignados = [n.pedido_id for n in solucion.no_asignados]
    if len(vistos) != len(set(vistos)):
        errores.append("Un pedido aparece en más de una parada")
    entrada = sorted(p.pedido_id for p in problema.pedidos)
    if sorted(vistos + no_asignados) != entrada:
        errores.append("Pedidos asignados + no asignados no cuadran con la entrada")
    return errores


def violaciones(problema: Problema, solucion: Solucion) -> list[str]:
    pedidos = {p.pedido_id: p for p in problema.pedidos}
    vehiculos = {v.vehiculo_id: v for v in problema.vehiculos}
    errores: list[str] = []
    for ruta in solucion.rutas:
        cargados = [pedidos[p.pedido_id] for p in ruta.paradas]
        errores += _carga(ruta, vehiculos[ruta.vehiculo_id], cargados)
        errores += _ventanas(ruta, pedidos)
        errores += _jornada(ruta, problema.configuracion)
    return errores + _cobertura(problema, solucion)
