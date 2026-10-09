# Evidencias ECL-60 / ST-034

Trazabilidad: ECL-60 → ECL-23 / EN-005.
[Validación técnica](../../VALIDACION_ST034.md).

| Archivo | Origen y significado |
|---|---|
| [metricas.prom](metricas.prom) | GET /metrics HTTP real tras login y consulta de conductores; datos sintéticos locales |
| [sondeos.jsonl](sondeos.jsonl) | Dos observaciones HTTP inmediatas de API/BD disponibles; no son una campaña cada 60 segundos |
| [metricas-fallos-controlados.prom](metricas-fallos-controlados.prom) | API separada en proceso: conexión BD rechazada, recuperación y excepción HTTP 500 sintética |
| [resultados.json](resultados.json) | Resultados y verificación de imagen Docker/healthcheck |

El fallo se aplica únicamente al motor de sondeo de una API aislada.
No se detuvo PostgreSQL ni la aplicación existente para producir las evidencias.
No se incluyen cuerpos de conductores, cookies, contraseñas ni URLs de conexión.

450 pruebas unitarias y 104 de integración aprobadas. La verificación Docker arrancó
una imagen del backend con Python 3.12.10, comprobó healthy y retiró ese contenedor
temporal. Se conservaron el contenedor de BD y sus bases.

Reproducción: scripts/verify_metrics.py y app.monitoring.poll, según la validación.
Estas evidencias verifican instrumentación; no acreditan campaña de capacidad ni SLA mensual.
