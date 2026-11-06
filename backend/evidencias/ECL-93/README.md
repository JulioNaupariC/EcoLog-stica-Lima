# Evidencias ECL-93 / ST-044: spike del optimizador VRPTW

Prueba técnica previa a US-006 (riesgo R-01, RES-06): ¿resuelve OR-Tools un
VRPTW de 150 pedidos y 15 vehículos en ≤ 45 s respetando capacidad, ventanas y
jornada?

**Decisión: seguir con OR-Tools** (`ortools==9.14.6206`) para ST-047, con un
límite de búsqueda de 20 s. Los datos son sintéticos; los límites están al
final.

## Medición

Se midió en dos equipos con el mismo comando
(`python scripts/spike_vrptw.py --corridas 30 --salida …`), semilla 2026 y límite
de búsqueda de 20 s.

### Laptop de desarrollo (criterio del ticket)

- **Archivo:** [medicion-laptop.json](medicion-laptop.json), medido el 06/11/2026 por Antony Munive.
- **Equipo:** Windows 11 (10.0.26200), procesador AMD64 Family 25 Model 117 (AuthenticAMD), 16 núcleos lógicos, Python 3.12.10. El script no registra la RAM.

| Escenario | Corridas | p95 | Máximo | Rutas | Asignados | No asignados | Violaciones |
|---|---|---|---|---|---|---|---|
| 150 pedidos / 15 vehículos | 30 | 20,04 s | 20,04 s | 11 | 148 | 2 | 0 |
| 100 pedidos / 10 vehículos | 1 | 20,02 s | 20,02 s | 6 | 98 | 2 | 0 |
| 50 pedidos / 5 vehículos | 1 | 20,00 s | 20,00 s | 4 | 48 | 2 | 0 |

En la laptop la solución de 150 / 15 recorre 226,5 km: 79,0 % menos distancia y 82,7 % menos CO₂ que la ruta secuencial.

### Entorno de desarrollo en la nube

- **Archivo:** [medicion-entorno-nube.json](medicion-entorno-nube.json), medido
  el 06/11/2026.
- **Equipo:** Linux, 2 núcleos lógicos x86_64, Python 3.12.3.

| Escenario | Corridas | p95 | Máximo | Rutas | Asignados | No asignados | Violaciones |
|---|---|---|---|---|---|---|---|
| 150 pedidos / 15 vehículos | 30 | 20,02 s | 20,03 s | 11 | 148 | 2 | 0 |
| 100 pedidos / 10 vehículos | 1 | 20,01 s | 20,01 s | 6 | 98 | 2 | 0 |
| 50 pedidos / 5 vehículos | 1 | 20,01 s | 20,01 s | 3 | 48 | 2 | 0 |

- **RNF-001 cumplido en los dos equipos:** p95 de 30 corridas ≤ 45 s (20,04 s en la laptop y 20,02 s en la nube). El tiempo lo
  marca el límite de búsqueda. La primera solución factible sale en 0,5 s
  (400,0 km) y la búsqueda local la baja a 226,5 km en 10 s y a 222,7 km en 20 s.
  Un equipo más lento llega al mismo tiempo, con una solución algo peor, nunca
  más tarde.
- **No asignados:** en cada escenario hay 2 pedidos inviables a propósito. Uno de
  3 500 kg sale como `EXCEDE_CAPACIDAD` y otro con ventana de 05:00 a 06:00 sale
  como `VENTANA_INVIABLE`. El resto de la solución no se altera (RF-006, ruta
  infeliz).
- **Violaciones:** `app/optimizacion/verificacion.py` recalcula carga, ventanas,
  jornada y descansos sin confiar en el solver.
- **Descansos (RN-005):** en el escenario de 150 pedidos, 6 rutas pasan de 4 h e
  incluyen su descanso de 1 h; la más larga dura 320 min.

## Ahorro

**Frente a la ruta secuencial documentada** (orden de registro, mismos pedidos
atendidos):

| Escenario | Distancia optimizada | Distancia secuencial | Ahorro en distancia | Ahorro en CO₂ | Ahorro en combustible |
|---|---|---|---|---|---|
| 150 / 15 | 222,7 km | 1 077,2 km | 79,3 % | 83,1 % | 83,1 % |
| 100 / 10 | 168,1 km | 721,2 km | 76,7 % | 80,4 % | 80,4 % |
| 50 / 5 | 103,9 km | 394,1 km | 73,6 % | 73,6 % | 73,6 % |

El criterio del Acta (≥ 10 %) y el del ticket (≥ 18 %) se cumplen con holgura,
pero **esa cifra no debe presentarse sola**. La referencia secuencial es débil:
recorre los pedidos en el orden en que se registraron, cruzando distritos. El
ahorro en CO₂ es mayor que el de distancia porque el optimizador también elige
el vehículo (objetivo Green VRP).

**Frente a una referencia más exigente.** Un despachador que siempre va al
pedido pendiente más cercano que aún cabe recorre solo 183,9 km en el escenario
de 150, porque ignora las ventanas. Con eso, solo atiende a tiempo el 35,8 % de
los pedidos. El optimizador recorre más (222,7 km) porque cumple el 100 % de
las ventanas.

**En igualdad de condiciones** (todas las ventanas abiertas todo el día), el
optimizador recorre:

- 140,6 km, 23,5 % menos que el vecino más cercano, en el escenario 150 / 15;
- 27,5 % menos en el escenario 100 / 10;
- 26,0 % menos en el escenario 50 / 5.

**Conclusión:**

- El ahorro real dependerá de cómo planifica hoy DistriRápido; con datos reales
  será bastante menor que el 79 %.
- Para la Review conviene mostrar tres cifras: el ahorro frente a la ruta
  secuencial, el cumplimiento de ventanas y la comparación con el vecino más
  cercano.

## Modelo

- **Restricciones duras:**
  - capacidad en kg y m³ (RN-003);
  - ventanas de tiempo (RN-006);
  - jornada de 8 h y descanso obligatorio de 1 h tras 4 h continuas (RN-005),
    con el servicio y la espera contados como conducción.
- **Objetivo:** kg de CO₂, más una penalidad por pedido omitido según su
  prioridad (RN-007). Un minuto de jornada desempata, para evitar esperas largas.
- **Búsqueda:** `PATH_CHEAPEST_ARC` como primera solución y `GUIDED_LOCAL_SEARCH`.
  Con `PARALLEL_CHEAPEST_INSERTION` la búsqueda ocupaba 17 s antes de mejorar y
  terminaba en 245 km; con `PATH_CHEAPEST_ARC` termina en 222,7 km.
- **Hallazgo técnico:** con el descanso **opcional**, OR-Tools no encuentra rutas
  de más de 4 h y descarta pedidos. Por eso el descanso se modela como
  obligatorio: si la ruta es corta, cae fuera de ella. Hay una prueba que lo
  cubre (`test_long_day_includes_the_rn005_break`).

## Límites (no declarados como cumplidos)

- **Datos sintéticos, no de la empresa:**
  - coordenadas aleatorias en cajas aproximadas de los 4 distritos;
  - depósito supuesto en Santa Anita;
  - flota típica de 6 furgones, 7 camionetas y 2 motos;
  - factores de CO₂ derivados de 2,68 y 2,31 kg CO₂/L.
- **Distancias:** Haversine × 1,35 a 20 km/h, sin tráfico ni red vial real. RES-06
  y SUP-04 siguen abiertos hasta tener un proveedor de mapas.
- **Ejecución:** la optimización corre en el mismo proceso. Desacoplarla y
  automatizar la prueba de rendimiento es EN-003 (ECL-21).
- **Parámetros:** EN-008 (ECL-26) los reemplaza por valores versionados con
  fuente.

## Reproducción

No usa base de datos, red ni credenciales. Desde `backend/`, con
`requirements-dev.lock` instalado:

```powershell
python scripts/spike_vrptw.py
python -m pytest tests/unit/test_optimizacion_vrptw.py -q
```

[← Volver al README principal](../../../README.md)
