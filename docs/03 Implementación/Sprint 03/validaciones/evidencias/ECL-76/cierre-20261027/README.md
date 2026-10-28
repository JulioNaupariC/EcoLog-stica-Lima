# ECL-76 — Campaña real del 27/10/2026

Fecha real: **27/10/2026**, `America/Lima`. Base de código:
`cac7a034e5966e5d5517c6324e2ec850a5d7fa90` más la corrección del script E2E.
El [manifiesto](manifest.json) contiene el hash SHA-256 del script ejecutado,
los contadores de JUnit y las coberturas. No se atribuye la ejecución al commit
posterior que incorpora los resultados.

## Resultados

| Comprobación | Resultado real | Evidencia |
|---|---|---|
| Backend unitario, Python 3.12.10 y lock | 868 aprobadas, cobertura 92,81 %, 0 omitidas | [JUnit](backend-unit.xml), [consola](backend-console.txt) |
| Integración PostgreSQL/PostGIS | **250 aprobadas**, 0 fallos/errores/omitidas | [JUnit](backend-integration.xml), [consola](backend-console.txt) |
| Frontend Linux, Node 22.18.0 y lock | 732 aprobadas en 50 archivos, 0 omitidas | [JUnit](frontend-tests.xml), [consola](frontend-console.txt) |
| Cobertura frontend | Líneas 97,71 %, ramas 92,95 %, sentencias 95,56 %, funciones 94,96 %; supera los umbrales globales del 80 % | [Consola](frontend-console.txt), [manifiesto](manifest.json) |
| Typecheck, ESLint, build, sintaxis E2E | Aprobados | [Consola frontend](frontend-console.txt) |
| Ruff check y format | Aprobados; 212 archivos conformes | [Consola backend](backend-console.txt) |
| Chrome 156.0.8078.48 / Chromium | **10/10** offline, recarga, itinerario y reconexión; un alta online adicional | [Resultado completo](../run-2026-10-27T21-30-35-858Z/results.json) |
| Firefox 142.0.1 | **10/10** offline, recarga, itinerario y reconexión; un alta online adicional | [Resultado completo](../run-2026-10-27T21-30-35-858Z/results.json) |
| Respuesta perdida y replay | En la primera ronda de cada navegador, 201 persistido cuya respuesta se pierde, seguido de 200 y el mismo acuse; replay explícito 200 en las 20 rondas | [JSON](browser-results.json) |
| Unicidad y auditoría en base real | **22 operaciones, 22 incidencias y 22 trazas de alta**; exactamente una de cada por operación | [Consulta de solo lectura](persistence.json), [script usado](check-persistence.py) |

Docker Engine 29.9.2; imágenes base fijadas por digest en Compose y Dockerfile;
PostgreSQL 16 / PostGIS 3.5. El detalle espacial y versión PostgreSQL está en
`persistence.json`. Base demo `ecologistica_ecl76_demo`, base de integración
independiente `ecologistica_ecl76_test`; nunca se ejecutaron pruebas destructivas
contra la demo. Las migraciones demo `current` y `heads` coincidieron en
`0013_incidencias`. La comprobación `app.db.check` aprobó PostgreSQL/PostGIS.

Los JSON E2E registran para cada ronda la operación, ID de incidencia, respuestas,
replay y número de coincidencias en `GET /incidencias` como Operador. El contrato
no expone `operation_id` en el listado: se correlaciona mediante el marcador único
de observación y el ID del acuse. La consulta SQL adicional valida directamente
la unicidad por operación y sus auditorías, sin cambiar el contrato del API.

## Capturas reales

Viewport 360 × 800. Son del entorno demo real, con datos sintéticos:

- Chrome: [offline tras recarga](../run-2026-10-27T21-30-35-858Z/chrome-offline.png) y [confirmado al reconectar](../run-2026-10-27T21-30-35-858Z/chrome-reconnected.png).
- Firefox: [offline tras recarga](../run-2026-10-27T21-30-35-858Z/firefox-offline.png) y [confirmado al reconectar](../run-2026-10-27T21-30-35-858Z/firefox-reconnected.png).

## Incidentes de preparación y trazabilidad

Se conservan las evidencias iniciales sin modificarlas. Docker se instaló después
de la ejecución inicialmente bloqueada documentada en el
[registro histórico](../README.md). Docker Desktop estaba instalado pero detenido;
se inició y se creó una configuración privada `.env`, ignorada por Git, con
credenciales aleatorias para cuentas y base demo.

- El primer contenedor QA intentó escribir la caché de Ruff en el montaje de
  código de solo lectura. Se movió esa caché a `/tmp` y la campaña completa pasó.
- Los intentos E2E de [21:29:33 UTC](../run-2026-10-27T21-29-33-710Z/results.json)
  y [21:30:02 UTC](../run-2026-10-27T21-30-02-474Z/results.json) fallaron en el
  script al leer el acuse antes de su persistencia. El primero usó el script
  original; el segundo una copia de diagnóstico en la carpeta temporal ignorada.
  Se corrigió mediante sondeo explícito de IndexedDB, sin cambiar código de la
  aplicación. La campaña completa de 21:30:35 UTC pasó en ambos navegadores.

No se encontraron nuevos fallos del producto ni se abrió un bug adicional.
I03 conserva la limitación de jornada ya registrada en **ECL-82**; el resultado
aprobado de su prueba existente acredita propiedad de parada y ausencia de
modificación de su estado, no implementación del futuro modelo de jornada/ruta.
Pytest emitió dos deprecaciones de TestClient/Starlette; Vitest emitió avisos
React `act(...)`. Los informes conservan los resultados y la consola registra
esos avisos. CI remoto, alertas CodeQL y aprobaciones siguen siendo pasos del PR.

## Comandos y reproducción

El arranque, migraciones, seed privado y build/preview se describen en la
[matriz US-012](../../../VALIDACION_US012.md). Se montó también
`backend/scripts:/app/scripts:ro` para el seed: la imagen API no contiene scripts.
El frontend se sirvió en `127.0.0.1:5173` con build/preview y service worker;
Vite dev no permite acreditar recarga offline. El API se expuso solo en
`127.0.0.1:8000`. La campaña se ejecutó con:

```powershell
node frontend/scripts/verify-incidents-offline.mjs
```

Salida real, código 0:

```text
ECL-76: Chrome y Firefox, 10/10 rondas por navegador; API real, replay y unicidad verificados.
```

Los auxiliares usados quedan como evidencia reproducible: [Dockerfile QA](Dockerfile.qa),
[runner backend](run-backend.py), [runner frontend](run-frontend.sh) y
[copia exacta del script E2E](verify-incidents-offline.mjs). Se ejecutaron las
suites completas con dependencias lock y Python 3.12.10 en el contenedor QA;
los comandos pytest/Ruff aparecen al inicio de `backend-console.txt`.

Con el entorno de esta campaña activo, desde la raíz del repositorio:

```powershell
$qa = (Resolve-Path 'docs/03 Implementación/Sprint 03/validaciones/evidencias/ECL-76/cierre-20261027').Path
$qaRun = Join-Path $PWD ('.tmp-ecl76/retest-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $qaRun | Out-Null
docker build --file "$qa/Dockerfile.qa" --tag ecologistica-ecl76-qa backend
docker run --rm --network ecologistica-lima-ecl29_default --env-file .env --volume "${PWD}/backend:/app:ro" --volume "${qa}:/validation:ro" --volume "${qaRun}:/evidence" ecologistica-ecl76-qa python /validation/run-backend.py
docker compose --env-file .env run --rm --no-deps --volume "${qa}:/validation:ro" --volume "${qaRun}:/evidence" --entrypoint sh frontend /validation/run-frontend.sh
docker run --rm --network ecologistica-lima-ecl29_default --env-file .env --volume "${qa}:/validation:ro" --volume "${qaRun}:/evidence" ecologistica-ecl76-qa python /validation/check-persistence.py
```

El runner backend exige los nombres demo/test usados en esta campaña. En una
instalación nueva, crear **una sola vez** la base vacía de integración antes de
ejecutarlo, con el servicio `db` de este proyecto activo:

```powershell
docker compose --env-file .env exec -T db sh -c 'createdb --username="$POSTGRES_USER" --owner="$POSTGRES_USER" --template=template_postgis ecologistica_ecl76_test'
```

No ejecutar ese alta sobre una base existente ni eliminar datos para repetirla.
El fixture de integración exige un esquema vacío y protege la demo. Cada
repetición genera evidencia en la carpeta temporal nueva. La comprobación de
persistencia usa las operaciones de `browser-results.json`; para una campaña
E2E nueva, copiar su JSON nuevo a una carpeta de validación nueva en vez de
editar estos artefactos históricos. Los logs publicados eliminan valores
privados, nombre del equipo, rutas de usuario y secuencias ANSI; conservan
resultados y marcas temporales. Los scripts auxiliares no contienen credenciales.

[↑ Matriz US-012](../../../VALIDACION_US012.md)

[↑ Índice del Sprint 3](../../../../README.md)

[← Volver al README principal](../../../../../../../README.md)
