# ECL-63 / ST-037 — Medición inicial de payload y consultas críticas

**Trazabilidad:** ECL-63 / ST-037 → ECL-25 / EN-007 → RNF-012.
**Fecha:** 09/10/2026. **Base:** main `8c380fb`.
**Rama:** `docs/ECL-63-payload-consultas-criticas`.
**Estado:** análisis parcial; dashboard y rutas pendientes.

## Alcance y cobertura

Se midieron SELECT existentes del registro de pedidos y una consulta candidata,
expresamente identificada como propuesta. No se modificaron endpoints, modelos,
migraciones, índices ni arquitectura. Las optimizaciones corresponden a ST-038.

`frontend/src/pages/HomePage.tsx` presenta contenido estático y
`backend/app/main.py` no registra un router de dashboard. Los modelos y
repositorios actuales no implementan consultas de rutas optimizadas.
Las asignaciones del conductor no sustituyen esas rutas.

| Criterio | Resultado |
|---|---|
| Medir payload del dashboard sin mapa | Pendiente: funcionalidad inexistente en la base examinada |
| Verificar límite de 250 KB | No evaluable; bytes y cumplimiento son `null` |
| Analizar planes críticos | Parcial: pedidos medidos; dashboard/rutas pendientes |
| Documentar problemas y oportunidades | Tabla incluida; no se aplicaron optimizaciones |

Dependencias: ECL-15 / US-009 (dashboard), ECL-12 / US-006 y ECL-13 / US-007
(generación y reoptimización de rutas). **No se acredita completar ECL-63,
ECL-25 ni RNF-012.** Un 404, el HTML, el bundle o la respuesta de pedidos
no constituyen evidencia del payload del dashboard.

## Entorno y metodología

- PostgreSQL 16.9, PostGIS 3.5.2, Python 3.13.3.
- Contenedor local de pruebas `ecologistica-ecl48-test`; base exclusiva
  `ecologistica_ecl63_queries_test`, creada para estas mediciones.
- Migraciones actuales hasta head; índices originales y estadísticas ANALYZE.
- 100 clientes, 100,000 pedidos sintéticos: 100 días de 1,000 pedidos,
  10,000 pendientes y 90,000 entregados.
- Coordenadas idénticas y textos sintéticos; no representa selectividad
  geográfica ni una campaña de capacidad.
- Cinco ejecuciones secuenciales por SELECT con
  `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`, transacción de solo lectura y
  timeout de sentencia de 10 segundos.
- Caché no controlada; no se vaciaron buffers ni se aplicó carga concurrente.
  Los planes muestran hits en memoria y cero lecturas físicas en estas consultas.
- Mediana del tiempo de ejecución PostgreSQL; excluye planificación, red,
  autenticación, middleware, serialización, inserciones y commit.
  **No equivale a P95 HTTP ni demuestra SLA o rendimiento con concurrencia.**

## Resultados reales

| Consulta | Origen | Plan observado | Filas | Mediana |
|---|---|---|---:|---:|
| Cliente por UUID | ClienteRepository.exists | Seq Scan, 100 clientes | 1 | 0.017 ms |
| Coordenadas por UUID | PedidoRepository.coordinates | Index Scan / pedido_pkey | 1 | 0.023 ms |
| Pendientes desde 01/10 ordenados por ventana, LIMIT 50 | Candidata; sin endpoint de listado | Limit + Index Scan / idx_pedido_pendiente_ventana | 50 | 0.037 ms |

La existencia de cliente reproduce el SELECT cuando el identity map de la
sesión no lo contiene. Si está cargado, SQLAlchemy puede evitar esa consulta.
El Seq Scan no indica falta de índice: cliente_pkey existe; sobre 100 clientes
se recorrieron dos buffers y se descartaron 99 filas. No se forzó el planificador.

La consulta de coordenadas usa la PK y calcula dos valores para un pedido.
El GiST no participa en el filtro por UUID: esto no justifica eliminarlo ni
acredita consultas espaciales. La candidata usa el índice compuesto, sin Sort;
falta definir filtros y paginación estable antes de convertirla en API.
**No se detectó lentitud en estos SELECT**, sin extrapolar a otras consultas,
datos o cargas. Plan Width no equivale a bytes de JSON.

## Problemas y oportunidades para ST-038

| Hallazgo | Evidencia / efecto | Oportunidad y validación |
|---|---|---|
| Dashboard/rutas ausentes | No se pueden medir criterios completos | Completar dependencias y medir endpoints y SQL reales |
| Existencia carga cinco columnas del cliente | cliente_exists.json; el servicio utiliza un booleano | Comparar EXISTS/proyección mínima con equivalencia y datos mayores |
| Índice estado/ventana existente | Candidata usa idx_pedido_pendiente_ventana | Reutilizar según filtros reales; validar distribución y cursor estable |
| Posible crecimiento de respuestas futuras | Riesgo, no exceso de bytes medido | DTO agregado sin mapa y paginación; comparar tamaños reales |
| Compresión/caché sin beneficio cuantificado | No hay respuesta de dashboard disponible | Medir gzip, CPU, frescura e invalidación; separar por permisos |
| Joins de cliente/ruta no implementados | No hay plan para justificar índices adicionales | Revisar FK/joins al existir consultas; no crear índices preventivamente |

No se declara ahorro de bytes o mejora de velocidad sin comparaciones
antes/después. No se incorporan Redis, compresión, caché ni nuevos índices.

## Protocolo pendiente para payload y planes

1. Identificar endpoint y contrato autenticado del dashboard; registrar rol,
   filtros, dataset, versión y fecha.
2. Capturar HTTP 200, Content-Type, Content-Encoding y tamaños transferido y
   decodificado en Network. Separar tiles, geometrías y trazas del mapa.
   Si están en el mismo JSON, documentar la proyección sin mapa y conservar
   además el tamaño total transferido.
3. Medir bytes UTF-8 del JSON sin mapa. Usar provisionalmente el umbral
   conservador de 250,000 bytes (250 KB decimal); 250 KiB serían 256,000 bytes.
4. Comparar tamaño decodificado y comprimido por separado: gzip no prueba
   por sí solo que el agregado cumpla el límite.
5. Capturar EXPLAIN de las consultas efectivamente ejecutadas por dashboard
   y rutas; repetir después de optimizar. No publicar cookies, tokens,
   credenciales ni un HAR con datos personales.

## Evidencia y reproducción

- [Resultados y entorno](evidencias/ECL-63/resultados.json).
- [Plan cliente](evidencias/ECL-63/cliente_exists.json).
- [Plan coordenadas](evidencias/ECL-63/pedido_coordinates.json).
- [Plan candidato](evidencias/ECL-63/candidate_pending_window.json).
- [Fuentes y hashes](evidencias/ECL-63/fuentes.json).
- [Reproducción](evidencias/ECL-63/README.md).
- [Instrumento](scripts/measure_critical_queries.py).

Verificación local: 15 planes reales, medianas recalculadas y guardas de base
exclusiva/siembra no repetible; Ruff del instrumento.
CI y revisión humana pendientes del Pull Request.
