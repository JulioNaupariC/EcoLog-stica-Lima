# Validación ECL-60 / ST-034 — Métricas de API y base de datos

## Trazabilidad

ECL-60 / ST-034 → ECL-23 / EN-005.
Referencia: [plan de ST-033](../docs/sprint-2/plan-pruebas-capacidad.md),
RNF-007 (disponibilidad) y RNF-008 (capacidad).
Rama: `feat/ECL-60-metricas-api-bd`; base Git `ef5583b`.

## Implementación y criterios

| Criterio | Implementación | Evidencia |
|---|---|---|
| Latencias relevantes | Middleware HTTP para operaciones API e histogramas de ejecución SQL | Pruebas y exportaciones .prom |
| Solicitudes y errores 5xx | Contadores por método/ruta/estado y contador 5xx independiente | HTTP 503 y excepción 500 controlados |
| Disponibilidad API/BD | /health independiente y /health/ready con SELECT 1 | Éxito, conexión rechazada y recuperación |
| Consulta en pruebas | /metrics protegido por sesión/RBAC, sondeos JSONL | HTTP real y pruebas de permisos |

Los módulos están en `app/monitoring`. No se agregan dependencias ni servicios Docker.
Los hooks se instalan sobre cada motor de negocio y auditoría, sin modificar sus
transacciones. La comprobación de disponibilidad tiene un tercer motor de lectura
con pool limitado a una conexión, sin desbordamiento, espera de pool de 0.2 s,
conexión de 2 s y statement_timeout de PostgreSQL de 2 s.

## Métricas y privacidad

| Métrica | Tipo y dimensiones |
|---|---|
| ecolog_http_requests_total | Contador: method, route, status |
| ecolog_http_5xx_total | Contador: method, route; únicamente 500–599 |
| ecolog_http_exceptions_total | Contador: method, route |
| ecolog_http_requests_in_flight | Gauge: method, route |
| ecolog_http_request_duration_seconds | Histograma: method, route, status |
| ecolog_database_operations_total | Contador: engine, operation, outcome |
| ecolog_database_operation_duration_seconds | Histograma: engine, operation |
| ecolog_database_probes_total | Contador: outcome |
| ecolog_database_probe_duration_seconds | Histograma |
| ecolog_database_up | Último resultado observado; ausente antes del primer sondeo |
| ecolog_database_last_probe_timestamp_seconds | Timestamp del último sondeo |
| ecolog_process_start_time_seconds | Inicio del registro de métricas del proceso |

Los histogramas usan límites acumulativos de 0.005, 0.01, 0.025, 0.05, 0.1,
0.25, 0.5, 1, 2, 5, 10 segundos y +Inf, con sum y count.
Formato de texto compatible con la [exposición de Prometheus](https://prometheus.io/docs/instrumenting/exposition_formats/).
El registro usa memoria acotada por etiquetas conocidas y locks para los hilos.

Las rutas son plantillas de OpenAPI, por ejemplo /conductores/{conductor_id}.
Rutas inexistentes se agrupan como unmatched; métodos desconocidos como OTHER.
No se retienen cuerpos, queries HTTP, IDs, DNI, direcciones, cookies, contraseñas,
SQL, parámetros SQL ni mensajes de excepciones en las métricas.
Las operaciones SQL se clasifican por metadatos de SQLAlchemy en SELECT, INSERT,
UPDATE, DELETE u OTHER (incluye SQL textual), usando sus
[eventos oficiales](https://docs.sqlalchemy.org/en/20/core/events.html).

## Acceso y consulta

- GET /health conserva la respuesta de liveness existente: HTTP 200, status=ok.
- GET /health/ready devuelve HTTP 200 con database=up o HTTP 503 con database=down.
  También devuelve database_latency_seconds, sin detalles de configuración.
- GET /metrics utiliza la sesión y el permiso existente INDICADORES_CONSULTAR.
  ADMINISTRADOR, OPERADOR, ANALISTA y AUDITOR tienen acceso según la matriz actual.
  CONDUCTOR recibe 403; sin cookie y con el servicio de autenticación disponible, 401.
  Si autenticación o auditoría no están disponibles, falla de forma cerrada con 503.
- /metrics no se cuenta como tráfico HTTP de negocio. Su autenticación sí ejecuta SQL,
  incluido en las métricas de los motores; los sondeos tienen métricas independientes.
- OpenAPI incluye los nuevos endpoints y las respuestas de error.

En desarrollo local, iniciar sesión con una cuenta autorizada en la aplicación y abrir
/metrics en el mismo host. Las cookies no dependen del puerto. La API instrumentada de
esta verificación está en http://127.0.0.1:8001; la aplicación existente mantiene 5173.

Para sondear desde un proceso externo:

```powershell
python -m app.monitoring.poll --url http://127.0.0.1:8000 --interval 60
```

Ejecutar desde backend y guardar stdout en un archivo JSONL de evidencias.
`--samples 2` limita la cantidad; por defecto se ejecuta continuamente.
Cada observación registra timestamp UTC con zona, estado HTTP, latencia y disponibilidad
de ambos endpoints. AVAILABLE exige ambos HTTP 200 dentro de 5 s. Los fallos HTTP,
de transporte, timeout o cuerpo incorrecto generan UNAVAILABLE, sin mensajes sensibles.
Un agente detenido no genera observaciones: esos huecos son SIN_DATOS, nunca disponibilidad.

En Compose, después del build, se usa el mismo módulo sin instalar herramientas nuevas:

```powershell
docker compose --env-file .env exec -T backend python -m app.monitoring.poll --url http://127.0.0.1:8000 --samples 2
```

Este sondeo ocurre dentro del contenedor; registrar su ubicación. No demuestra conectividad
desde un usuario externo. El healthcheck de backend utiliza /health/ready, con timeout
HTTP de 5 s y timeout Docker de 6 s. No se cambian servicios, redes, puertos ni volúmenes.

## Interpretación para ST-035 y ST-036

Las métricas son por proceso y reinician al reiniciar la API; el entorno actual usa un
worker. Exportar periódicamente las series para conservar historia. Múltiples workers
o réplicas necesitan recolección por instancia; no atribuir agregación multiproceso.

Separar POST /pedidos con status=201 para observar registros aceptados. Los histogramas
permiten estimaciones por buckets, no un P95 exacto de cada intento. La validación del
cuerpo y persistencia, los tiempos del cliente y el P95 exacto pertenecen al generador
de ST-035. Cero tráfico no acredita latencia ni tasa de errores.

El gauge por ruta permite muestreo de POST /pedidos en vuelo. La campaña debe guardar
muestras al menos cada segundo; un valor máximo aislado no prueba concurrencia sostenida.
Cancelaciones sin respuesta se clasifican como status=no_response y no se contabilizan
como respuestas 5xx; separarlas del denominador de respuestas HTTP.

La latencia SQL cubre ejecución de cursor, no espera de pool, fetch completo ni commit.
El histograma HTTP incluye procesamiento y envío ASGI, no latencia de red del cliente.
SELECT 1 verifica conexión y lectura; no valida migraciones ni PostGIS. Para ello
se conserva `python -m app.db.check`.

Los límites de conexión y sentencia reducen bloqueos; no garantizan un deadline global
del resolver DNS o del sistema operativo. El sondeo externo aplica timeout y rechaza
resultados de más de 5 s.

La disponibilidad mensual requiere el calendario 05:00–22:00 America/Lima, sondeos
cada 60 s, mantenimiento anunciado y evaluación conservadora de SIN_DATOS del plan.
El último gauge positivo no acredita disponibilidad actual ni el SLA mensual.

## Resultados locales — 9 de octubre de 2026

- Ruff check y format --check: aprobados.
- Suite unitaria: 450 pruebas aprobadas; cobertura global 92.87%.
- API métricas, middleware HTTP, probe y main: 100% de cobertura de sentencias.
- Registro de métricas: 98.39%; hooks SQL: 96.77%; sondeo: 98.18%.
- Integración: 104 pruebas aprobadas contra PostgreSQL 16/PostGIS del contenedor
  ecologistica-ecl48-test, usando la base nueva ecologistica_ecl60_metrics_test.
- La primera base seleccionada tenía tablas y el fixture de seguridad bloqueó la corrida;
  se conservó y se creó la base nueva. No se borraron bases ni volúmenes existentes.
- HTTP real: login, consulta autorizada de métricas, denegación sin sesión, liveness,
  readiness y ejecución SQL de consulta de conductores.
- API aislada en proceso: conexión real rechazada en localhost:1, HTTP 503 de readiness,
  liveness HTTP 200 durante el fallo, recuperación HTTP 200 y excepción controlada HTTP 500.
- Compose config --quiet y build backend: aprobados.
- Imagen Docker Python 3.12.10: healthcheck API/BD healthy en contenedor temporal,
  retirado al terminar. Ver imagen y resultados en la evidencia.

Las pruebas locales unitarias/integración usan Python 3.13.3; la imagen verificada usa
Python 3.12.10, como CI. Hay avisos de deprecación existentes de Starlette/httpx/AnyIO;
no se cambiaron dependencias de otros tickets.

## Evidencias y reproducción

Ver [evidencias ECL-60](evidencias/ECL-60/README.md).
`scripts/verify_metrics.py` requiere dependencias de desarrollo y entorno local:
MONITORING_TEST_EMAIL, MONITORING_TEST_PASSWORD y opcional MONITORING_TEST_URL.
Usar cuentas sintéticas y variables privadas, nunca poner credenciales en comandos
publicables. También requiere DATABASE_URL privada para la API aislada de fallo.
El script no exporta credenciales ni datos de negocio.

```powershell
python -m pytest tests/unit -q --cov=app --cov-report=term-missing --cov-fail-under=80
python -m pytest tests/integration -q
python -m ruff check .
python -m ruff format --check .
```

Las pruebas de integración necesitan TEST_DATABASE_URL explícita, separada y con
esquema público vacío; no usar la base de desarrollo compartida.

## Estado de entrega

Instrumentación y verificaciones locales completas. Commit, PR, CI y revisión del equipo
pendientes de entrega por el usuario. No se ejecutó la campaña de 1,000 pedidos /
50 vehículos / 100 solicitudes, ni se demostró SLA mensual de 99.5%.
Esa ejecución y su informe corresponden a ST-035 y ST-036.
