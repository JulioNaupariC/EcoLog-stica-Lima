# Incidencias y límites — ST-035 / ECL-61

Este registro conserva hallazgos de pruebas; no crea ni modifica tickets Jira
y no atribuye correcciones de capacidad a ST-035.

| ID | Hallazgo / evidencia | Impacto y siguiente acción |
|---|---|---|
| ST035-01 | 100 clientes de Locust no garantizan 100 POST activos sostenidos; series `monitor.jsonl` y métrica `ecolog_http_requests_in_flight` | No acreditar RNF-008 si faltan muestras o hay valores <100. Evaluar ajuste explícito de clientes/tasa y repetir en un host dedicado; conservar las corridas previas. |
| ST035-02 | El muestreo autenticado de métricas puede retrasarse durante carga; se conservan inicio, latencia, lag y huecos | No completar huecos con valores favorables ni atribuir exclusivamente a CPU del generador. Revisar contención de API/BD y separar observador/generador; no se cambiaron pools ni permisos. |
| ST035-03 | El tablero ECL-15 no está expuesto en la API de esta revisión | Consulta de tablero pendiente para la cobertura integral de RNF-008; salud y flota no la sustituyen. |
| ST035-04 | Jornada comprimida a 180 s y disponibilidad observada solo durante ventanas cortas del ambiente local | No equivale a 17 h reales ni acredita SLA mensual. Requiere monitoreo del calendario operativo completo, cobertura y mantenimientos anunciados trazables. |
| ST035-05 | PostGIS local 3.6.2, frente a la versión 3.5 prevista en el plan/Compose; API, BD y carga comparten recursos de Windows | Los resultados pertenecen a este entorno; repetir en la infraestructura objetivo antes de extrapolar capacidad. |
| ST035-06 | Primera preparación: Windows rechazó el token restringido de initdb dentro del sandbox. Segunda: faltaba habilitar geography/PostGIS antes de migrar | Resuelto para la ejecución: clúster local autorizado y extensión creada antes de Alembic. Se conservaron los diagnósticos `smoke`/`smoke2`; no se tocaron bases compartidas. |

La corrida `stress2` sufrió un salto de unas 6 h 45 min entre observaciones,
compatible con suspensión/interrupción del host. Tras el salto vencieron las
sesiones: 100 respuestas 401 en la fase etiquetada estable, fuera de su ventana
programada; no hubo población P95 válida. Se observaron 37 filas sin respuesta
válida conciliada durante la interrupción. Corrida inválida, conservada íntegra.
No atribuir esas latencias/401 a capacidad normal ni interpretar el intervalo
sin datos como disponible. Se añadió una solicitud temporal de impedir
suspensión automática y selección de perfiles para repetir en una base nueva.
La causa exacta del salto del equipo no se ha diagnosticado (ST035-07).

Se finalizaron tres mediciones de estrés (1, 3 y recuperación de 2), con P95 de
1.751248, 1.219589 y 1.098492 s, y 0% de 5xx. El agregado diagnóstico es
1.497054 s sobre 203,798 registros válidos persistidos. No se acredita carga
sostenida de 100 solicitudes: solo 19%, 19.5% y 21% de segundos con muestras
≥100. El dashboard y el SLA mensual siguen fuera de la evidencia disponible.

ST035-08: la jornada conserva 55 adelantos del temporizador de hasta 1.297 ms
y retraso máximo de 99.643 ms. El conteo por las franjas reales sigue siendo
exactamente el plan de 1,000 pedidos. El script actualizado revalida el reloj
tras esperar; no se modificaron los registros originales. Locust cerró las
primeras ventanas unas décimas antes del tiempo nominal desde test_start;
se declaró tolerancia de muestreo de 1 s y se añadió un segundo de cierre con
límite explícito de fase en la recuperación. No se relajaron P95/5xx/concurrencia.

Consultar [VALIDACION_ST035.md](../../VALIDACION_ST035.md) y el reporte para
todos los denominadores, huecos y condiciones. No se seleccionaron únicamente
los segmentos favorables dentro de una repetición.
