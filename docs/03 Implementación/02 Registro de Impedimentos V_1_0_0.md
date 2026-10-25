# Registro de impedimentos — Sprint 2

**Nombre del Proyecto:** EcoLogística Lima — optimizador de rutas sostenibles para DistriRápido S.A.C.

**Líder del Proyecto:** Julio Armando Naupari Camarena.

**Asignatura:** Taller de Proyectos 2 — Ingeniería de Sistemas e Informática.

**Sprint:** Sprint 2 — Gestión operativa y experiencia del conductor.

**Periodo planificado:** 08/10/2026–23/10/2026, según el tablero compartido.

**Fecha de corte:** 25/10/2026, America/Lima (cierre del Sprint 2).

**Versión del contenido:** 1.3.1.

**Fuente del corte técnico:** `main` con los PR #47–#57 integrados y el PR de cierre del Sprint 2.

**Estado Jira:** cinco padres y 19 subtareas en Finalizada (27/27 SP de padres); el sprint se cierra en Jira tras integrar el PR de cierre (acuerdo R3 de la retrospectiva del 23/10/2026).

## Criterio del registro

Un **impedimento** es lo que bloquea o frena al equipo: una dependencia, un
problema de entorno o un acuerdo pendiente. Los **defectos y brechas de producto**
no son impedimentos: se gestionan como trabajo del backlog con su clave de Jira,
como sugirió el docente en la Review del 09/10. La prioridad se fija por el
impacto: **Alta** si bloquea criterios de aceptación o la demostración, **Media**
si retrasa la verificación sin bloquearla y **Baja** si solo afecta a la
comparabilidad de resultados. Fechas en hora de Lima.

## Impedimentos

| # | Fecha de registro | Descripción | Impacto | Prioridad | Reportado por | Responsable | Fecha tope | Estado | Fecha de resolución | Resolución / comentarios |
|---|---|---|---|---|---|---|---|---|---|---|
| I-01 | 09/10/2026 | No había datos ni entorno preparados para demostrar el producto | La demostración no se realizó en la Review: criterio 3 de la rúbrica con 2/4 y sin evidencia ante el stakeholder de las 5 HU/enablers (27 SP) | Alta | Daniel Gamarra Moreno (docente, en la Review) | Antony Munive Ríos | 16/10/2026 | Resuelto | 13/10/2026 | `seed_demo.py` crea datos ficticios por rol, con conductores de borde y paradas reales ([PR #52](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/52), commit `aea1897`). Demostración complementaria ejecutada y grabada el 13/10/2026 con esos datos ([video](https://drive.google.com/file/d/1YC6s3QDTsN35XVCBZmUVEwc64c_F2rWO/view?usp=sharing)) |
| I-02 | 09/10/2026 | Colisión de identificadores de revisión Alembic entre conductores y reportes del conductor | Bloqueaba la integración de ECL-58 (ST-032) con ECL-48: dos ramas de migración incompatibles | Alta | Giancarlo Marcio Soto Escobar | José Samuel Delgadillo Pantoja | 09/10/2026 | Resuelto | 09/10/2026 | Identificador de revisión acortado y cadena 0007 → 0008 restaurada (commit `b6a3e26`) |
| I-03 | 09/10/2026 | Las BDD de conductores (ECL-47) y preferencias (ECL-51) siguen en estado BORRADOR, sin ratificar por el equipo | Impide la aceptación formal de US-003 y US-005 (8 SP): los criterios se verifican contra una fuente no aprobada | Media | Giancarlo Marcio Soto Escobar (DOC-01 de ST-028) | Frank Roy Yupanqui Acevedo | 20/10/2026 | Abierto | — | Pendiente de sesión de ratificación con Julio Armando Naupari Camarena; ver acción A4 de la retrospectiva |
| I-04 | 13/10/2026 | La prueba E2E offline (ST-032) usaba un puerto de PostgreSQL que Windows reserva en el equipo de pruebas (rango 55401–55500) | Impedía reacreditar el escenario «pérdida y recuperación de red» de EN-004 tras el rediseño | Media | Antony Munive Ríos | Antony Munive Ríos | 16/10/2026 | Resuelto | 13/10/2026 | Opción `--pg-port` en `verify_driver_offline.py`; ejecución con el puerto 15432 aprobada en Chrome y Firefox (PR #54, commit `201db9b`) |
| I-05 | 13/10/2026 | No se pudo consultar la configuración de protección de `main`: la API de GitHub la reserva a administradores del repositorio | Sin confirmarla no se podía acreditar que la [política de PR](<../04 Contribución/01. Politica de pull requests V_1_0_0.md>) (aprobación de una persona distinta del autor) se aplica de forma obligatoria | Media | Antony Munive Ríos | Antony Munive Ríos | 16/10/2026 | Resuelto | 13/10/2026 | La protección está activa: en el [PR #48](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/48) GitHub mostró «Review required — At least 1 approving review is required by reviewers with write access» y «Merging is blocked» hasta la aprobación de José Samuel Delgadillo Pantoja (21:10:22 UTC; merge 21:10:52 UTC). Mantener la regla: acción A2 |
| I-06 | 13/10/2026 | El enlace de evidencia de ECL-59 en Jira apunta a la ruta anterior del plan de capacidad, reubicado en la Fase 1 | La trazabilidad Jira → GitHub de ST-033 queda rota hasta corregirla | Baja | Antony Munive Ríos | Antony Munive Ríos | 16/10/2026 | Abierto | — | Actualizar el enlace a `docs/03 Implementación/Sprint 02/informes/plan-pruebas-capacidad.md`; el [mapa de reubicación](<Sprint 02/README.md>) cubre la consulta mientras tanto |
| I-07 | 13/10/2026 | El equipo de pruebas usaba Node 24 mientras CI fija Node 22.18.0 | Resultados locales no comparables con CI | Baja | Antony Munive Ríos | Antony Munive Ríos | 13/10/2026 | Resuelto | 13/10/2026 | Node 22.18.0 oficial con SHA-256 verificado; las fases 2 y 3 se validaron con esa versión ([PR #48](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/48)) |

### Historial de estados

| # | Abierto | En progreso | Resuelto | Evidencia |
|---|---|---|---|---|
| I-01 | 09/10/2026 — Review sin demostración | 13/10/2026 — rama `chore/sprint-2-datos-demo` | 13/10/2026 — merge del PR #52 | Commit `aea1897`; [video de la demostración complementaria](https://drive.google.com/file/d/1YC6s3QDTsN35XVCBZmUVEwc64c_F2rWO/view?usp=sharing) |
| I-02 | 09/10/2026 — integración de ST-032 | 09/10/2026 — corrección en la rama de ST-032 | 09/10/2026 | Commit `b6a3e26` |
| I-03 | 09/10/2026 — DOC-01 en ST-028 | — | — | [VALIDACION_ST028](<Sprint 02/validaciones/VALIDACION_ST028.md>) |
| I-04 | 13/10/2026 — fallo de arranque del clúster | 13/10/2026 — opción `--pg-port` | 13/10/2026 — reprueba aprobada | [Evidencia ECL-58](../../frontend/evidencias/ECL-58/retest-20261013/README.md) |
| I-05 | 13/10/2026 — consulta de la API de protección de rama (HTTP 404 sin permisos) | 13/10/2026 — comprobación en un PR real | 13/10/2026 — merge bloqueado hasta la aprobación | [PR #48](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/48) |
| I-06 | 13/10/2026 — reubicación de la Fase 1 | — | — | [PR #47](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/47) |
| I-07 | 13/10/2026 — preparación del pipeline | 13/10/2026 | 13/10/2026 | Reporte de la fase 2 en el PR #48 |

## Gestionados como backlog

Defectos y brechas de producto detectados en el Sprint 2. Se gestionan con su
clave de Jira; los resueltos indican el PR que los cierra.

| Elemento | Clave Jira | Impacto | Prioridad | Estado | Destino / evidencia |
|---|---|---|---|---|---|
| D-01: el pedido no proponía las preferencias del cliente (P8, RF-005) | ECL-53 / ECL-54 | Impedía acreditar US-005 | Alta | Resuelto 13/10/2026 | [PR #49](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/49); reprueba aprobada en Chrome y Firefox |
| Pedidos y preferencias exigían escribir el UUID del cliente | ECL-53 | Uso propenso a errores | Alta | Resuelto 13/10/2026 | `GET /clientes` y buscador accesible ([PR #49](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/49)) |
| N+1 en el listado de conductores | ECL-64 | 22 consultas para 20 filas; 102 para 100 | Media | Resuelto 13/10/2026 | 2 consultas por página ([PR #48](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/48)) |
| Alta y edición de conductores sin auditoría (RN-015) | ECL-48 | Incumplía una regla de negocio | Alta | Resuelto 13/10/2026 | [PR #50](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/50), migración 0010 |
| El itinerario mostraba datos ficticios junto a los reales | ECL-56 | Información engañosa para el conductor | Alta | Resuelto 13/10/2026 | [PR #51](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/51) |
| Sincronización offline no se reactivaba en Firefox si faltaba el evento `online` | ECL-58 | Reportes retenidos en el dispositivo | Alta | Resuelto 13/10/2026 | [PR #54](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/54) (`10737e3`) |
| Payload ≤250 KB (RNF-012) no medible y el Inicio contaba habilitados sobre los primeros 100 conductores | ECL-25 | ECL-25 no cumplía | Alta | Resuelto 13/10/2026 | Indicadores agregados del Inicio: 347 bytes, regresión en CI e índice 0011 ([evidencias](../../backend/evidencias/ECL-25-inicio/README.md), [PR #57](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/57)) |
| Dashboard de sostenibilidad pendiente; debe ampliar el endpoint de indicadores | ECL-15 | Sin indicadores de CO₂ | Media | Pendiente | Product Backlog — priorizar en el Sprint Planning 3; después de la primera ruta optimizada |
| Asignación real de rutas (planificador VRPTW) | ECL-12 (EP-03) | Licencia vencida y disponibilidad no se aplican en una asignación real | Alta | Pendiente | Candidato al Sprint 3 (primeros del backlog) |
| Carga sostenida de 100 solicitudes no acreditada (19–21 % de segundos ≥100) | ECL-23 / ECL-61 | EN-005 parcial | Media | Pendiente | Product Backlog — priorizar en el Sprint Planning 3: repetir la corrida con el generador corregido |
| SLA mensual ≥99,5 % no medido | ECL-23 / ECL-62 | EN-005 parcial | Media | Pendiente | Product Backlog — priorizar en el Sprint Planning 3: requiere un mes de observación |
| Alertas operativas reales y prueba con lector de pantalla | ECL-14 / ECL-22 | EN-004 parcial | Media | Pendiente | Product Backlog — priorizar en el Sprint Planning 3 |
| Vulnerabilidad alta transitiva en `source-map-js` (ya registrada en ST-032) | Sin clave; registrar en el Product Backlog | Riesgo en la cadena de dependencias de desarrollo | Media | Pendiente | Product Backlog — priorizar en el Sprint Planning 3; `npm audit` del 13/10/2026: 1 alta, corrección disponible |
| División del bundle por rutas (+49 KB tras el rediseño) | Sin clave; registrar en el Product Backlog | Carga inicial mayor | Baja | Pendiente | Product Backlog — priorizar en el Sprint Planning 3; al incorporar el mapa (ECL-14) |
| Punto de partida como geografía PostGIS, ventanas estructuradas en preferencias y CRUD completo de clientes | Sin clave; registrar en el Product Backlog | Fuera del alcance del parche | Baja | Pendiente | Product Backlog — priorizar en el Sprint Planning 3 |

## Fuentes

- [VALIDACION_ST028](<Sprint 02/validaciones/VALIDACION_ST028.md>), [INFORME_ST036](<Sprint 02/informes/INFORME_ST036.md>), [INFORME_ST037](<Sprint 02/informes/INFORME_ST037.md>) y [VALIDACION_ST038](<Sprint 02/validaciones/VALIDACION_ST038.md>).
- GitHub: PR #22–#54 (autoría, aprobaciones y fechas de merge consultadas el 13/10/2026).
- Comentarios del docente en la Review del 09/10/2026 ([acta](<03 Revisión del Sprint V_1_0_0.md>)).

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 01/10/2026 | Entregable del Sprint 1; contenido anterior conservado en el historial Git. |
| 1.1.0 | 09/10/2026 | Sustitución del contenido por el entregable del Sprint 2, con evidencias y pendientes al corte. |
| 1.2.0 | 13/10/2026 | Separación entre impedimentos y backlog, responsables y fechas, impacto cuantificado e historial de estados. |
| 1.3.0 | 13/10/2026 | ECL-25 resuelto con los indicadores agregados del Inicio; el dashboard de sostenibilidad queda como pendiente propio. |
| 1.3.1 | 25/10/2026 | Corte de cierre: fuente con los PR #47–#57, guía ST-029 (ECL-55) integrada en `Sprint 02/diseno/` y cierre del sprint en Jira según el acuerdo del 23/10/2026. |

El nombre V_1_0_0 del archivo se conserva por exigencia de la consigna.

[← Volver al README principal](../../README.md)
