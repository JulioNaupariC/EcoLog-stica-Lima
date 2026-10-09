# ECL-64 / ST-038 — Optimización justificada de consultas

**Trazabilidad:** ECL-64 / ST-038 → ECL-25 / EN-007 → RNF-012.
**Base Git:** `bc512a5`. **Fecha:** 09/10/2026.
**Rama:** `feat/ECL-64-optimizacion-api-consultas`.
**Estado:** incremento parcial validado; dashboard y rutas siguen pendientes.

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

- [Análisis de partida ST-037](INFORME_ST037.md).
- [Comparación y 80 planes](evidencias/ECL-64/comparacion.json).
- [Registro de verificación y hashes](evidencias/ECL-64/verificacion.json).
- [Instrucciones de evidencia](evidencias/ECL-64/README.md).
- [Instrumento](scripts/compare_client_lookup.py).
