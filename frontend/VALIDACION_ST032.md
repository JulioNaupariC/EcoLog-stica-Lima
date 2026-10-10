# Validación ST-032 / ECL-58 — revisión final

Esta revisión sustituye los resultados parciales conservados al final del archivo.
Se ejecutó recarga offline y sincronización automática contra FastAPI y
PostgreSQL/PostGIS reales, usando exclusivamente datos sintéticos.

## Resultados actuales

Ejecución E2E final: **2026-10-10 04:53 UTC**, noche del 9 de octubre en Lima.
Chrome 155.0.8059.40 y Firefox 157.0, 360 px, diez ciclos por navegador.
Python 3.12.6, PostgreSQL 16.15 y PostGIS 3.6.2; único head Alembic
`0009_driver_stop_order`, con upgrade/downgrade comprobado.

| Criterio o comprobación | Resultado |
|---|---|
| Último itinerario offline | IndexedDB por propietario con dirección, referencia y ventana; shell público versionado. Recarga sin red aprobada en 20 ciclos. |
| Reportes pendientes offline | Mismo UUID conservado hasta ACK; pendiente visible incluso tras recargar. |
| Sincronización automática sin duplicados | Reconexión, comprobación de sesión, reintentos de 2 a 60 s, Web Locks cuando está disponible e idempotencia backend: 20 operaciones = 20 filas SQL. |
| Estado visual | Pendiente, reconexión, reintento y confirmado; actualización del estado y snapshot después del ACK. |
| TypeScript / ESLint / build de producción | Aprobados |
| Vitest | 471 pruebas; líneas 97.23%, sentencias 95.16%, ramas 93.20% |
| Pytest unitario backend | 560 pruebas; cobertura 93.17% |
| Ruff check / format | Aprobados |
| Integración PostgreSQL/PostGIS aislada | 2 pruebas aprobadas; restricciones, aislamiento, migraciones y reportes |
| Permisos HTTP reales | Otro conductor: 404; operador: 403 |

El primer ciclo pierde el ACK después de persistir y reintenta el mismo UUID.
El segundo simula API inaccesible y recupera por temporizador. Además se repite
cada operación después del ACK. La consulta SQL final contiene exactamente los
20 UUID del navegador. Se comprueba logout y acceso con cuenta diferente.
Resultados, registros y ocho capturas: [evidencias/ECL-58](evidencias/ECL-58/README.md).

Persisten avisos `act(...)` de algunos tests React y dos avisos Starlette/AnyIO;
no fallaron las suites. GitHub Actions y revisión humana del nuevo PR quedan
pendientes del push; no se presentan como ejecutados.

## Reproducir la revisión final

Desde la raíz con dependencias backend instaladas en `.venv`:

```powershell
cd frontend
npm.cmd ci
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run test:coverage
cd ../backend
../.venv/Scripts/python.exe -m pytest tests/unit --cov=app --cov-fail-under=80
../.venv/Scripts/python.exe -m ruff check .
../.venv/Scripts/python.exe -m ruff format --check .
```

E2E requiere PostgreSQL 16 con PostGIS, Chrome instalado y Playwright/Firefox.
Instalar el arnés en un directorio auxiliar ignorado y ejecutar:

```powershell
cd ../frontend
npm.cmd install --prefix node_modules/.st032-browser-check --no-save --package-lock=false playwright@1.64.0
node node_modules/.st032-browser-check/node_modules/playwright/cli.js install firefox
cd ../backend
../.venv/Scripts/python.exe -m scripts.verify_driver_offline --pg-bin 'C:/Program Files/PostgreSQL/16/bin' --playwright-module '../frontend/node_modules/.st032-browser-check/node_modules/playwright/index.mjs'
../.venv/Scripts/python.exe -m scripts.verify_driver_offline --pg-bin 'C:/Program Files/PostgreSQL/16/bin' --integration-only
```

El orquestador exige puertos libres 55456, 8056 y 5179, crea una base nueva en
`.tmp-st032-pg/`, aplica migraciones, prepara pedidos/asignaciones, compila y
levanta sus procesos. Los detiene al finalizar. No usa la base de desarrollo.
Las credenciales aleatorias no se exportan. Ambas ejecuciones regeneran evidencia.

## Preparación y límites operativos

- Iniciar sesión y consultar la ruta con red una vez en un build de producción
  servido sobre HTTPS o localhost. `npm run dev` no instala el Service Worker.
- La recarga recupera una pista de identidad en **la misma pestaña**, limitada
  al vencimiento comunicado por el servidor. No inicia sesiones nuevas offline.
  La API valida siempre su cookie y 401/403 retira el acceso.
- IndexedDB no cifra los datos. Se guardan dirección, referencia y ventana
  necesarias para consultar la ruta, reemplazando el cache anterior de solo
  UUID/estados. No se copian campos de cliente, DNI, teléfono ni credenciales.
  Una referencia libre puede contener datos sensibles: usar dispositivos
  autorizados y evitar datos personales innecesarios.
- Snapshot con TTL 24 h, borrado tras logout correcto. La cola pendiente se
  conserva con advertencia y solo se envía bajo la cuenta propietaria autenticada.
  Una revocación no puede detectarse sin red antes del vencimiento local.
- `DriverReportService.provision_assignment(..., pedido_id=...)` vincula cada
  parada con su pedido auténtico. Las asignaciones históricas sin vínculo muestran
  una advertencia; no se inventan direcciones. El productor del optimizador
  completo está fuera de ST-032.
- El nuevo shell se activa al cerrar las pestañas de la versión anterior;
  su cache solo contiene recursos públicos, nunca respuestas API.
- Esta validación local no certifica dispositivos físicos ni acredita un SLA.

---

# Historial: validación parcial anterior (resultados sustituidos)

## Incremento

- El itinerario del conductor carga las asignaciones del API autenticado y usa
  una instantánea IndexedDB por UUID de usuario como fallback ante fallos
  recuperables.
- La outbox mantiene los reportes offline hasta recibir un ACK con el mismo
  `operation_id`; el transporte no envía identidad propietaria ni credenciales
  explícitas y utiliza la cookie de sesión.
- El backend autoriza consultas/reportes sólo al conductor autenticado, valida
  pertenencia de la parada y persiste el reporte idempotente con la transición
  final en una transacción.
- Cerrar sesión advierte si hay reportes pendientes. Estos permanecen en el
  dispositivo y el usuario puede cancelar el cierre o sincronizarlos al volver
  a ingresar con la misma cuenta. Tras invalidar la sesión, se borra el snapshot
  del itinerario de ese usuario; un fallo de limpieza se informa.
- La pantalla de ejemplo previa permanece explícitamente rotulada como ficticia;
  los UUID reales proceden del endpoint de asignación.
- La outbox y el snapshot comparten IndexedDB versión 2 y conservan los datos
  previos durante la actualización del esquema. Se validan UUID, estados,
  vencimiento, posiciones únicas y aislamiento por usuario.

## Límite de integración

La API autenticada e idempotente está implementada. La revisión
`0008_driver_reports` depende de `0007_create_conductor` para
evitar la colisión de revisiones Alembic. El backend ofrece
`DriverReportService.provision_assignment(...)` como integración interna no HTTP.
Hasta conectar el planificador confiable a esa operación,
`GET /conductor/itinerario` devolverá una lista vacía. No se consideran
terminadas la integración con el optimizador ni pruebas end-to-end contra rutas
reales.

La migración y las pruebas de integración requieren PostgreSQL/PostGIS aislado,
`TEST_DATABASE_URL` terminado en `_test` y esquema público vacío. No apuntarlas a
la base de desarrollo. La validación local de interfaz y servicios tampoco
sustituye pruebas con lector de pantalla, usuarios o dispositivos móviles.

## Comprobaciones locales

| Comando | Resultado |
|---|---|
| `npm ci` | Correcto; npm reportó 1 vulnerabilidad alta en el árbol de dependencias |
| `npm run typecheck` | Aprobado |
| `npm run lint` | Aprobado |
| `npm test` | 294 pruebas aprobadas en 17 archivos |
| `npm run build` | Aprobado |
| `c:/python314/python.exe -m pytest --basetemp .pytest-tmp-st032 tests/unit --cov=app --cov-report=term --cov-fail-under=80` (desde `backend/`) | 322 pruebas aprobadas; cobertura total 90.42% |
| `C:\python314\python.exe -m ruff check .` | Aprobado |
| `python -m ruff format --check .` | 107 archivos ya formateados |
| `python -m alembic heads` | Un único head: `0008_driver_reports` |
| Navegador integrado: viewport 360 px; home/login | Sin scroll horizontal; campos y enlace de navegación de 44 px |
| Navegador integrado: IndexedDB real con transporte simulado | Snapshot guardado/leído/borrado; reporte pendiente tras error y retirado de la cola tras ACK coincidente |
| `$env:DATABASE_URL='postgresql+psycopg://offline:offline@localhost/offline'; C:\python314\python.exe -m alembic upgrade head --sql` | SQL PostgreSQL generado sin conectarse a una base |
| Pruebas de integración Alembic/PostgreSQL | No ejecutadas: no hay `TEST_DATABASE_URL` configurada |

Los tests enfocados de API y servicio pasan; el conjunto unitario backend cumple
el umbral de cobertura del 80%. La ejecución Python se hizo con 3.14.4 en este
entorno; no certifica por sí sola los demás intérpretes declarados. La simulación
de transporte y las pruebas de unidad no sustituyen el end-to-end contra una API
y una base PostgreSQL/PostGIS desplegadas.
