# Evaluación de Calidad de Código — SonarQube

**Nombre del Proyecto:** EcoLogística Lima

**Fecha de Análisis:** 2026-10-29

**Versión del Análisis:** V_1_0_0

| Metadato | Valor |
|---|---|
| Ticket | [ECL-65 / EN-009 — Evaluar la calidad de código con SonarCloud](https://continental-team-il84x39k.atlassian.net/browse/ECL-65) (parte B) |
| Responsable | Antony Munive Ríos — @ANTONY-MUNIVE |
| Proyecto SonarCloud | [JulioNaupariC_EcoLog-stica-Lima](https://sonarcloud.io/project/overview?id=JulioNaupariC_EcoLog-stica-Lima) |
| Análisis evaluado | Rama `main`, commit `7fd891a`, 29/10/2026 15:39 (America/Lima), el último tras integrar el trabajo del Sprint 3 |
| Tamaño analizado | 13 230 líneas de código (`ncloc`) en `backend/app` y `frontend/src` |

**Cómo se obtiene el análisis.** Desde la parte A de ECL-65
([PR #67](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/67)), el análisis automático
de SonarCloud está desactivado y lo ejecuta el job **Quality / SonarCloud** del CI en cada PR y en
cada push a `main`. La cobertura no es estimada: SonarCloud recibe los reportes reales de
**pytest** (`coverage.xml`, job «Backend / Quality and unit») y de **Vitest** (`lcov.info`, job
«Frontend»), y el job verifica que cada archivo cubierto exista en el repositorio antes de enviarlo.
Con `sonar.qualitygate.wait=true`, un Quality Gate fallido pone el CI en rojo: el resultado no
se puede ocultar.

## 1. Resumen Ejecutivo de Quality Gate

- **Estado del Quality Gate:** PASSED
- **Porcentaje de Cobertura de Pruebas (Coverage):** 94,5 %
- **Duplicación de Código:** 0,0 %

| Calificación de SonarCloud | Resultado | Causa |
|---|---|---|
| Fiabilidad (Reliability) | **A** | 0 bugs |
| Seguridad (Security) | **C** | 2 vulnerabilidades MEDIUM (sección 3, hallazgos 1 y 2) |
| Mantenibilidad (Maintainability) | **A** | Deuda de 57 min sobre 13 230 líneas |
| Revisión de seguridad (Security Review) | **A** | 0 security hotspots pendientes |

El Quality Gate por defecto evalúa el **código nuevo**; por eso pasa aunque la calificación
global de seguridad sea C: las dos vulnerabilidades se detectaron el 09/10 y el 25/10, antes
del periodo de código nuevo del último análisis, y se corrigen en el [PR #78](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/78).

Cobertura por componente en las ejecuciones locales del 29/10/2026 sobre el mismo código:
backend **92,81 %** (868 pruebas, pytest) y frontend **97,67 %** de líneas (732 pruebas, Vitest).
El 94,5 % de SonarCloud combina ambas. En el **código nuevo**, que es lo que evalúa el Quality
Gate, SonarCloud mide **94,8 %** de cobertura: 459 líneas por cubrir con 13 sin cubrir (97,2 %
de líneas) y 371 condiciones con 30 sin cubrir
([captura de Measures → Coverage](<evidencias/ECL-65/sonarcloud-measures-coverage-main.png>)).
El [Overview de `main`](<evidencias/ECL-65/sonarcloud-overview-main.png>) muestra el Quality Gate
«Passed — All conditions passed» y las calificaciones de la tabla anterior.

## 2. Métricas Principales

La severidad usa la escala de la plantilla, equivalente a la de SonarCloud: Bloqueante = BLOCKER,
Alta = CRITICAL, Media = MAJOR, Baja = MINOR.

| Categoría | Cantidad Detectada | Severidad (Bloqueante / Alta / Media / Baja) |
|---|---|---|
| Bugs | 0 | — |
| Vulnerabilidades | 2 | 0 / 0 / 2 / 0 |
| Code Smells | 6 | 2 / 0 / 4 / 0 |
| Security Hotspots | 0 | — (Security Review Rating A) |

Exclusiones del análisis, justificadas en `sonar-project.properties`:

| Exclusión | Motivo |
|---|---|
| `frontend/src/**/*.test.ts(x)` y `frontend/src/test/**` | Son pruebas: se analizan como `sonar.tests` y no como código de la aplicación. |
| `docs/**` y `**/evidencias/**` | Documentación y evidencias generadas (JSON, XML, capturas); no son código ejecutable. |
| `backend/loadtest/**` y `backend/scripts/**` | Herramienta de carga (ST-035) y utilidades locales y de demo; no se despliegan con la API. |
| `backend/alembic/versions/**` (solo cobertura y duplicación) | Migraciones generadas y declarativas. |
| `frontend/src/main.tsx` y `env.d.ts` (solo cobertura) | Arranque y tipos del entorno, igual que en `frontend/vite.config.ts`. |

## 3. Plan de Remediación y Deuda Técnica

- **Deuda Técnica Estimada:** **57 min** de mantenibilidad (`sqale_index`, los 6 code smells).
  Sumando las 2 vulnerabilidades (30 min cada una), el esfuerzo total de remediación que
  calcula SonarCloud es **1 h 57 min** (8 issues).
- **Principales hallazgos y acciones correctivas:**
  1. **SSRF en el sondeo de disponibilidad.** `pythonsecurity:S8703`, vulnerabilidad Media, en
     `backend/app/monitoring/poll.py:17`. **Corregido** en el [PR #78](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/78):
     el sondeo solo acepta hosts de loopback salvo los declarados en `MONITOR_ALLOWED_HOSTS`,
     con 6 pruebas nuevas.
  2. **«Credencial embebida».** `python:S2068`, vulnerabilidad Media, en
     `backend/app/api/dependencies.py:19`. **Falso positivo, eliminado** en el
     [PR #78](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/78): era el mensaje de error
     «Cambio de contraseña requerido»; la constante se renombra sin cambiar la API.
  3. **Función que siempre devuelve el mismo valor.** `python:S3516`, Bloqueante, en
     `backend/app/monitoring/poll.py:50`. **Corregido** en el [PR #78](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/78):
     `main()` devuelve 130 cuando se interrumpe con Ctrl+C.
  4. **Orden de `CORSMiddleware`.** `python:S8414`, Bloqueante, en `backend/app/main.py:93`.
     **Aceptado con justificación, sin cambio:** `MetricsMiddleware` va por fuera a propósito
     para contar también las solicitudes preflight CORS (ECL-60, prueba
     `test_cors_preflight_and_unsupported_method_are_counted`) y no genera respuestas propias.
     Julio Naupari lo registró como *Accepted* en SonarCloud con este motivo el 29/10/2026;
     los issues abiertos de `main` bajaron de 8 a 7.
  5. **`tabIndex` en un elemento no interactivo.** `typescript:S6845`, Media, en
     `frontend/src/components/ui/DataTable.tsx:25`. **Planificado:**
     [ECL-87](https://continental-team-il84x39k.atlassian.net/browse/ECL-87), Sprint 4.
  6. **Elemento interactivo con rol no interactivo.** `typescript:S6843`, Media, en
     `frontend/src/components/ui/DataTable.tsx:36`. **Planificado:**
     [ECL-87](https://continental-team-il84x39k.atlassian.net/browse/ECL-87), Sprint 4,
     sin regresión de la evaluación WCAG de ECL-67.
  7. **Expresión regular con backtracking superlineal.** `typescript:S8786`, Media, en
     `frontend/src/domain/driverForm.ts:59`. **Planificado:**
     [ECL-87](https://continental-team-il84x39k.atlassian.net/browse/ECL-87), Sprint 4.
  8. **Expresión regular con backtracking superlineal.** `typescript:S8786`, Media, en
     `frontend/src/pages/VehiclesPage.tsx:60`. **Planificado:**
     [ECL-87](https://continental-team-il84x39k.atlassian.net/browse/ECL-87), Sprint 4.

Con el PR #78 aplicado, quedan 4 de los 8 issues (todos Media, frontend), unos 50 min de
deuda, y la calificación de seguridad pasa a **A** al no quedar vulnerabilidades abiertas.
Ese resultado se confirmará con el siguiente análisis de `main` y se registrará en el Sprint 4.

**Calidad fuera de SonarCloud.** La auditoría de dependencias del mismo commit encontró
vulnerabilidades conocidas solo en herramientas de desarrollo (`vite`, `vitest`, `certifi`,
`setuptools` y transitivas). Se corrigen en el [PR #77](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/77);
el detalle está en el Reporte de Seguridad OWASP de ECL-66 (`04 OWASP V_1_0_0.md`).

[Evidencias ECL-65](<evidencias/ECL-65/README.md>) ·
[Volver al índice del Sprint 3](README.md) ·
[← Volver al README principal](../../../README.md)
