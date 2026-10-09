# Validación local — ECL-58 / ST-032

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
