# Evaluación de Calidad de Código — SonarQube

**Nombre del Proyecto:** EcoLogística Lima

**Fecha de Análisis:** 2026-11-12

**Versión del Análisis:** V_1_0_0

| Metadato | Valor |
|---|---|
| Ticket | [ECL-102 — Evaluación final de calidad y seguridad del MVP](https://continental-team-il84x39k.atlassian.net/browse/ECL-102) |
| Redacción | Antony Munive Rios (@ANTONY-MUNIVE), con apoyo de IA (Claude) |
| Proyecto SonarCloud | [JulioNaupariC_EcoLog-stica-Lima](https://sonarcloud.io/project/overview?id=JulioNaupariC_EcoLog-stica-Lima) |
| Análisis evaluado | Rama `main`, commit `8cf6258`, 12/11/2026, el último tras integrar el trabajo del Sprint 4 |
| Alcance analizado | `backend/app` y `frontend/src` (Measures muestra las dos carpetas) |
| Evidencia | Capturas de SonarQube Cloud del 12/11/2026 en [evidencias/ECL-102](<evidencias/ECL-102>) |
| Antecedente | [Calidad de código del Sprint 3](<../Sprint 03/03 Calidad de código V_1_0_0.md>) |

**Cómo se obtiene el análisis.** Igual que en el Sprint 3:
- El job **Quality / SonarCloud** del CI analiza cada PR y cada push a `main`.
- La cobertura llega de los reportes reales de pytest (`coverage.xml`) y Vitest
  (`lcov.info`).
- Con `sonar.qualitygate.wait=true`, un Quality Gate fallido pone el CI en rojo.

## 1. Resumen Ejecutivo de Quality Gate

- **Estado del Quality Gate:** **PASSED** en `8cf6258`. En código nuevo: cobertura
  **97,3 %**, duplicación **0,0 %**, 0 security hotspots y 1 issue nuevo
  (resumen del check «SonarCloud Code Analysis» de ese commit).
- **Porcentaje de Cobertura de Pruebas (Coverage):** **95,6 %** en todo el código (94,5 % en el Sprint 3)
- **Duplicación de Código:** **0,0 %**

| Calificación de SonarCloud | Resultado | Causa |
|---|---|---|
| Fiabilidad (Reliability) | **A** | 2 issues de fiabilidad: 1 de severidad alta abierto (sección 3) y 1 bloqueante que no aparece entre los abiertos (ver la nota de la sección 2). 4 cerrados en los últimos 30 días. |
| Seguridad (Security) | **A** | **0 issues de seguridad.** En el Sprint 3 era C por `S8703`, cerrada en ECL-84 (#87); 2 issues de seguridad cerrados en los últimos 30 días |
| Mantenibilidad (Maintainability) | **A** | Deuda de **10 min**, ratio de deuda 0,0 %, esfuerzo para llegar a A: 0. 3 issues de mantenibilidad cerrados en 30 días |
| Revisión de seguridad (Security Review) | **A** | 0 security hotspots; «100 % Security hotspots reviewed» |

Cobertura medida en local sobre el mismo commit, el 12/11/2026:
- **Backend:** **95,53 %** de sentencias de `app` (5 010 sentencias, 224 sin
  cubrir). 1 327 pruebas unitarias pasan y 2 se omiten (pytest con `--cov=app`).
- **Frontend:** **98,02 %** de líneas, 96 % de sentencias, 93,25 % de ramas y
  95,73 % de funciones. 1 018 pruebas pasan en 65 archivos (Vitest con
  `--coverage`).

El dato de SonarCloud combina ambos reportes.

## 2. Métricas Principales

La severidad usa la escala de la plantilla: Bloqueante = BLOCKER, Alta = CRITICAL,
Media = MAJOR, Baja = MINOR.

| Categoría | Cantidad Detectada | Severidad (Bloqueante / Alta / Media / Baja) |
|---|---|---|
| Bugs (issues de fiabilidad) | 2 | 1 / 1 / 0 / 0 |
| Vulnerabilidades (issues de seguridad) | **0** | — |
| Code Smells (issues de mantenibilidad) | 2 | Abiertos: 1 de severidad alta (el mismo issue de `vrptw.py`) |
| Security Hotspots | **0** | — (Security Review Rating A) |

Las exclusiones del análisis no cambian respecto del Sprint 3: pruebas, `docs/`,
evidencias, `backend/loadtest`, `backend/scripts` y migraciones solo para
cobertura y duplicación. Están justificadas en `sonar-project.properties`.

## 3. Plan de Remediación y Deuda Técnica

- **Deuda Técnica Estimada:** **10 min** en todo el código (Measures → Maintainability: 1 issue, ratio de deuda 0,0 %, calificación A). En el Sprint 3 era de 57 min.
- **Hallazgos del Sprint 3 y su cierre en el Sprint 4:**

  | Hallazgo del Sprint 3 | Acción en el Sprint 4 | Estado |
  |---|---|---|
  | `pythonsecurity:S8703` SSRF en `poll.py` (vulnerabilidad Media) | `safe_origin()` rearma el origen desde la allowlist ([ECL-84](https://continental-team-il84x39k.atlassian.net/browse/ECL-84), [#87](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/87)) | Cerrado: 0 issues de seguridad y calificación A |
  | `typescript:S6845` y `S6843` en `DataTable.tsx` (Media) | Se quitó `tabIndex` de la región estática; el desplazamiento usa botones nativos ([ECL-87](<ECL-87 code smells frontend.md>), [#105](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/105)) | Cerrado |
  | `typescript:S8786` en `driverForm.ts` y `VehiclesPage.tsx` (Media) | Expresiones regulares lineales ([ECL-87](<ECL-87 code smells frontend.md>), [#105](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/105)) | Cerrado |
  | `python:S8414` orden de `CORSMiddleware` (Bloqueante) | Sin cambio: aceptado con justificación desde el 29/10/2026 | Aceptado |

- **Hallazgos detectados y corregidos durante el Sprint 4:**
  1. **`python:S1764` expresiones idénticas en una prueba de
     `test_seed_demo_mvp.py`.** Fiabilidad, detectado por el Quality Gate en el
     PR [#127](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/127). Se
     corrigió antes del merge comparando dos llamadas distintas
     (`primera, segunda = pedidos_demo(), pedidos_demo()`).
  2. **Prueba dependiente de la fecha** (`test_seed_demo`, hora fija). No lo
     detecta SonarCloud. Rompió el CI el 12/11 y se corrigió en
     [#139](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/139). La
     acción A18 de la retrospectiva busca evitarlo.
- **Issue abierto al corte y su corrección:**
  - **Hallazgo:** «Refactor this function to always return tuples of the same
    length».
  - **Ubicación:** `backend/app/optimizacion/vrptw.py`, línea 291
    (`_descanso`).
  - **Impacto:** fiabilidad y mantenibilidad, severidad alta, 10 min de
    esfuerzo. Se detectó hace 6 días (modelo VRPTW, ECL-96).
  - **Causa:** la función devolvía `(Descanso,)` o `()` desde dos `return`
    distintos.
  - **Acción:** **corregido** en
    [#149](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/149). Un
    solo retorno con `tuple(...)[:1]`, sin cambio de comportamiento: 111
    pruebas unitarias y 56 de integración de optimización en verde. Al
    integrarlo, los issues abiertos y la deuda deben quedar en 0. Se confirma
    con el análisis de `main` posterior al merge.

**Nota sobre el conteo.**
- El Overview indica **2 issues** en todo el código, y el gráfico de
  fiabilidad los reparte en Bloqueante 50 % y Alta 50 %.
- El filtro de issues Open/Confirmed y Measures muestran **1 issue abierto**
  (10 min).
- El segundo, de severidad Bloqueante, no está abierto. Por la severidad y el
  historial, corresponde al `S8414` (orden de `CORSMiddleware`), aceptado con
  justificación desde el 29/10/2026. *(Confirmar en SonarCloud con el filtro
  «Accepted».)*

**Calidad fuera de SonarCloud.**
- Auditoría de dependencias bloqueante en el CI desde ECL-85.
- `ruff check` y `ruff format --check` en el backend.
- `eslint` y `tsc` en el frontend.
- Los resultados de seguridad están en el [reporte OWASP](<04 OWASP V_1_0_0.md>).

[Volver al índice del Sprint 4](README.md) ·
[← Volver al README principal](../../../README.md)
