# Informe de estado del proyecto — Sprint 2

**Nombre del Proyecto:** EcoLogística Lima — optimizador de rutas sostenibles para DistriRápido S.A.C.

**Líder del Proyecto:** Julio Armando Naupari Camarena.

**Asignatura:** Taller de Proyectos 2 — Ingeniería de Sistemas e Informática.

**Sprint:** Sprint 2 — Gestión operativa y experiencia del conductor.

**Periodo planificado:** 08/10/2026–23/10/2026, según el tablero compartido.

**Fecha de corte:** 13/10/2026, America/Lima.

**Versión del contenido:** 1.2.0.

**Fuente del corte técnico:** `main` en `ea30983` (PR #47–#55 integrados).

**Estado Jira:** cinco padres y 19 subtareas en Finalizada (27/27 SP de padres); sprint activo.

## Resumen ejecutivo

El Sprint 2 entregó la gestión de conductores y de preferencias de entrega, la
experiencia móvil del conductor con almacenamiento offline, la instrumentación de
métricas y un análisis de rendimiento. En Jira las cinco historias y enablers
figuran **Finalizada**; contrastadas con sus criterios de aceptación, **una
cumple** (ECL-11), **tres cumplen parcialmente** (ECL-9, ECL-22, ECL-23) y **una no
cumple** (ECL-25). Esa diferencia es el dato principal de este informe.

Tras la Review del 09/10 (14/20) se aplicó un parche entre el 13/10 y hoy: se
corrigió el defecto D-01 (las preferencias del cliente ya se proponen al
registrar un pedido), se eliminó un problema N+1, se auditó la gestión de
conductores, se rediseñó la interfaz y se preparó un conjunto de datos para
demostrar el producto. Los PR #47–#54 están integrados en `main` (`10737e3`). El
13/10/2026 se grabó una [demostración complementaria](https://drive.google.com/file/d/1YC6s3QDTsN35XVCBZmUVEwc64c_F2rWO/view?usp=sharing) con datos ficticios;
es posterior a la Review y no sustituye su evaluación.

## Estado por historia y enabler

«Cerrado en Jira» indica el estado del tablero. «Criterios» indica si los
escenarios BDD de [Transformando a ágil](<../02 Planificación/01 Transformando a ágil V_1_0_0.md>)
están acreditados con evidencia reproducible.

| Elemento | SP | Responsable Jira | Cerrado en Jira | Criterios | Evidencia | Acción |
|---|---:|---|---|---|---|---|
| ECL-9 / US-003 Conductores y disponibilidad | 5 | Frank Roy Yupanqui Acevedo | Finalizada | **Parcial**: alta y elegibilidad acreditadas; la asignación a rutas que debe impedir una licencia vencida y usar la nueva disponibilidad aún no existe | [ST-022](<Sprint 2/validaciones/VALIDACION_ST022.md>), [ST-024](<Sprint 2/validaciones/VALIDACION_ST024.md>), [PR #50](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/50) | Completar con el planificador de rutas (ECL-12, candidato al Sprint 3, primeros del backlog) |
| ECL-11 / US-005 Preferencias de entrega | 3 | Frank Roy Yupanqui Acevedo | Finalizada | **Cumple**: preferencia válida asociada y propuesta en el pedido; datos inválidos rechazados | [ST-028 y reprueba D-01](<Sprint 2/validaciones/VALIDACION_ST028.md>), [PR #49](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/49) | Ratificar la BDD ECL-51 (impedimento I-03) |
| ECL-22 / EN-004 Experiencia móvil, accesible y offline | 8 | Giancarlo Marcio Soto Escobar | Finalizada | **Parcial**: 360 px sin desplazamiento, WCAG 2.1 AA en axe y offline en Chrome/Firefox acreditados; no hay alertas operativas reales ni prueba con lector de pantalla | [Evidencias ECL-22](../../frontend/evidencias/ECL-22-rediseno/README.md), [reprueba offline](../../frontend/evidencias/ECL-58/retest-20261013/README.md), [PR #53](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/53) | Alertas con ECL-14 y prueba con lector de pantalla (Product Backlog — priorizar en el Sprint Planning 3) |
| ECL-23 / EN-005 Capacidad, disponibilidad y observabilidad | 8 | Julio Armando Naupari Camarena | Finalizada | **Parcial**: P95 ≤2 s y 0 % de 5xx en tres corridas; carga sostenida de 100 solicitudes no acreditada (19–21 % de los segundos) y SLA mensual no medido | [ST-035](<Sprint 2/validaciones/VALIDACION_ST035.md>), [ST-036](<Sprint 2/informes/INFORME_ST036.md>) | Repetir la corrida de concurrencia y medir un mes operativo |
| ECL-25 / EN-007 Transferencia de datos y consultas | 3 | Antony Munive Ríos | Finalizada | **No cumple**: el payload del dashboard no es medible porque el dashboard no existe; consultas de pedidos y conductores revisadas | [ST-037](<Sprint 2/informes/INFORME_ST037.md>), [ST-038](<Sprint 2/validaciones/VALIDACION_ST038.md>), [PR #48](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/48) | Medir con el dashboard (ECL-15; Product Backlog — priorizar en el Sprint Planning 3) |

**Lectura:** 27/27 SP cerrados en Jira frente a 3/27 SP con todos sus criterios
acreditados (ECL-11). Las subtareas ECL-46 a ECL-64 pasaron a Finalizada en unas
36 horas y casi todas permanecieron entre 0,5 y 3 segundos en «En curso»; el
análisis de causas está en la [retrospectiva](<04 Retrospectiva del Sprint V_1_0_0.md>).

## Métricas de calidad al corte

Ejecutadas localmente el 13/10/2026 sobre la rama del PR #54 (Python 3.12.10,
Node 22.18.0, PostgreSQL 16.15 + PostGIS 3.6.2). CI de GitHub en verde en los
PR #47–#53.

| Ámbito | Resultado | Antes del parche (12/10) |
|---|---|---|
| Backend: ruff y formato | Sin errores | Sin errores |
| Backend: pruebas unitarias | 613 pasan; cobertura 93,35 % | 560; 93 % |
| Backend: pruebas de integración | 143 pasan (PostgreSQL + PostGIS) | 120 |
| Frontend: eslint y tsc | Sin errores | Sin errores |
| Frontend: pruebas | 529 pasan; cobertura 95,47 % de sentencias | 471 |
| Frontend: build | JS 392,9 KB (120,1 KB gzip); CSS 42,0 KB | JS 343,8 KB (104 KB gzip) |
| Accesibilidad | axe-core 4.13.0 sin violaciones WCAG 2.1 AA en Chrome 155 y Firefox 146.0.1 | Sin auditoría automática del producto completo |
| Contraste | 50 combinaciones de color cumplen AA (temas claro y oscuro) | No verificado |
| Navegación de documentación | `scripts/check_docs.py` sin errores, en CI | 38 documentos sin enlazar |
| Listado de conductores | 2 consultas SQL por página (antes 22 con 20 filas, 102 con 100) | N+1 |
| Dependencias | `npm audit`: 1 vulnerabilidad alta transitiva (`source-map-js`, corrección disponible) | La misma (ST-032) |

## Resultado del parche posterior a la Review

| Fase | Resultado | PR |
|---|---|---|
| 1. Estructura y navegación | Documentos del Sprint 2 dentro de `docs/03 Implementación/`, `.gitignore` completo, README con enlaces de ida y vuelta a los 63 documentos y verificador en CI | [#47](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/47) |
| 2.1 N+1 de conductores | De 22 a 2 consultas por página, con prueba de regresión | [#48](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/48) |
| 2.2 D-01 / P8 | Buscador de clientes y propuesta de preferencias en el pedido; reprueba en Chrome y Firefox aprobada | [#49](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/49) |
| 2.3 Auditoría de conductores (RN-015) | Alta y actualización auditadas sin datos personales; migración 0010 | [#50](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/50) |
| 2.4 Itinerario sin datos ficticios | El ejemplo solo aparece con `VITE_DEMO_ITINERARY=true` | [#51](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/51) |
| 2.5 Datos de demostración | `seed_demo.py` idempotente, solo sobre bases `*_demo` | [#52](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/52) |
| 3. Rediseño UI/UX | Sistema de diseño, modo oscuro, layout por rol e itinerario real; 84 capturas antes/después | [#53](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/53) |
| 3. Reconexión sin evento `online` | Sincronización offline estable; reprueba 3/3 en Chrome 155 y Firefox 157.0 | [#54](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/54) (en revisión) |

## Riesgos para el Sprint 3

| Riesgo | Probabilidad / impacto | Respuesta |
|---|---|---|
| **El optimizador (EP-03: ECL-12, ECL-13, ECL-21, ECL-26) no está iniciado y de él dependen la asignación real de rutas, el dashboard y las métricas de CO₂.** Suma 34 SP de una sola persona responsable | Alta / alto | Empezar por EN-003 (ECL-21) y un VRPTW mínimo con datos de `seed_demo.py`; revisar el alcance del sprint si la primera iteración no está lista a mitad de sprint |
| ECL-25 y RNF-012 siguen sin medirse hasta que exista el dashboard (ECL-15) | Alta / medio | Planificar ECL-15 inmediatamente después de la primera ruta optimizada y medir el payload con el protocolo de ST-037 |
| Criterios cerrados en Jira sin evidencia (subtareas con 0,5–3 s en «En curso») | Media / alto | Aplicar el Definition of Done antes de mover a Finalizada (acción A1 de la retrospectiva) |
| Carga sostenida de 100 solicitudes y SLA mensual sin acreditar | Media / medio | Repetir la corrida con el generador corregido y registrar un mes de disponibilidad (Product Backlog — priorizar en el Sprint Planning 3) |
| BDD de conductores y preferencias en BORRADOR | Media / medio | Ratificación por Frank y Julio antes de implementar nuevas reglas (acción A4) |
| Vulnerabilidad alta transitiva en `source-map-js` | Baja / medio | Actualizar la dependencia y volver a ejecutar `npm audit` (Product Backlog — priorizar en el Sprint Planning 3) |

## Fuentes

- Tablero Jira del proyecto ECL (estados, fechas y Time in Status comunicados al 12/10/2026).
- Pruebas y métricas: ejecuciones locales del 13/10/2026 y CI de los PR citados.
- [Índice de la documentación técnica del Sprint 2](<Sprint 2/README.md>).

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 01/10/2026 | Entregable del Sprint 1; contenido anterior conservado en el historial Git. |
| 1.1.0 | 09/10/2026 | Sustitución del contenido por el entregable del Sprint 2, con evidencias y pendientes al corte. |
| 1.2.0 | 13/10/2026 | Estado por criterios frente a Jira, métricas tras el parche post-Review, PR #47–#54 y riesgos del Sprint 3. |

El nombre V_1_0_0 del archivo se conserva por exigencia de la consigna.

[← Volver al README principal](../../README.md)
