# ECL-21 (EN-003) — Benchmark de extremo a extremo de RNF-001

RNF-001: una optimización del Operador con hasta 150 pedidos y 15 vehículos
termina en ≤ 45 s en el percentil 95 de 30 ejecuciones, con semilla y datos
fijos. Esta entrega cubre el **escenario 2 de EN-003 para la optimización**
(benchmark reproducible). La cola/worker (escenario 1) y la reoptimización de
RNF-002 quedan pendientes; ver [Límites](#límites-y-pendientes).

## Resultado medido

Campaña del 08/11/2026 (UTC), evidencia en
[`evidencias/ECL-21/run-2026-11-08T05-43-25Z`](<evidencias/ECL-21/run-2026-11-08T05-43-25Z/resumen.json>)
([CSV por corrida](<evidencias/ECL-21/run-2026-11-08T05-43-25Z/corridas.csv>)).

| Medida | Valor |
|---|---|
| Corridas / respuestas 201 / fallidas | 30 / 30 / 0 |
| Violaciones de restricciones duras | 0 |
| `POST /optimizaciones` P50 / **P95** / máx. | 20,137 s / **20,183 s** / 20,279 s |
| POST + detalle P95 | 20,210 s |
| Motor (duración guardada) P95 | 20,030 s |
| `GET /optimizaciones/{id}` | 0,021–0,033 s |
| Pedidos servidos / no asignados por corrida | 148 / 2 (`EXCEDE_CAPACIDAD` 1, `VENTANA_INVIABLE` 1) |
| Rutas por corrida | 8–11 |
| Ahorro de distancia frente a la ruta secuencial | 75,9 %–84,0 % |
| Cumplimiento de ventanas planificado | 100 % |
| **RNF-001 (P95 ≤ 45 s en 30 corridas)** | **Cumple** en este entorno |

Los dos no asignados son intencionales: el escenario sintético de ST-044 incluye
un pedido que excede toda la flota y otro con ventana anterior a la jornada.

## Cómo se midió

- Script: `backend/scripts/benchmark_optimizacion.py`.
- Cada corrida siembra su propio escenario con `sinteticos.escenario(150, 15,
  semilla)`. Las semillas van de 2027 a 2056.
- Se inicia sesión como un Operador sintético; la contraseña es aleatoria, se
  usa una vez y no se guarda.
- Se llama a `POST /optimizaciones` con IDs explícitos, así ningún otro dato de
  la base entra en la selección, y luego a `GET /optimizaciones/{id}`.
- Los tiempos son de reloj (`perf_counter`) desde el envío hasta la respuesta
  201, que solo llega con la corrida ya guardada en PostgreSQL/PostGIS.
- Las restricciones duras (ventanas, capacidad, sin duplicados, sin pedido
  servido y omitido) se verifican sobre la respuesta de la API.
- Los datos de cada corrida se borran al terminarla.
- Percentil por rango más cercano, la definición conservadora usada en ST-044.
- Parámetros: versión `BENCH-REFERENCIA-RN`, registrada por el script con los
  valores de referencia de RN-011/RN-012 porque la base desechable no tenía
  ninguna vigente.

Entorno: contenedor Linux 6.18 con 2 CPU, Python 3.12.3, OR-Tools 9.14.6206,
PostgreSQL 16 con PostGIS local, límite de búsqueda del motor de 20 s
(`OPTIMIZACION_TIEMPO_LIMITE_S`). Código del servicio: el de `main` tras el
merge de ECL-96 (`a75688e`); el `resumen.json` registra el commit de la rama
del benchmark (`eb53947`), que solo agrega el script y sus pruebas.

### Reproducir

Desde `backend/`, sobre una base **desechable** cuyo nombre termine en `_test`
o `_bench` y migrada a la última versión (el script rechaza otras bases y
`APP_ENV=production`):

```bash
python scripts/benchmark_optimizacion.py --corridas 30 --salida "<carpeta>"
```

El script toma `DATABASE_URL` del entorno; no escribas la contraseña en el
comando compartido. Termina con código 0 solo si se cumple RNF-001.

## Límites y pendientes

- El tiempo está dominado por el límite de búsqueda: el motor usa los 20 s
  completos y la API agrega unos 0,1–0,3 s. Con el límite actual el margen frente
  a 45 s es amplio; si se sube el límite, hay que repetir la campaña.
- Cliente en proceso (`TestClient`): no incluye latencia de red ni el servidor
  web de producción. Es una medición de la aplicación y la base, no de la red
  del laboratorio.
- Medido en el contenedor de desarrollo, no en la PC del laboratorio (ECL-68).
- RNF-002 (reoptimización, P95 ≤ 30 s) no se mide: la reoptimización (US-007)
  todavía no existe.
- Escenario 1 de EN-003 (cola/worker): pendiente. Cambiaría el `POST` de 201 a
  202 con consulta posterior; se decide con el equipo después de la demo.

[Índice del Sprint 4](README.md)

[← Volver al README principal](../../../README.md)
