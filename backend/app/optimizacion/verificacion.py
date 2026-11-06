"""Independent check of a solution against the hard constraints.

It does not trust the solver: it recomputes loads, windows, working day and
breaks from the solution itself. Used by the tests and by the spike script.
"""

from app.optimizacion.modelo import Problema, Solucion


def violaciones(problema: Problema, solucion: Solucion) -> list[str]:
    c = problema.configuracion
    pedidos = {p.pedido_id: p for p in problema.pedidos}
    vehiculos = {v.vehiculo_id: v for v in problema.vehiculos}
    errores: list[str] = []
    vistos: list[str] = []

    for ruta in solucion.rutas:
        vehiculo = vehiculos[ruta.vehiculo_id]
        cargados = [pedidos[p.pedido_id] for p in ruta.paradas]
        vistos.extend(p.pedido_id for p in ruta.paradas)
        kg = sum(p.peso_kg for p in cargados)
        m3 = sum(p.volumen_m3 for p in cargados)
        if kg > vehiculo.capacidad_kg + 1e-9:
            errores.append(f"{ruta.vehiculo_id}: {kg:.2f} kg > capacidad")
        if m3 > vehiculo.capacidad_m3 + 1e-9:
            errores.append(f"{ruta.vehiculo_id}: {m3:.3f} m3 > capacidad")
        for parada in ruta.paradas:
            pedido = pedidos[parada.pedido_id]
            if (
                not pedido.ventana_inicio_min
                <= parada.eta_min
                <= pedido.ventana_fin_min
            ):
                errores.append(f"{parada.pedido_id}: llegada fuera de ventana")
        etas = [p.eta_min for p in ruta.paradas]
        if etas != sorted(etas):
            errores.append(f"{ruta.vehiculo_id}: secuencia no cronológica")
        if ruta.salida_min < c.inicio_jornada_min:
            errores.append(f"{ruta.vehiculo_id}: sale antes del inicio de jornada")
        descanso = sum(d.duracion_min for d in ruta.descansos)
        if ruta.duracion_min - descanso > c.jornada_max_min:
            errores.append(f"{ruta.vehiculo_id}: excede la jornada")
        if ruta.duracion_min > c.conduccion_continua_max_min:
            if not ruta.descansos:
                errores.append(f"{ruta.vehiculo_id}: más de 4 h sin descanso")
            else:
                d = ruta.descansos[0]
                antes = d.inicio_min - ruta.salida_min
                despues = ruta.regreso_min - (d.inicio_min + d.duracion_min)
                if d.duracion_min < c.descanso_min or max(antes, despues) > (
                    c.conduccion_continua_max_min
                ):
                    errores.append(f"{ruta.vehiculo_id}: tramo continuo > 4 h")

    no_asignados = [n.pedido_id for n in solucion.no_asignados]
    if len(vistos) != len(set(vistos)):
        errores.append("Un pedido aparece en más de una parada")
    if sorted(vistos + no_asignados) != sorted(pedidos):
        errores.append("Pedidos asignados + no asignados no cuadran con la entrada")
    return errores
