# ECL-64 / ST-038 — Optimización justificada de consultas

**Trazabilidad:** ECL-64 / ST-038 → ECL-25 / EN-007 → RNF-012.
**Base Git:** `bc512a5`. **Fecha:** 09/10/2026.
**Rama:** `feat/ECL-64-optimizacion-api-consultas`.
**Estado:** actualizado el 13/10/2026: el Inicio cumple el límite de 250 KB con regresión en CI; consultas de rutas pendientes de US-006 (ver la última sección).

## Cambio implementado

El hallazgo de ST-037 indica que ClienteRepository.exists recuperaba cinco
columnas del perfil para devolver únicamente un booleano. Ahora se ejecuta
SELECT EXISTS filtrado por cliente_id y se devuelve ese booleano.
El perfil del cliente no se carga ni se introduce en el identity map.

El servicio de pedidos mantiene su contrato y transacción, validación de
cliente, errores sanitizados, restricciones de persistencia, RBAC y auditoría.
No cambian endpoints, esquemas HTTP ni OpenAPI. Tampoco cambia la respuesta
de registro de pedidos.

La consulta verifica el estado actual en la base. Session.get podía reutilizar
una entidad ya cargada en la sesión; EXISTS consulta la base cada vez.
El servicio de registro abre su propia sesión y realiza una comprobación por
pedido. No se aplica una caché de existencia que pudiera quedar obsoleta.
La prueba de integración comprueba cliente existente, UUID ausente, ausencia
de hidratación y eliminación posterior visible en la misma sesión.

## Comparación antes/después

Se reutilizó la base sintética aislada de ST-037 con 100 clientes y 100,000
pedidos, sin modificar sus datos. PostgreSQL 16.9, Python 3.13.3.
El instrumento captura el SQL real emitido por Session.get y por el repositorio
actual; ejecuta 20 pares por caso, alternando el orden antes/después.

Se conservaron 80 planes EXPLAIN ANALYZE BUFFERS JSON. Las medianas son tiempos
de ejecución PostgreSQL, sin planificación, red, ORM, HTTP ni concurrencia.
No se vació la caché; los resultados no representan una prueba de capacidad.

| Medida | Antes | Después | Interpretación |
|---|---:|---:|---|
| Campos del resultado SQL | 5 del perfil | 1 booleano | Se elimina la recuperación del perfil |
| Suma de tamaños internos de los valores para el cliente existente | 58 bytes | 1 byte | pg_column_size; excluye protocolo y cabeceras |
| Mediana con cliente existente | 0.011 ms | 0.011 ms | Sin mejora de latencia demostrada |
| Mediana con UUID ausente | 0.0115 ms | 0.012 ms | Diferencia pequeña; no se declara aceleración |
| Resultado funcional existente / ausente | true / false | true / false | Compatible |
| Payload HTTP del dashboard | No medido | No medido | Funcionalidad ausente; cumplimiento null |

Los tamaños internos NO son bytes transferidos por la red ni tamaño JSON.
La reducción cuantificada corresponde a los valores seleccionados en este
dataset; no se extrapola a todas las peticiones. Para el UUID ausente,
EXISTS devuelve una fila false, mientras el SELECT previo no devuelve filas.
El beneficio acreditado es minimización de datos del perfil, no mayor velocidad.

## Decisiones sobre índices, respuestas, paginación y caché

| Técnica | Decisión y justificación |
|---|---|
| Proyección mínima | Implementada: EXISTS devuelve solo el resultado requerido por el servicio |
| Índice cliente_id | Se conserva cliente_pkey; en 100 clientes un Seq Scan puede ser más barato. No se fuerza el planificador ni se duplica la PK |
| Índice pedido_id | Se conserva pedido_pkey, utilizado por coordenadas en ST-037 |
| Estado / ventana | Se conserva idx_pedido_pendiente_ventana, utilizado por la candidata de ST-037; el listado real no existe aún |
| Índice espacial | Se conserva GiST de ubicación; una búsqueda por UUID no justifica eliminarlo |
| Nuevos índices | No aplicados: ST-037 no detectó una consulta lenta ni joins reales que los justifiquen |
| Agregación / paginación del dashboard | Pendiente de su endpoint y contrato; no se sustituyen por pedidos o asignaciones |
| Compresión HTTP | Pendiente de medición real de payload, CPU y tamaño decodificado; no se modifica middleware global sin beneficio acreditado |
| Caché con vigencia | Pendiente de una consulta costosa y reglas de frescura/invalidez/permisos; no se cachean perfiles ni autorización |
| Arquitectura | No se añaden Redis, servicios, migraciones o configuraciones Docker |

## Verificación funcional

- 556 pruebas unitarias aprobadas.
- Cobertura de app/repositories/clientes.py: 100%, superior al 80% requerido.
- Regresión de integración: 116 aprobadas y una omitida por falta de DATABASE_URL.
- La prueba omitida de PostgreSQL/PostGIS se ejecutó por separado con una
  conexión explícita de pruebas y aprobó: 117 pruebas de integración verificadas.
- Las pruebas destructivas usaron una base nueva exclusiva
  ecologistica_ecl64_regression_test; no se alteró la semilla de ST-037.
- Ruff aprobado para los cuatro archivos Python afectados.
- Medianas recalculadas desde los planes y equivalencia funcional comprobada.
- Frontend no modificado; no se volvió a ejecutar su suite.
- CI, SAST y revisión humana del nuevo incremento pendientes del PR.

Comandos desde backend (URLs privadas de pruebas, nunca producción):

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m pytest tests/unit --cov=app.repositories.clientes --cov-report=term-missing --cov-fail-under=80 -q
python -m pytest tests/integration -q
python scripts/compare_client_lookup.py --output evidencias/ECL-64-repeticion
```

La comparación exige DATABASE_URL de ecologistica_ecl63_queries_test,
preparada según ST-037, y solo ejecuta SELECT en una transacción de solo lectura.
La regresión exige TEST_DATABASE_URL de otra base vacía con nombre terminado
en _test. La prueba de PostGIS utiliza DATABASE_URL de pruebas.
Usar carpetas de salida distintas para preservar esta evidencia.

## Criterios pendientes y evidencia

Se reducen datos consultados y se conservan las funcionalidades comprobadas.
Se documentan índices y resultados antes/después. **El límite de 250 KB del
dashboard sigue sin evaluarse**, al faltar ECL-15 / US-009. Las consultas
de rutas dependen de ECL-12 / US-006 y ECL-13 / US-007.

No se acredita finalizar ECL-64, ECL-25 ni RNF-012. Al disponer del dashboard,
seguir el protocolo de ST-037: medir JSON UTF-8 sin mapa, bytes comprimidos y
decodificados por separado, comparar con 250,000 bytes y obtener sus planes
reales antes de decidir agregación, caché, paginación o índices adicionales.

- [Análisis de partida ST-037](../informes/INFORME_ST037.md).
- [Comparación y 80 planes](../../../../backend/evidencias/ECL-64/comparacion.json).
- [Registro de verificación y hashes](../../../../backend/evidencias/ECL-64/verificacion.json).
- [Instrucciones de evidencia](../../../../backend/evidencias/ECL-64/README.md).
- [Instrumento](../../../../backend/scripts/compare_client_lookup.py).

## Corrección N+1 del listado de conductores — 13/10/2026

**Defecto:** `ConductorService.list_page` llamaba a `session.get(Usuario, …)`
por cada fila para calcular `habilitado_asignacion`, lo que generaba una
consulta adicional por conductor.

**Cambio:** `ConductorRepository.list_page` obtiene cada conductor y su cuenta
en una sola sentencia (`SELECT conductor, usuario … LEFT OUTER JOIN usuario`),
y el servicio calcula la elegibilidad con la cuenta ya cargada. El contrato
HTTP de `GET /conductores` no cambia: mismos campos, orden y paginación.

**Medición:** sentencias contadas con `before_cursor_execute` sobre la llamada
al servicio, con 105 conductores sembrados. Entorno local: PostgreSQL 16.15 +
PostGIS 3.6.2, Windows 11, Python 3.12.10.

| `page_size` | Filas devueltas | Sentencias antes | Sentencias después |
|---:|---:|---:|---:|
| 20 | 20 | 22 | 2 |
| 100 | 100 | 102 | 2 |

Las dos sentencias restantes son el `COUNT(*)` del total y la página con el
join.

**Prueba de regresión:**
[`test_conductor_list_queries.py`](../../../../backend/tests/integration/test_conductor_list_queries.py)
exige como máximo 3 sentencias por página, sea cual sea `page_size`. Cubre:

| Tipo de ruta | Escenario | Resultado |
|---|---|---|
| Dorada | 25 conductores elegibles, página 1 de 20 | 20 habilitados, ≤ 3 sentencias |
| Feliz | `page_size` 1, 20 y 100 sobre 105 conductores | ≤ 3 sentencias en los tres casos |
| Infeliz | 5 conductores con cuenta `INACTIVO` | Ninguno habilitado, ≤ 3 sentencias |
| Borde | Tabla vacía, última página parcial (21 → página 2) y página fuera de rango | 0, 1 y 0 filas; ≤ 3 sentencias |

Con el código anterior, 4 de los 8 casos fallan: todos los que devuelven 3 o
más filas.

Esta corrección no cambia el estado de ECL-64, ECL-25 ni RNF-012, que siguen
dependiendo del dashboard según la sección anterior.

## Indicadores agregados del Inicio — 13/10/2026

**Problema verificado:** el Inicio descargaba `GET /vehiculos` completo (sin
paginación) solo para contar, y `GET /conductores?page_size=100` para contar
habilitados en el navegador. Con 200 conductores mostraba «72 habilitados
(primeros 100)» cuando había 145.

**Cambio:** `GET /indicadores/operacion` (api → servicio → repositorio) devuelve
solo agregados calculados en SQL con `COUNT`/`SUM … FILTER` y un `GROUP BY` de
pedidos por estado y prioridad. La elegibilidad usa la misma regla que
`habilitado_asignacion`: conductor ACTIVO, cuenta CONDUCTOR ACTIVA, licencia
vigente en Lima y disponibilidad no vencida. Protegido con
`indicadores.consultar` de alcance general: el conductor (alcance propio)
recibe 403. Errores saneados a 503 y OpenAPI actualizado. El Inicio hace una
sola petición.

**Vigencia:** `Cache-Control: private, max-age=30`. Las cifras informan el
Inicio, no deciden asignaciones; 30 s acotan la desactualización y evitan
repetir la agregación al navegar. La respuesta incluye `generado_en` y la
interfaz muestra la hora. No se comprime: 347 bytes no lo justifican.

**Medición:** dataset ficticio de 50 vehículos, 200 conductores y 30 000 pedidos
(30 días × 1 000) en `ecologistica_ecl25_test`; PostgreSQL 16.15 + PostGIS
3.6.2, Python 3.12.10.

| Medida | Antes | Después |
|---|---:|---:|
| Peticiones del Inicio | 2 | 1 |
| Bytes UTF-8 del JSON | 35 871 (11 775 + 24 096) | 347 |
| Sentencias SQL | 3 + 4 | 5 (sesión, autorización y 3 agregados) |
| Conductores habilitados mostrados | 72 de los primeros 100 | 145 de 200 |

| Consulta agregada | Plan sin índice nuevo | Plan con la migración 0011 |
|---|---|---|
| Vehículos | Seq Scan, 1 buffer, 0,04 ms | Igual (50 filas) |
| Conductores | Hash Left Join con usuario, 9 buffers, 0,17 ms | Igual (200 filas) |
| Pedidos por estado y prioridad | Seq Scan, 721 buffers, 8,67 ms | Index Only Scan, 28 buffers, 3,66 ms |

Tiempos: mediana de 5 ejecuciones de `EXPLAIN (ANALYZE, BUFFERS)`.

**Decisión sobre índices:** se crea `idx_pedido_estado_prioridad (estado,
prioridad)` en la migración 0011, porque el plan pasa de leer la tabla completa
a un index-only scan con 25 veces menos buffers. Coste: 224 kB y una entrada de
B-tree por pedido (unos 1 000 al día). Vehículos y conductores no llevan índice:
son tablas de decenas o cientos de filas y el seq scan cuesta menos de 0,2 ms.

**Consultas de rutas:** no aplica hasta US-006 (ECL-12); justificación
documentada: no existen tablas ni consultas de rutas optimizadas que revisar. Se
revisarán con el mismo protocolo cuando existan.

**Regresión en CI:**
[`test_indicadores_operacion.py`](../../../../backend/tests/integration/test_indicadores_operacion.py)
siembra el dataset y exige payload ≤ 250 000 bytes y exactamente 5 sentencias SQL,
iguales con la base vacía y con 30 000 pedidos.

| Tipo de ruta | Escenario | Resultado |
|---|---|---|
| Dorada | Administrador con el dataset completo | Agregados exactos, 347 bytes, 5 sentencias, sin datos personales |
| Feliz | Operador, analista y auditor | 200 |
| Infeliz | Sin sesión, conductor y fallo de base | 401, 403 y 503 saneado sin `Cache-Control` privado |
| Borde | Base vacía; 200 conductores frente al listado paginado; licencia que vence hoy y disponibilidad terminada | Ceros; mismo total de habilitados que `habilitado_asignacion`; solo cuenta la licencia vigente con disponibilidad abierta |

La US-009 (indicadores de sostenibilidad, ECL-15) debe ampliar este mismo
endpoint en lugar de crear otro y mantener la prueba de 250 KB.

- [Evidencias y reproducción](../../../../backend/evidencias/ECL-25-inicio/README.md).
- [Medición antes](../../../../backend/evidencias/ECL-25-inicio/medicion-antes.json), [después sin índice](../../../../backend/evidencias/ECL-25-inicio/medicion-despues-sin-indice.json) y [después](../../../../backend/evidencias/ECL-25-inicio/medicion-despues.json).
- [Instrumento](../../../../backend/scripts/measure_home_payload.py) y [dataset](../../../../backend/scripts/indicadores_dataset.py).

[↑ Índice del Sprint 2](../README.md)

[← Volver al README principal](../../../../README.md)
