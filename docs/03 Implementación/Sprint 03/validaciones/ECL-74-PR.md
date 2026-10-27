## Ticket Jira

[ECL-74 / ST-041](https://continental-team-il84x39k.atlassian.net/browse/ECL-74)
— Formulario móvil de incidencia con borrador y cola offline.

## Objetivo

Permitir al Conductor reportar una incidencia desde su itinerario, conservar
el borrador y enviarla al recuperar conectividad sin duplicados. La interfaz
identifica los faltantes y distingue el envío pendiente del registro confirmado
pendiente de validación por Operación.

## Cambios

- Ruta protegida `/conductor/incidencias/nueva`, entrada desde itinerario,
  seis tipos, tres severidades con icono/texto, hora automática, GPS/parada y
  observación de hasta 500 puntos de código Unicode.
- Borrador por propietario y cola persistente en IndexedDB separada de los
  almacenes del Sprint 2; transacciones atómicas y UUID v4 estable.
- Sincronización por cuenta al reconectar, Web Locks, timeout, acuse validado
  y estados visibles; pausa de 401/403/409/422 y corrección de 422 con misma clave.
- Cabecera `X-Expected-Owner-ID` validada contra la cookie en el POST para
  rechazar cambios de cuenta entre pestañas sin registrar una cola ajena;
  OpenAPI y CORS actualizados. Ajuste autorizado por José.
- Soporte de recarga offline del formulario en el service worker y aviso de
  incidencias pendientes al cerrar sesión.
- Ajuste mínimo de backend autorizado por José: coordenadas opcionales del
  pedido asignado en el itinerario. No hay migraciones ni cambios de permisos.
- Pruebas, guía de validación y 16 capturas Chrome/Firefox a 360 px en ambos temas.

## Validaciones y evidencia

Resultados locales del 26/10/2026, America/Lima:

| Validación | Resultado | Evidencia |
|---|---|---|
| Tests unitarios frontend | [x] Pasan: 635 pruebas, 48 archivos; cobertura global 97,51 % líneas, 92,56 % ramas | `npm --prefix frontend run test:coverage -- --maxWorkers=2` |
| Tests del incremento | [x] Pasan: 32 pruebas específicas nuevas; cobertura focalizada inicial (31 pruebas previas al guard) 96,44 % líneas, 88,54 % ramas | Archivos `incident.test.ts`, `incidentSync.test.ts`, `IncidentCreatePage.test.tsx`, `useIncidentSynchronization.test.tsx` |
| Tests unitarios backend | [x] Pasan: 867; cobertura 92,25 % | `python -m pytest tests/unit --cov=app --cov-fail-under=80`, desde `backend/` |
| Tests de integración real | [ ] Pendiente: Docker no está disponible en el equipo de ejecución | Requiere sesión de prueba y PostgreSQL/PostGIS; no se sustituye con mocks |
| Flujo en navegador | [x] Chrome 156.0.8078.48 y Firefox 157.0; claro/oscuro, 360 px, recarga offline y reconexión, una operación/POST | [Resultados](<evidencias/ECL-74/browser-results.json>) y [16 capturas](<evidencias/ECL-74/README.md>) con API HTTP sintética local |
| Reprueba con propietario esperado | [x] Las cuatro combinaciones vuelven a pasar con la nueva cabecera; pruebas HTTP comprueban rechazo de cookie ajena y preflight | [Resultados nuevos](<evidencias/ECL-74/owner-guard/browser-results.json>) y `test_I16_*` en `test_incidencias_api.py` |
| Lint y formateo | [x] Frontend ESLint y backend Ruff en verde | `npm --prefix frontend run lint`; `python -m ruff check .`; `python -m ruff format --check .` |
| Type-check y build | [x] En verde | `npm --prefix frontend run typecheck`; `npm --prefix frontend run build` |
| Documentación | [x] Enlaces e índices verificados | `python scripts/check_docs.py` |
| CodeQL | [ ] Pendiente de ejecución en GitHub y revisión de alertas | Security > Code scanning alerts |

Una ejecución exitosa de CodeQL confirma que el análisis terminó. La ausencia
de alertas nuevas requiere revisión explícita; no se declara comprobada aquí.

### Criterios de aceptación del formulario

- [x] Registra tipo, ubicación, severidad y observación; hora automática.
- [x] Datos incompletos conservan borrador e indican campos y foco.
- [x] Sin conexión conserva el reporte; reconexión sin cambiar operación ni duplicar.
- [x] Etiquetas visibles, teclado, 360 px y modo oscuro, con evidencia local.

## Riesgos

- Las capturas usan API sintética; falta la integración real con Docker/BD.
  No acredita la campaña completa de 10/10 de ECL-76 ni la jornada de ECL-82.
- Paradas sin coordenadas no inventan ubicación: la opción indica la limitación
  y el GPS sigue disponible. Se mantiene compatibilidad con instantáneas antiguas.
- Desplegar el backend actualizado junto al frontend para permitir la nueva
  cabecera en CORS y comprobarla en servidor.
- Borrar los datos del navegador elimina borradores y pendientes locales.
  La interfaz informa si el almacenamiento falla.

## Checklist de seguridad y revisión

- [x] No se añaden secretos ni credenciales.
- [x] No se introducen dependencias de producción ni se modifica el lockfile.
- [x] Se actualiza documentación e índices del Sprint 3.
- [x] OpenAPI incluye las coordenadas opcionales mediante el esquema Pydantic.
- [ ] Aceptación integrada del ticket: pendiente de API/BD reales.
- [ ] Auditoría técnica independiente sobre el head definitivo.
- [ ] CI y CodeQL del head definitivo en verde; alertas revisadas.
- [ ] Aprobación humana por área antes de integrar.

Preparar como **Draft**. Solicitar revisión a **@GiancarloSE** (`frontend/`),
**@FrankRoyYA** (`docs/`) y **@ANTONY-MUNIVE** o **@JulioNaupariC** (`backend/`).
La sesión implementadora no realiza su propia auditoría independiente ni mergea.

[Validación ST-041](<VALIDACION_ST041.md>)

[↑ Índice del Sprint 3](<../README.md>)

[← Volver al README principal](<../../../../README.md>)
