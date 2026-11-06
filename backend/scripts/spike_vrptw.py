"""ECL-93 (ST-044): measure the OR-Tools VRPTW optimizer on synthetic data.

Reproducible: the same seed generates the same orders and fleet. No database,
network or credentials are used. Examples (from ``backend/``)::

    python scripts/spike_vrptw.py
    python scripts/spike_vrptw.py --corridas 30 --salida evidencias/ECL-93/medicion.json

RNF-001 asks for <= 45 s at the 95th percentile of 30 runs with 150 orders and
15 vehicles; ``--corridas 30`` reproduces that measurement.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import ortools

from app.optimizacion.distancias import matriz_km, minutos_viaje
from app.optimizacion.modelo import Configuracion, Problema, Solucion
from app.optimizacion.sinteticos import escenario
from app.optimizacion.verificacion import violaciones
from app.optimizacion.vrptw import resolver

LIMITE_RNF001_S = 45.0
ESCENARIOS = ((150, 15), (100, 10), (50, 5))


def percentil(valores: list[float], p: float) -> float:
    """Nearest-rank percentile, the conservative definition."""
    ordenados = sorted(valores)
    rango = max(1, math.ceil(p / 100 * len(ordenados)))
    return ordenados[rango - 1]


def vecino_mas_cercano(problema: Problema, solucion: Solucion) -> dict:
    """Stronger manual reference: the dispatcher always drives to the closest
    pending order that still fits (capacity only, windows ignored). Returns
    its distance and the share of orders it would serve inside their window,
    simulated with the same speed and service time as the optimizer."""
    c = problema.configuracion
    servidos = {p.pedido_id for r in solucion.rutas for p in r.paradas}
    pedidos = [p for p in problema.pedidos if p.pedido_id in servidos]
    km = matriz_km(
        [problema.deposito, *(p.ubicacion for p in pedidos)], c.factor_desvio
    )
    pendientes = set(range(1, len(pedidos) + 1))
    disponible = [c.inicio_jornada_min] * len(problema.vehiculos)
    total, a_tiempo, v = 0.0, 0, 0
    while pendientes:
        indice = v % len(problema.vehiculos)
        vehiculo = problema.vehiculos[indice]
        v += 1
        actual, kg, m3, reloj = 0, 0.0, 0.0, float(disponible[indice])
        while True:
            opciones = [
                i
                for i in pendientes
                if kg + pedidos[i - 1].peso_kg <= vehiculo.capacidad_kg
                and m3 + pedidos[i - 1].volumen_m3 <= vehiculo.capacidad_m3
            ]
            if not opciones:
                break
            siguiente = min(opciones, key=lambda i: (km[actual][i], i))
            pedido = pedidos[siguiente - 1]
            total += km[actual][siguiente]
            reloj += minutos_viaje(km[actual][siguiente], c.velocidad_kmh)
            reloj = max(reloj, pedido.ventana_inicio_min)
            a_tiempo += reloj <= pedido.ventana_fin_min
            reloj += c.servicio_min
            kg += pedido.peso_kg
            m3 += pedido.volumen_m3
            pendientes.discard(siguiente)
            actual = siguiente
        total += km[actual][0]
        disponible[indice] = int(reloj) + minutos_viaje(km[actual][0], c.velocidad_kmh)
    return {
        "distancia_km": round(total, 3),
        "cumplimiento_ventanas_pct": round(a_tiempo / len(pedidos) * 100, 1)
        if pedidos
        else None,
    }


def sin_ventanas(problema: Problema) -> float:
    """Optimizer distance when every window spans the whole working day."""
    c = problema.configuracion
    fin = c.inicio_jornada_min + c.jornada_max_min + c.descanso_min
    libres = tuple(
        replace(p, ventana_inicio_min=c.inicio_jornada_min, ventana_fin_min=fin)
        if p.ventana_inicio_min < p.ventana_fin_min
        and p.ventana_fin_min > c.inicio_jornada_min
        else p
        for p in problema.pedidos
    )
    solucion = resolver(replace(problema, pedidos=libres))
    return solucion.comparacion.optimizada.distancia_km if solucion.comparacion else 0


def medir(pedidos: int, vehiculos: int, semilla: int, corridas: int, limite: int):
    problema = escenario(
        pedidos, vehiculos, semilla, Configuracion(tiempo_limite_s=limite)
    )
    tiempos: list[float] = []
    solucion = None
    for _ in range(corridas):
        solucion = resolver(problema)
        tiempos.append(solucion.duracion_s)
    assert solucion is not None
    comparacion = solucion.comparacion
    vecino = vecino_mas_cercano(problema, solucion)
    libre_km = sin_ventanas(problema)
    return {
        "pedidos": pedidos,
        "vehiculos": vehiculos,
        "semilla": semilla,
        "tiempo_limite_s": limite,
        "corridas": corridas,
        "tiempos_s": tiempos,
        "tiempo_max_s": max(tiempos),
        "tiempo_p95_s": percentil(tiempos, 95),
        "tiempo_mediana_s": statistics.median(tiempos),
        "cumple_rnf001": percentil(tiempos, 95) <= LIMITE_RNF001_S,
        "rutas": len(solucion.rutas),
        "pedidos_asignados": sum(len(r.paradas) for r in solucion.rutas),
        "no_asignados": [
            {"pedido_id": n.pedido_id, "motivo": n.motivo.value}
            for n in solucion.no_asignados
        ],
        "violaciones": violaciones(problema, solucion),
        "optimizada": vars(comparacion.optimizada) if comparacion else None,
        "secuencial_registro": vars(comparacion.secuencial) if comparacion else None,
        "ahorro_distancia_pct": comparacion.ahorro_distancia_pct
        if comparacion
        else None,
        "ahorro_co2_pct": comparacion.ahorro_co2_pct if comparacion else None,
        "ahorro_combustible_pct": (
            comparacion.ahorro_combustible_pct if comparacion else None
        ),
        "vecino_mas_cercano": vecino,
        "optimizada_sin_ventanas_km": libre_km,
        "ahorro_sin_ventanas_vs_vecino_pct": (
            round((vecino["distancia_km"] - libre_km) / vecino["distancia_km"] * 100, 1)
            if vecino["distancia_km"]
            else None
        ),
        "rutas_con_descanso": sum(1 for r in solucion.rutas if r.descansos),
        "duracion_max_ruta_min": max(
            (r.duracion_min for r in solucion.rutas), default=0
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semilla", type=int, default=2026)
    parser.add_argument(
        "--corridas", type=int, default=1, help="Corridas del escenario 150/15"
    )
    parser.add_argument("--limite", type=int, default=Configuracion.tiempo_limite_s)
    parser.add_argument("--salida", type=Path, help="Archivo JSON de evidencia")
    args = parser.parse_args()

    resultados = []
    for pedidos, vehiculos in ESCENARIOS:
        corridas = args.corridas if (pedidos, vehiculos) == ESCENARIOS[0] else 1
        r = medir(pedidos, vehiculos, args.semilla, corridas, args.limite)
        resultados.append(r)
        print(
            f"{pedidos:>3} pedidos / {vehiculos:>2} vehículos: "
            f"p95 {r['tiempo_p95_s']:.2f} s (máx {r['tiempo_max_s']:.2f} s, "
            f"{corridas} corrida(s)) · {r['rutas']} rutas · "
            f"{r['pedidos_asignados']} asignados · "
            f"no asignados {[n['motivo'] for n in r['no_asignados']]} · "
            f"ahorro distancia {r['ahorro_distancia_pct']} % "
            f"(vecino más cercano: {r['vecino_mas_cercano']['distancia_km']} km, "
            f"{r['vecino_mas_cercano']['cumplimiento_ventanas_pct']} % a tiempo; "
            f"sin ventanas {r['ahorro_sin_ventanas_vs_vecino_pct']} % menos) · "
            f"CO2 {r['ahorro_co2_pct']} % · violaciones {len(r['violaciones'])}"
        )

    evidencia = {
        "ticket": "ECL-93 (ST-044)",
        "medido_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "equipo": {
            "sistema": platform.platform(),
            "procesador": platform.processor() or platform.machine(),
            "nucleos_logicos": os.cpu_count(),
            "python": platform.python_version(),
            "ortools": ortools.__version__,
        },
        "configuracion": vars(replace(Configuracion(), tiempo_limite_s=args.limite)),
        "resultados": resultados,
    }
    if args.salida:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(
            json.dumps(evidencia, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Evidencia: {args.salida}")


if __name__ == "__main__":
    main()
