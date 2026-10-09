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
  a ingresar con la misma cuenta.
- La pantalla de ejemplo previa permanece explícitamente rotulada como ficticia;
  los UUID reales proceden del endpoint de asignación.

## Límite de integración

El backend aún no cuenta con modelo ni proceso productor de rutas/paradas. La
migración añade un registro de asignaciones mínimo y el backend ofrece
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
| `npm run lint` | Aprobado |
| `npm test` | 285 pruebas aprobadas en 15 archivos |
| `npm run typecheck` | Aprobado |
| `npm run build` | Aprobado |
| `C:\python314\python.exe -m pytest tests/unit --cov=app --cov-report=term --cov-fail-under=80` | 320 pruebas aprobadas; cobertura total 90.26% |
| `C:\python314\python.exe -m ruff check .` | Aprobado |
| `C:\python314\python.exe -m ruff format --check .` | Aprobado |
| `$env:DATABASE_URL='postgresql+psycopg://offline:offline@localhost/offline'; C:\python314\python.exe -m alembic upgrade head --sql` | SQL PostgreSQL generado sin conectarse a una base |
| Pruebas de integración Alembic/PostgreSQL | No ejecutadas: no hay `TEST_DATABASE_URL` configurada |

Los tests enfocados de API, servicio y repositorio reportan 100% de cobertura
por módulo. La ejecución Python se hizo con 3.14.4 en este entorno; no certifica
por sí sola los demás intérpretes declarados por el proyecto.
