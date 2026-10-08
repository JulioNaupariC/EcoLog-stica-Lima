# Plan de pruebas de capacidad y disponibilidad — Sprint 2

**Proyecto:** EcoLogística Lima  
**Trazabilidad:** ECL-59 / ST-033 → ECL-23 / EN-005; RNF-007 (rendimiento) y RNF-008 (disponibilidad).  
**Dependencias:** ECL-60 / ST-034 (instrumentación); ECL-61 / ST-035 (ejecución y evidencia).  
**Responsable del plan:** Julio Armando Naupari Camarena  
**Estado:** metodología propuesta; sin resultados de ejecución.

## 1. Objetivo y umbrales

Planificar ensayos reproducibles sobre la API FastAPI y PostgreSQL/PostGIS, con datos sintéticos y sin afectar producción.

| Indicador | Umbral |
|---|---|
| Volumen de referencia | 1,000 pedidos por día |
| Flota de referencia | 50 vehículos |
| Carga concurrente | 100 solicitudes activas |
| P95 de registro válido `POST /pedidos` | ≤ 2 segundos |
| Tasa de respuestas HTTP 5xx | < 1 % |
| Disponibilidad objetivo | ≥ 99.5 % en horario 05:00–22:00, zona `America/Lima` |

Los 1,000 pedidos/día expresan **volumen diario de negocio**; las 100 solicitudes concurrentes expresan **estrés instantáneo**. No son medidas equivalentes y se evaluarán por separado.

## 2. Herramienta y entorno reproducible

- **Herramienta prevista:** Locust (Python), con scripts versionados y versión de dependencia fijada en el entregable de ECL-61. Su ejecución aún no está implementada.
- **Entorno:** ambiente aislado de pruebas, aplicación FastAPI y PostgreSQL 16/PostGIS 3.5; registrar CPU, RAM, número de réplicas/workers, configuración de red, versión Git, fecha, semilla del generador de datos y versiones de componentes antes de cada corrida. No ejecutar contra producción.
- **Perfiles:** (A) volumen funcional de 1,000 registros válidos distribuidos dentro de una jornada simulada; (B) estrés de 100 usuarios virtuales con una operación `POST /pedidos` activa por usuario y sin tiempo de espera entre tareas, ajustando la generación de carga para verificar la simultaneidad real del lado servidor.
- **Flota:** precargar exactamente 50 vehículos sintéticos válidos en `vehiculo`, con diversidad de tipo y capacidad; verificar mediante consulta de conteo. La existencia de 50 vehículos representa dimensión de flota, **no** implica que `POST /pedidos` asigne vehículos ni los consulte durante cada solicitud.
- **Fases propuestas por repetición:** 2 minutos de calentamiento, luego 10 minutos de medición bajo 100 usuarios virtuales configurados, con tres repeticiones independientes. Mantener la fase estable y documentar ramp-up, solicitudes en vuelo, tasa de generación efectiva y limitación del generador. Si no se constatan 100 peticiones HTTP **simultáneamente activas**, declarar que se alcanzaron 100 usuarios virtuales, pero no afirmar simultaneidad de 100 solicitudes.
- **Verificación de simultaneidad:** registrar marca de inicio/fin por petición en Locust y métricas de solicitudes en vuelo del servidor instrumentadas en ECL-60; calcular y guardar el máximo, el promedio y la distribución por intervalos de un segundo. Diferenciar `usuarios virtuales=100` de `solicitudes concurrentes observadas=100`; si no coincide, ajustar el perfil y repetir.
- **Aislamiento:** ejecutar fuera de los periodos de servicio real con credenciales sintéticas; sin datos personales. Registrar desviaciones y condiciones de cada repetición.

Los tiempos/duraciones anteriores son parámetros **propuestos** del plan, no una descripción de pruebas ya realizadas.

## 3. Preparación de datos, autenticación y flujo real

1. Preparar una base de pruebas **independiente** y aplicar migraciones Alembic; comprobar `alembic current` y `alembic heads`, PostgreSQL/PostGIS y disponibilidad de la API.
2. Crear o provisionar previamente usuarios de prueba autorizados (rol `OPERADOR` o `ADMINISTRADOR`, con permiso `pedidos.crear`), clientes sintéticos persistidos y 50 vehículos. Guardar un manifiesto de IDs y semilla; no incluir contraseñas ni cookies en las evidencias.
3. Por usuario virtual iniciar sesión mediante **`POST /login`** con JSON `email` y `password`; validar respuesta satisfactoria y conservar la **cookie HttpOnly de sesión** mediante el cliente HTTP de Locust. Renovar sesión si caduca. No intentar autorizar `POST /pedidos` sin cookie válida.
4. Preparar cargas JSON válidas para **`POST /pedidos`**: `cliente_id` existente, `direccion`, `referencia` no vacía **o** latitud/longitud juntas, `peso_kg` y `volumen_m3` positivos, ventanas de tiempo con zona horaria y `ventana_fin > ventana_inicio`, `prioridad` permitida y `tipo_producto`. Generar referencias identificables por repetición, sin PII.
5. Ejecutar `POST /pedidos` y validar **HTTP 201**, JSON con `pedido_id` UUID y `cliente_id` esperado. Una respuesta 2xx distinta de 201 o un cuerpo inválido cuenta como error funcional.
6. Verificar persistencia con consultas de lectura a la base de prueba (conteo e IDs de pedidos creados) al terminar cada corrida. **No** incluir el tiempo de verificación SQL dentro del P95 HTTP de registro.
7. Al terminar cada repetición, exportar estadísticas y evidencias. Reiniciar a un estado sintético equivalente con un procedimiento controlado: usar base nueva/aislada o transacción y limpieza explícita de **solo** los pedidos sintéticos identificados por manifiesto; verificar que no queden residuos antes de la siguiente repetición. Nunca eliminar datos de producción, clientes ajenos ni volúmenes compartidos. Reponer clientes, flota y usuarios con la misma semilla.
8. Separar la preparación, el inicio de sesión, el calentamiento, el escenario de registro y la verificación posterior en los registros y métricas.

Una corrida que no crea ni persiste pedidos válidos **no puede declararse satisfactoria**, aunque sus tiempos sean bajos.

## 4. Medición, cálculos y errores

- **Población del P95:** duraciones del intercambio HTTP de `POST /pedidos` de la **fase estable**, incluyendo respuestas fallidas, timeouts y errores de conexión cuando se disponga de una duración registrada; informar además **P95 de solicitudes con HTTP 201 válido**, de forma separada. Excluir calentamiento, `POST /login`, consultas de salud y verificación SQL. Ordenar la población y tomar la observación de rango `ceil(0.95 × N)` (percentil empírico de rango más próximo); documentar N, mínimo, mediana y P95 por repetición y agregado, sin ocultar errores.
- **Tasa HTTP 5xx:** `100 × cantidad de respuestas 500–599 / total de respuestas HTTP recibidas de POST /pedidos en fase estable`. Reportar N y numerador. Las respuestas 4xx **sí** se incluyen en el denominador, pero se informan aparte como fallos funcionales/autorización/validación, no como 5xx.
- **Timeouts y errores de conexión:** no cuentan como respuestas HTTP 5xx porque no hay respuesta. Contabilizarlos aparte respecto de **intentos totales**: respuestas HTTP + intentos sin respuesta, e indicar sus duraciones/límites; cualquier ocurrencia afecta la evaluación global de ejecución.
- **Éxito funcional:** porcentaje de intentos con HTTP 201, `pedido_id` válido y persistencia comprobada. Informar fallos por categoría (4xx, 5xx, timeout, transporte, validación de respuesta, ausencia en DB).
- **Aceptación:** P95 de registro ≤2 s, errores HTTP 5xx <1 %, escenario concurrente verdaderamente medido, solicitudes funcionalmente válidas y errores de transporte/4xx analizados; no inferir éxito solo por satisfacer dos umbrales. Si se prueba una carga distinta de la objetivo, reportar la limitación explícitamente.
- **Repeticiones:** informar cada ejecución y el resultado conjunto; ninguna repetición se descarta sin motivo documentado. Conservar exportaciones de Locust, trazas del backend, métricas de ECL-60, manifiesto anonimizado y versión Git.

## 5. Disponibilidad y observación mensual

- **Periodo:** cada mes calendario completo, calculado en zona horaria `America/Lima`, con ventana operativa diaria 05:00–22:00. La evaluación parcial de horas o días se identifica como **parcial**; no acredita SLA mensual.
- **Frecuencia prevista de sondeo:** una verificación automática **cada 60 segundos** desde una ubicación de monitoreo declarada. Registrar timestamp con zona horaria, latencia, resultado HTTP y estado de conectividad a base.
- **API disponible:** respuesta HTTP 200 de `GET /health` dentro de 5 s **y** comprobación separada de conexión y lectura `SELECT 1` en PostgreSQL dentro de 5 s. El `GET /health` actual solo acredita el proceso; no acredita la base de datos. El comprobador de BD para monitoreo periódico queda pendiente de implementar en ECL-60 o en la herramienta operativa definida por el equipo.
- **Minutos disponibles:** intervalos completos del calendario operativo con ambas comprobaciones exitosas. Si hay fallo de API o BD, contabilizar indisponibilidad. Si un sondeo está ausente o el agente de monitoreo no responde, marcar `SIN_DATOS` y **no** computarlo como disponible; publicar cobertura de observación y evaluar conservadoramente esos intervalos como no disponibles hasta aclaración documentada.
- **Cálculo:** `disponibilidad (%) = 100 × minutos disponibles / minutos operativos evaluables del mes`, con los intervalos sin datos tratados conservadoramente según el punto anterior. Informar por separado minutos previstos, exitosos, fallidos, sin datos y cobertura del monitor.
- **Mantenimientos anunciados:** registrar ventana, autorización, alcance y comunicado previo. Excluirla del denominador **solo si** la política SLA aprobada y RNF aplicable permiten explícitamente la exclusión; si no existe dicha autorización, contarla como indisponibilidad. Informar tanto la disponibilidad bruta como la ajustada, y cada exclusión.
- **Criterio objetivo:** disponibilidad mensual ≥99.5 % durante la jornada. No confundir resultados de una corrida de carga o de una jornada con el SLA del mes.

## 6. Evidencias y entregables

- Script Locust, dependencias fijadas, configuración de entorno y semilla de datos (**a crear por ECL-61**).
- Manifiesto de 1,000 pedidos sintéticos/día y 50 vehículos; recuentos y verificación de persistencia.
- Registro de 100 usuarios virtuales frente a solicitudes en vuelo realmente observadas.
- Resultados por repetición y agregados: respuestas HTTP 201, 4xx, 5xx, fallos sin respuesta, percentiles y observaciones.
- Exportaciones del generador, métricas instrumentadas por ECL-60 y registro del SLA mensual, con disponibilidad/cobertura y exclusiones justificadas.
- Enlaces al PR, Jira, versión Git y declaración explícita de limitaciones.

## 7. Responsabilidades y cierre

- **Julio — ECL-59 / ST-033:** definir y revisar esta metodología; no atribuirse instrumentación o mediciones ejecutadas.
- **Antony — ECL-60 / ST-034:** instrumentar y exponer métricas de API/BD y ayudar a verificar solicitudes activas y sondeos operativos.
- **José — ECL-61 / ST-035:** implementar scripts de carga, ejecutar repeticiones y producir evidencia de resultados reales.
- **Julio — ST-036:** documentar SLA, hallazgos y respuesta operativa cuando existan datos comprobados.

**Estado de esta revisión:** únicamente **planificación metodológica**. No se ha ejecutado una campaña de carga, no se ha medido P95 ni se ha demostrado disponibilidad mensual.
