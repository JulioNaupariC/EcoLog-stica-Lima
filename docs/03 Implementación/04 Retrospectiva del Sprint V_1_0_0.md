# Retrospectiva del Sprint — Sprint 2

**Nombre del Proyecto:** EcoLogística Lima — optimizador de rutas sostenibles para DistriRápido S.A.C.

**Líder del Proyecto:** Julio Armando Naupari Camarena.

**Asignatura:** Taller de Proyectos 2 — Ingeniería de Sistemas e Informática.

**Sprint:** Sprint 2 — Gestión operativa y experiencia del conductor.

**Periodo planificado:** 08/10/2026–23/10/2026, según el tablero compartido.

**Fecha de corte:** 25/10/2026, America/Lima (cierre del Sprint 2).

**Versión del contenido:** 1.3.0.

**Fuente del corte técnico:** `main` con los PR #47–#57 integrados y el PR de cierre del Sprint 2.

**Base del análisis:** datos de Jira (estados y Time in Status), historial de Git y
PR de GitHub, el feedback de la Review del 09/10/2026 y la reunión de retrospectiva
del equipo en clase el 23/10/2026. El análisis es sin culpables:
describe hechos del proceso y sus causas, no desempeños individuales.

## Hallazgos del Sprint 2

| # | Hallazgo | Dato verificable |
|---|---|---|
| H1 | Las subtareas pasaron por «En curso» sin trabajo registrado en ese estado | Casi todas las subtareas ECL-46 a ECL-64 estuvieron entre 0,5 y 3 segundos en «En curso» (Time in Status de Jira) |
| H2 | El cierre se concentró al final y no reflejó el avance real | 19 subtareas pasaron a Finalizada en unas 36 horas de un sprint de 15 días |
| H3 | La regla de aprobación independiente se cumplió, pero el tiempo de revisión fue muy corto | PR #22–#46: los 23 integrados tienen la aprobación de una persona distinta del autor antes del merge (0 sin aprobación independiente); 10 se integraron a 6 minutos o menos de abrirse; mediana 13,8 minutos |
| H4 | La autoría en Git no coincide con el responsable en Jira | ECL-9 y ECL-11 (responsable Frank): código de Antony y Giancarlo. `metrics.py` de ECL-23 (responsable Julio): Giancarlo. `compare_client_lookup.py` de ECL-25 (responsable Antony): Giancarlo |
| H5 | Se implementó contra criterios no ratificados | Las BDD de ECL-47 y ECL-51 siguen en estado BORRADOR |
| H6 | No se demostró el producto en la Review | Acta del 09/10/2026: demostración no realizada; criterio 3 de la rúbrica con 2/4 |
| H7 | «Finalizada» en Jira no equivale a criterios acreditados | 27/27 SP cerrados frente a 3/27 SP con todos sus criterios acreditados ([informe de estado](<01 Informe de estado del proyecto V_1_0_0.md>)) |

## Análisis por eje

### Personas

- **Qué pasó:** el trabajo se concentró en pocas personas (H4) y la exposición
  no incluyó la demostración (H6).
- **Causa raíz:** no se repartió explícitamente quién demuestra cada historia ni
  se ensayó; quien conocía el flujo técnico no era siempre el responsable en Jira.
- **Qué mantener:** la colaboración entre líneas resolvió bloqueos, como la
  colisión de migraciones del 09/10, corregida el mismo día.

### Relaciones

- **Qué pasó:** todos los PR tuvieron la aprobación de otra persona, exigida por la
  protección de `main` (impedimento I-05, resuelto), pero 10 de 23 se aprobaron e
  integraron a 6 minutos o menos de abrirse (H3), con poco margen para que el
  revisor reprodujera el cambio.
- **Causa raíz:** las integraciones se concentraron en pocas horas al final
  (H2), y la revisión se hizo con prisa para cerrar el tablero.
- **Qué pasó también:** los criterios de conductores y preferencias no se
  ratificaron entre negocio, UX y backend antes de implementar (H5); el defecto
  D-01 (preferencias no propuestas en el pedido) nació de esa ambigüedad.

### Procesos

- **Qué pasó:** el tablero se actualizó en bloque al final (H1, H2) y cerró
  historias cuyos criterios no estaban acreditados (H7).
- **Causa raíz:** el Definition of Done no se comprueba antes de mover a
  Finalizada; el estado de Jira se usó como registro de entrega, no como
  seguimiento diario. Tampoco hay Story Points en las subtareas, por lo que el
  avance no se puede medir durante el sprint.
- **Qué mantener:** cada subtarea dejó un informe de validación con escenarios,
  evidencia y límites, y los informes declararon con honestidad lo no acreditado
  (concurrencia sostenida, SLA mensual, payload del dashboard).

### Herramientas

- **Qué pasó:** las evidencias quedaron dispersas fuera de `docs/03 Implementación`
  y sin navegación desde el README; no había datos para demostrar el producto.
- **Causa raíz:** ninguna herramienta comprobaba la ubicación ni los enlaces de la
  documentación, y no existía un script de datos de demostración.
- **Corrección aplicada:** verificador `scripts/check_docs.py` en CI
  ([PR #47](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/47)) y
  `seed_demo.py` ([PR #52](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/52)).

## Reunión de retrospectiva — 23/10/2026

| Campo | Registro |
|---|---|
| Fecha y lugar | Viernes 23/10/2026, en clase (fecha de fin planificada del Sprint 2) |
| Asistentes | Julio Armando Naupari Camarena (líder), Frank Roy Yupanqui Acevedo (analista de requisitos), Giancarlo Marcio Soto Escobar (UX/UI), Antony Munive Ríos (backend y optimización), José Samuel Delgadillo Pantoja (frontend y QA) |
| Insumos | Hallazgos H1–H7 y plan de acción A1–A6 de esta retrospectiva |

### Acuerdos

| # | Acuerdo | Cómo se aplica |
|---|---|---|
| R1 | Las acciones A1–A6 se mantienen y cada una corresponde al rol documentado de su responsable ([Equipo](<../../README.md#equipo>)) | Seguimiento en la retrospectiva del Sprint 3 |
| R2 | Como no todos tienen la misma disponibilidad, los PR se atienden como una cola: cada PR lo aprueba el integrante del rol correspondiente tras revisar los cambios | Revisores por rol en [`.github/CODEOWNERS`](<../../.github/CODEOWNERS>) y sección 3.4 de la [política de PR](<../04 Contribución/01. Politica de pull requests V_1_0_0.md>) (acción A7) |
| R3 | El Sprint 2 no se cierra en Jira hasta confirmar que el diseño de Giancarlo (ECL-55 / ST-029) está alineado con lo implementado | La guía se integra en el PR de cierre con la confirmación de Giancarlo; después se cierra el sprint en Jira |
| R4 | Cada sprint conserva una rama final con su código y documentación como evidencia; las ramas de trabajo se eliminan al cerrar el sprint, y las del Sprint 3 se conservan hasta su evaluación del 30/10/2026 | Ramas `sprint-1` y `sprint-2` (acción A8) |

## Seguimiento de las acciones del Sprint 1

| Acción del Sprint 1 | Responsable | Fecha comprometida | Resultado | Evidencia |
|---|---|---|---|---|
| Validación cruzada del README (ECL-29) | José Samuel Delgadillo Pantoja | 02/10/2026 | Cumplida por otra persona: la revisó Giancarlo | Revisión del PR #20 ([adenda V_1_0_1](<../02 Planificación/02 Artefactos Jira V_1_0_1.md>)) |
| Preparar cuentas y datos de demostración | Giancarlo Marcio Soto Escobar | 02/10/2026 | No cumplida en plazo; causó la Review sin demostración. Resuelta el 13/10 con `seed_demo.py` | [PR #52](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/52) |
| Conciliar el estado de Jira | Julio Armando Naupari Camarena | 02/10/2026 | Cumplida | [Adenda V_1_0_1](<../02 Planificación/02 Artefactos Jira V_1_0_1.md>) |
| Revisión humana del PR #20 y de Docker Compose | Antony Munive Ríos con un revisor | 03/10/2026 | Cumplida: PR #20 aprobado por Giancarlo e integrado; Compose validado sin login ni persistencia de datos de negocio | Adenda V_1_0_1 |
| Registrar el feedback del stakeholder | Frank Roy Yupanqui Acevedo | 02/10/2026 | No cumplida: no hay acta del Sprint 1 | — |

Resultado: 3 de 5 acciones cumplidas, una con otra persona responsable. Las dos
incumplidas reaparecieron en el Sprint 2 como la falta de demostración y de acta;
por eso el plan siguiente fija una métrica y una forma de comprobación por acción.

## Plan de acción

Las acciones son compromisos del equipo. A1–A6 fueron confirmadas en la reunión
del 23/10/2026 (acuerdo R1) y A7–A8 surgieron de ella. Se revisarán en la
retrospectiva del Sprint 3 con la misma tabla de seguimiento.

Estado de A4 al 25/10/2026: las BDD ECL-47 y ECL-51 siguen en BORRADOR en el
repositorio, por lo que la acción está vencida y continúa como prioridad al
inicio del Sprint 3.

| # | Acción | Responsable | Fecha límite | Métrica verificable | Cómo se comprobará |
|---|---|---|---|---|---|
| A1 | Comprobar el Definition of Done (criterios con evidencia enlazada, pruebas en verde, revisión) antes de mover una tarea a Finalizada | Julio Armando Naupari Camarena | 23/10/2026 | 100 % de las tareas finalizadas del Sprint 3 con enlace a evidencia; ninguna con menos de 1 hora en «En curso» | Time in Status de Jira y revisión de enlaces en la planificación del Sprint 3 |
| A2 | Mantener la regla de protección de `main` que exige la aprobación de una persona distinta del autor | Julio Armando Naupari Camarena | 23/10/2026 | 0 PR integrados sin aprobación de otra persona; mantener la regla de protección | Consulta de autor, aprobaciones y merge de los PR del Sprint 3 en GitHub |
| A3 | Alinear la autoría con Jira: quien hace el trabajo figura como responsable o como `Co-authored-by` en el commit | Antony Munive Ríos | 23/10/2026 | 100 % de los commits del Sprint 3 con autor o coautor igual al responsable Jira de su clave ECL | Script que cruza `git log` con las claves ECL y la exportación de Jira |
| A4 | Ratificar las BDD antes de implementar | Frank Roy Yupanqui Acevedo | 20/10/2026 | ECL-47 y ECL-51 en estado APROBADO; 0 historias del Sprint 3 iniciadas con BDD en BORRADOR | Cabecera de estado de las BDD y fecha del commit de aprobación anterior a la primera rama de la historia |
| A5 | Registrar Story Points en Jira para historias y subtareas | Frank Roy Yupanqui Acevedo | 23/10/2026 | 100 % de los elementos del Sprint 3 con Story Points antes de iniciar el sprint | Exportación del sprint en Jira |
| A6 | Ensayar la demostración antes de la Review con `seed_demo.py` y el guion con tiempos | Giancarlo Marcio Soto Escobar | Un día hábil antes de la Review del Sprint 3 | 1 ensayo completo cronometrado ≤15 minutos con todas las historias demostradas | Grabación o capturas del ensayo enlazadas en la Revisión del Sprint 3 |
| A7 | Activar **Require review from Code Owners** en la protección de `main` y atender los PR por rol según CODEOWNERS | Julio Armando Naupari Camarena | Antes del primer PR del Sprint 3 | 100 % de los PR del Sprint 3 aprobados por un dueño del área que modifican, distinto del autor | Revisores y aprobaciones de cada PR del Sprint 3 en GitHub |
| A8 | Conservar una rama `sprint-N` por sprint cerrado, protegida, y eliminar las ramas de trabajo integradas | Julio Armando Naupari Camarena | Al cierre de cada sprint | 1 rama `sprint-N` por sprint cerrado; 0 ramas de trabajo integradas tras el cierre (salvo las del sprint en evaluación) | Listado de ramas del repositorio en GitHub |

## Fuentes

- [Informe de estado](<01 Informe de estado del proyecto V_1_0_0.md>), [registro de impedimentos](<02 Registro de Impedimentos V_1_0_0.md>) y [revisión del Sprint](<03 Revisión del Sprint V_1_0_0.md>).
- Jira: Time in Status y fechas de transición comunicadas al 12/10/2026.
- GitHub: autoría, aprobaciones y tiempos de merge de los PR #22–#54, consultados el 13/10/2026.
- Git: autoría de commits por archivo (`git log`) al 13/10/2026.

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 01/10/2026 | Entregable del Sprint 1; contenido anterior conservado en el historial Git. |
| 1.1.0 | 09/10/2026 | Sustitución del contenido por el entregable del Sprint 2, con evidencias y pendientes al corte. |
| 1.2.0 | 13/10/2026 | Hallazgos verificables, causas raíz por eje, seguimiento de las acciones del Sprint 1 y plan SMART. |
| 1.3.0 | 25/10/2026 | Reunión de retrospectiva del 23/10/2026 con asistentes y acuerdos R1–R4, estado de A4 y acciones A7–A8 (revisores por rol y ramas de cierre). |

El nombre V_1_0_0 del archivo se conserva por exigencia de la consigna.

[← Volver al README principal](../../README.md)
