## Ticket Jira

[ECL-76 / ST-043 — Pruebas de incidencias por tipo de ruta](https://continental-team-il84x39k.atlassian.net/browse/ECL-76)

## Objetivo

Trazar US-012 contra los 16 escenarios de la BDD aprobada de ECL-72 y cubrir las
variantes de interfaz pendientes. Preparar la campaña offline real en Chrome y
Firefox y registrar los resultados disponibles sin dar por ejecutada la integración.

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

## Validaciones y evidencia

Ejecución local del 27/10/2026; Python 3.14.4 y Node 22.18.0.
La matriz detalla la diferencia respecto al entorno Python 3.12.10 de CI.

| Validación | Resultado | Evidencia |
|---|---|---|
| Tests unitarios | [x] Pasan: backend 868, cobertura 92,27 %; frontend 732, líneas 97,62 %, ramas 92,87 % | Matriz y evidencias enlazadas abajo |
| Tests de integración | Pendientes: Docker/PostGIS no disponibles en este equipo | Registro de entorno |
| Lint y formateo | [x] En verde: Ruff lint/formato, ESLint, sintaxis Node | Registro de comandos |
| Type-check | [x] En verde; build frontend también aprobado | Registro de comandos |
| CodeQL | Pendiente ejecución remota y revisión de alertas | No se afirma CI ni Security en verde |

- [Matriz de validación US-012](https://github.com/JulioNaupariC/EcoLog-stica-Lima/blob/test/ECL-76-pruebas-incidencias/docs/03%20Implementaci%C3%B3n/Sprint%2003/validaciones/VALIDACION_US012.md).
- [Evidencias](https://github.com/JulioNaupariC/EcoLog-stica-Lima/tree/test/ECL-76-pruebas-incidencias/docs/03%20Implementaci%C3%B3n/Sprint%2003/validaciones/evidencias/ECL-76).

## Riesgos

- La campaña E2E no llegó a iniciar navegadores: faltan Docker, servicios y
  configuración demo privada. No hay capturas ni 10/10 reales. El script debe
  validarse contra el entorno real antes de cerrar el ticket.
- I03 permanece parcial por la validación de jornada registrada en ECL-82.
  El script deja las incidencias sintéticas de prueba en la base local.
- Vitest emite avisos React `act(...)`; pytest emite dos deprecaciones.
  No hubo fallos en las suites ejecutadas.

## Checklist de seguridad y revisión

- [x] No se añaden secretos ni credenciales.
- [x] No se introducen dependencias nuevas en la aplicación.
- [x] Se actualizó documentación y navegación.
- [x] OpenAPI no cambia: se conserva el contrato de los endpoints.
- [x] Pruebas doradas, felices, infelices y de borde identificadas en la matriz.
- [x] Matriz con resultados reales y evidencia registrada.
- [ ] E2E real Chrome y Firefox: diez ciclos por navegador sin duplicados.
- [ ] Criterios de aceptación completos del ticket satisfechos.
- [ ] Integración PostGIS y checks remotos en verde.
- [ ] Se revisaron las alertas de CodeQL.
- [ ] Auditoría técnica independiente y aprobación humana.

Revisores: **@GiancarloSE** (`frontend/`) y **@FrankRoyYA** (`docs/`).
No se modifica `backend/tests/`; no se requiere el tercer revisor por ese motivo.
Mantener este PR en **Draft** hasta completar las validaciones pendientes.

[↑ Índice del Sprint 3](<../README.md>)

[← Volver al README principal](../../../../README.md)
