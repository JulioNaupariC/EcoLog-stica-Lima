# Validación ST-035 / ECL-61 — carga y disponibilidad

Ticket: [ECL-61](https://continental-team-il84x39k.atlassian.net/browse/ECL-61).
Padre ECL-23 / EN-005; referencias RNF-007/RNF-008 y
[plan ST-033](../docs/sprint-2/plan-pruebas-capacidad.md).

## Implementación

- `loadtest/campaign.py`: clúster local nuevo, migraciones/PostGIS,
  aprovisionamiento autenticado de flota y nueva base por perfil.
- `loadtest/locustfile.py`: HTTP real, cookie de sesión, generación de pedidos,
  tiempos y respuestas por intento, métricas del servidor y recursos del host.
- `loadtest/analysis.py`: población válida conciliada, rango más próximo para
  P95, denominador HTTP 5xx y comprobación conservadora de concurrencia.
- `loadtest/audit.py`: recálculo y comprobación de archivos exportados sin BD/API.
- `loadtest/report.py` y `capture.mjs`: reporte HTML y capturas desde resultados
  registrados; no contienen valores favorables inventados.
- `requirements-load.lock`: Locust 2.46.7 y dependencias fijadas, separadas del
  entorno de despliegue. El workflow CI conserva pruebas negativas y cobertura
  de las utilidades de análisis, auditoría y reporte.

## Escenario ejecutado

Base Git `468e4167c165f540668abaa5c04f0b292ef78c77`, rama
`feat/ECL-61-st035-carga-disponibilidad`, código nuevo aún sin commit durante
las mediciones. Fecha 9 de octubre de 2026. Semilla 35061.

Windows 11, Python 3.12.6, PostgreSQL 16.15, PostGIS 3.6.2, FastAPI 0.141.1,
Uvicorn 0.53.0 y Locust 2.46.7. Host de 32 CPU lógicas/24 físicas y
16,890,322,944 bytes de RAM. Una réplica/worker, pools de negocio/auditoría
separados con valores SQLAlchemy existentes (5+10 cada uno). La API, BD,
generador y sondeos comparten el equipo; no se modificó código de producción
para mejorar el resultado. Son mediciones locales de desarrollo.

Cada perfil verifica 100 usuarios OPERADOR activos, 100 clientes sintéticos,
50 vehículos activos (20 CAMIONETA, 20 FURGON y 10 MOTO), cero pedidos y cero
sesiones antes de los nuevos login. Cambian los UUID entre bases; los
manifiestos conservan las identidades reales y la misma generación lógica.

La jornada reproduce los 1,000 pedidos distribuidos por franja del plan,
comprimidos a 180 segundos. Se conservaron marcas programadas/reales por
intento y conteos horarios. No equivale a una jornada observada de 17 horas.

El estrés ejecuta tres repeticiones independientes de 60 s de subida, 120 s de
calentamiento y 600 s estables, con 100 clientes y una operación activa por
cliente. Se concilian todas las filas creadas; calentamiento, login, vehículos,
salud y consulta de métricas se separan de la población P95 de aceptación.

## Resultados

| Perfil | Intentos / válidos persistidos | P95 válido | 5xx | ≥100 solicitudes en vuelo | Resultado de carga |
|---|---:|---:|---:|---:|---|
| Jornada comprimida | 1,000 / 1,000 | 0.023460 s | 0/1,000 = 0% | No aplica al perfil diario | Volumen y franjas conciliados |
| Estrés 1 | 55,414 / 55,414 | 1.751248 s | 0/55,414 = 0% | 114/600 s (19%); 26 s sin muestra | No acreditado |
| Estrés 3 | 70,395 / 70,395 | 1.219589 s | 0/70,395 = 0% | 117/600 s (19.5%); 5 s sin muestra | No acreditado |
| Estrés 2 recuperado | 77,989 / 77,989 | 1.098492 s | 0/77,989 = 0% | 126/600 s (21%); 6 s sin muestra | No acreditado |
| Estrés 2 interrumpido, excluido del agregado | 100 / 0 en fase etiquetada estable | Sin población válida | 0/100 = 0%, con 100 respuestas 401 | Sin ventana estable evaluable | Inválido por interrupción |

**Agregado diagnóstico:** P95 **1.4970536999971955 s**, sobre **203,798** pedidos
únicos válidos y persistidos de estrés 1, estrés 3 y la recuperación. Se ordenaron
todas las duraciones; no se promediaron los P95. En las tres mediciones
terminadas hubo cero fallos funcionales/transporte y cero discrepancias de
persistencia; la auditoría recalcula esas poblaciones desde los JSONL.

Los umbrales numéricos P95 ≤2 s y 5xx <1% se cumplen en esas poblaciones
observadas. **No acreditan RNF-008 bajo la carga sostenida exigida:** la serie
del servidor no mantiene 100 solicitudes activas en todos los segundos y el
muestreador tiene retrasos. El resultado favorable de latencia es diagnóstico.

La segunda corrida original sufrió un salto de unas 6 h 45 min compatible
con suspensión/interrupción del host; hubo expiración de sesiones, 100 respuestas
401 tras el salto y 37 filas sin respuesta válida conciliada. Se conservó
íntegra en `stress2`; la recuperación independiente está en
`recovery-20261009/stress2`. No atribuir esos efectos a capacidad normal de API.

Los `campaign.json` nativos no se modificaron. La consolidación derivada está
en `campaign-20261009/campaign-consolidated.json`; `audit.json` verifica
resúmenes, IDs, horarios reales/programados, agregado e integridad SHA256.
No interpretar un código de salida 0 como aprobación de rendimiento.

La temporización inicial de Locust cerró las primeras mediciones una fracción
de segundo antes de 780 s desde el evento de inicio. La consolidación declara
una tolerancia nominal de 1 s, correspondiente a la resolución de muestreo;
no cambia los umbrales de rendimiento. El generador actualizado limita la fase
estable por reloj y reserva 1 s extra de cierre, utilizado en la recuperación.
En la jornada hubo 55 adelantos de temporizador de hasta 0.001297 s y un
retraso máximo de 0.099643 s; las 17 franjas reales mantienen exactamente los
conteos del plan. Se conservaron las marcas, y el generador actualizado vuelve
a comprobar el reloj después de esperar.

## Disponibilidad

Se sondean `/health` y `/health/ready` (lectura SELECT 1) cada segundo desde
el mismo host durante cada perfil. Los archivos guardan UTC, estados y
latencias; los resúmenes publican ventana, muestras correctas/fallidas y
huecos estimados. Los intervalos entre perfiles no se observaron y no se
presentan como disponibles ni como mantenimiento anunciado.

El porcentaje de éxito se refiere a muestras, sin certificar continuidad
entre ellas. Una ejecución de minutos y fuera/parcialmente fuera del horario
operativo no acredita el SLA mensual de 99.5%. **SLA mensual: NO MEDIDO.**

| Perfil | Sondeos correctos / totales | Intervalos correctos / esperados | Sin datos | Fallidos | Proporción conservadora de intervalos |
|---|---:|---:|---:|---:|---:|
| Jornada | 211/211 | 211/211 | 0 | 0 | 100% |
| Estrés 1 | 782/782 | 756/782 | 26 | 0 | 96.675% |
| Estrés 3 | 782/782 | 764/782 | 18 | 0 | 97.698% |
| Recuperación | 783/783 | 780/783 | 3 | 0 | 99.617% |
| Interrumpida | 151/152 | 147/24,361 | 24,213 | 1 | 0.603% |

La auditoría asigna cada sondeo al intervalo de 1 s más próximo desde la
primera observación; deduplica ráfagas de recuperación y marca fallido un
intervalo si alguna muestra falla. Estos valores estiman cobertura del sondeo
y no disponibilidad continua garantizada. Ventanas UTC exactas en el reporte
y los archivos crudos; entre perfiles queda tiempo no observado.

## Hallazgos y alcance

Se documentan en [incidencias](evidencias/ECL-61/INCIDENCIAS.md), junto con
desviaciones, evidencia y acciones sugeridas. La tarea ejecuta y verifica;
no modifica pools, arquitectura ni endpoints para corregir capacidad.

La consulta del tablero de RNF-008 depende de ECL-15: no existe ese endpoint
en la API de esta revisión y no se sustituyó por salud/flota. Aunque un
percentil individual fuera favorable, no se acredita el requisito integral
sin la concurrencia demostrada y esa cobertura funcional.

## Calidad y reproducción

Ver [loadtest/README.md](loadtest/README.md) y
[GUIA_JOSE_ST035.md](../GUIA_JOSE_ST035.md).
JUnit y cobertura están en `evidencias/ECL-61/`.
Validación final: **556 pruebas unitarias aprobadas, cobertura global 93.00%**;
gate de utilidades: **36 pruebas aprobadas, cobertura 90.99%**. El analizador
tiene 100% de cobertura. Ruff check/format y pip check aprobados. Dos avisos
de deprecación existentes de Starlette/AnyIO, sin cambio de dependencias del API.
Las pruebas unitarias del analizador cubren percentiles, límites estrictos,
5xx/4xx/timeouts, cero tráfico, identidad/persistencia, duplicados y muestras
de concurrencia ausentes o lentas. Las pruebas de evidencia detectan
alteración de resúmenes, percentiles, poblaciones, afirmaciones de SLA y hashes.

La campaña completa es local; ejecución remota de CI, PR y revisión de un
compañero quedan pendientes de que José suba la rama. No atribuir resultados
remotos a esta validación.
