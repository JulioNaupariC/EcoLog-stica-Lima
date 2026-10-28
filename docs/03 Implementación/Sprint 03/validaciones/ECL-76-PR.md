## Ticket Jira

[ECL-76 / ST-043 — Pruebas de incidencias por tipo de ruta](https://continental-team-il84x39k.atlassian.net/browse/ECL-76)

## Objetivo

Trazar US-012 contra los 16 escenarios de la BDD aprobada de ECL-72 y cubrir las
variantes de interfaz pendientes. Validar la integración real y la campaña
offline en Chrome y Firefox, con evidencia de reconexión sin duplicados.

## Cambios

- Añade 30 casos: faltantes individuales y combinados, recarga del borrador,
  hora futura, 501 caracteres Unicode, conflicto visible, 18 combinaciones de
  catálogos y límites temporales con reloj fijo.
- Añade `verify-incidents-offline.mjs`: login demo real, alta online, diez ciclos
  offline por navegador, recarga, itinerario, pérdida de acuse, replay 200 y
  unicidad comprobada en el listado de Operación mediante marcador e ID del acuse.
- Añade matriz I01–I16, JUnit, extractos, instrucciones Docker con build/preview
  y navegación desde ambos README. CI recoge las pruebas automáticamente y
  comprueba la sintaxis del E2E.
- Corrige la espera asíncrona del script para consultar IndexedDB hasta recibir
  el acuse persistido. Ejecuta 10/10 ciclos reales por navegador y verifica en
  PostGIS una incidencia y una auditoría por cada una de las 22 operaciones.

## Validaciones y evidencia

Ejecución local del 27/10/2026 en Docker, Python 3.12.10 y Node 22.18.0,
con dependencias lock. PostgreSQL 16/PostGIS 3.5 reales; demo e integración aisladas.

| Validación | Resultado | Evidencia |
|---|---|---|
| Tests unitarios | [x] Pasan: backend 868, cobertura 92,81 %; frontend 732, líneas 97,71 %, ramas 92,95 % | Matriz y evidencias enlazadas abajo |
| Tests de integración | [x] Pasan: 250 contra PostgreSQL/PostGIS, 0 omitidas | JUnit y consola del cierre |
| E2E Chrome y Firefox | [x] Pasan: 10/10 ciclos por navegador, replay 200 y unicidad comprobada | JSON y cuatro capturas reales |
| Lint y formateo | [x] En verde: Ruff lint/formato, ESLint, sintaxis Node | Registro de comandos |
| Type-check | [x] En verde; build frontend también aprobado | Registro de comandos |
| CodeQL | Pendiente ejecución remota y revisión de alertas | No se afirma CI ni Security en verde |

- [Matriz de validación US-012](https://github.com/JulioNaupariC/EcoLog-stica-Lima/blob/test/ECL-76-pruebas-incidencias/docs/03%20Implementaci%C3%B3n/Sprint%2003/validaciones/VALIDACION_US012.md).
- [Evidencias de cierre](https://github.com/JulioNaupariC/EcoLog-stica-Lima/tree/test/ECL-76-pruebas-incidencias/docs/03%20Implementaci%C3%B3n/Sprint%2003/validaciones/evidencias/ECL-76/cierre-20261027).

## Riesgos

- I03 permanece parcial por la validación de jornada registrada en ECL-82.
  El script deja las incidencias sintéticas de prueba en la base local.
- La evidencia inicial bloqueada y los dos intentos fallidos del propio script
  se conservan con su contexto. El cierre enlazado contiene la reprueba aprobada.
- Vitest emite avisos React `act(...)`; pytest emite dos deprecaciones.
  No hubo fallos en las suites ejecutadas.

## Checklist de seguridad y revisión

- [x] No se añaden secretos ni credenciales.
- [x] No se introducen dependencias nuevas en la aplicación.
- [x] Se actualizó documentación y navegación.
- [x] OpenAPI no cambia: se conserva el contrato de los endpoints.
- [x] Pruebas doradas, felices, infelices y de borde identificadas en la matriz.
- [x] Matriz con resultados reales y evidencia registrada.
- [x] E2E real Chrome y Firefox: diez ciclos por navegador sin duplicados.
- [x] Criterios de pruebas del ticket ejecutados y documentados; I03 parcial trazado a ECL-82.
- [x] Integración PostGIS local en verde.
- [ ] Checks remotos en verde tras publicar la rama.
- [ ] Se revisaron las alertas de CodeQL.
- [ ] Auditoría técnica independiente y aprobación humana.

Revisores: **@GiancarloSE** (`frontend/`) y **@FrankRoyYA** (`docs/`).
No se modifica `backend/tests/`; no se requiere el tercer revisor por ese motivo.
Trabajo local completo. Publicar como **Draft** hasta la auditoría técnica
independiente exigida por la política; después solicitar revisión humana.

[↑ Índice del Sprint 3](<../README.md>)

[← Volver al README principal](../../../../README.md)
