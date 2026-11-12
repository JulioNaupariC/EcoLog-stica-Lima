# Revisión del sprint

**Nombre del Proyecto:** EcoLogística Lima

**Líder del Proyecto:** Julio Armando Naupari Camarena

| Metadato | Valor |
|---|---|
| Ticket | [ECL-100 — Documentar la Revisión del Sprint 4 con la demostración del MVP](https://continental-team-il84x39k.atlassian.net/browse/ECL-100) |
| Sprint | Sprint 4 «Rutas y Cierre MVP», sprint 39 de Jira |
| Periodo | 04/11/2026 al 20/11/2026 en Jira (America/Lima). La evaluación se adelantó a la Inspección 4 del **13/11/2026, 14:20** |
| Objetivo del sprint | Entregar el MVP de EcoLogística Lima: generar rutas optimizadas sostenibles (US-006, VRPTW en ≤ 45 s para 150 pedidos y 15 vehículos), visualizarlas en el mapa (US-008) y consultar el dashboard de sostenibilidad (US-009) con parámetros versionados (EN-008); cerrar los pendientes de calidad, seguridad y accesibilidad, aplicar la retroalimentación del Sprint 3 y dejar la demo ejecutable en una PC de laboratorio. |
| Versión | 1.0.0 |
| Fecha de corte | 12/11/2026, 21:00 |
| Redacción | Antony Munive Rios (@ANTONY-MUNIVE), con apoyo de IA (Claude), con los datos de Jira y GitHub al corte |
| Revisión del contenido | Julio Naupari (dueño de ECL-100) y Giancarlo Soto (dueño suplente de docs) |
| Fuentes | Jira sprint 39; PR #87 a #144 de GitHub; checks de CI de `main`; documentos de `docs/03 Implementación/Sprint 04` |

**Alcance temporal.** El informe tiene corte al 12/11/2026. La sección 6
«Registro de la Review del 13/11/2026» se completa después de la evaluación, con
lo que ocurra en ella. No se declara una demostración exitosa antes de
ejecutarla.

## 1. Estado del backlog y velocidad

En Jira, el sprint 39 tiene **47 elementos**: 41 con puntos y 6 subtareas sin
puntos (ECL-93, 94, 95, 96, 119 y 120, todas «Finalizada»).

| Medida | Valor al corte |
|---|---|
| Puntos planificados | **108 SP** |
| Puntos finalizados | **95 SP (88 %)** |
| Elementos con puntos finalizados | 34 de 41 |
| Sin finalizar | [ECL-68](https://continental-team-il84x39k.atlassian.net/browse/ECL-68) (3 SP, «In Review / QA») · [ECL-100](https://continental-team-il84x39k.atlassian.net/browse/ECL-100) a [ECL-104](https://continental-team-il84x39k.atlassian.net/browse/ECL-104) (8 SP, documentos de cierre en PR) · [ECL-105](https://continental-team-il84x39k.atlassian.net/browse/ECL-105) (2 SP, PR #142 y #143) |
| Fuera del sprint, en backlog | [ECL-13 / US-007](https://continental-team-il84x39k.atlassian.net/browse/ECL-13) (8 SP), [ECL-107](https://continental-team-il84x39k.atlassian.net/browse/ECL-107) (3 SP), [ECL-121](https://continental-team-il84x39k.atlassian.net/browse/ECL-121) (5 SP), [ECL-122](https://continental-team-il84x39k.atlassian.net/browse/ECL-122) (3 SP) |

Los 8 SP de documentos de cierre se finalizan al integrar sus PR. Si entran antes
de la evaluación, la velocidad sube a **105 de 108 SP**. El estado de Jira no
reemplaza la verificación del
[Definition of Done](<../../02 Planificación/01 Transformando a ágil V_1_0_0.md#8-definition-of-done-dod-global>)
(sección 4).

## 2. Cumplimiento del objetivo

| Parte del objetivo | Resultado al corte |
|---|---|
| US-006: rutas optimizadas con VRPTW en ≤ 45 s para 150 pedidos y 15 vehículos | **Cumplido.** [ECL-12](https://continental-team-il84x39k.atlassian.net/browse/ECL-12). P95 de **20,18 s** en 30 corridas ([ECL-21](<ECL-21 benchmark RNF-001.md>)). La optimización se solicita por la API; la interfaz aún no tiene botón para generarla (ver sección 5). |
| US-008: rutas y alertas en mapa | **Cumplido.** [ECL-14](<ECL-14 mapa rutas.md>), con lista accesible como alternativa al mapa |
| US-009: dashboard de sostenibilidad | **Cumplido.** [ECL-15](<ECL-15 dashboard sostenibilidad.md>), con cierre de rutas real de [ECL-119](<ECL-119 cierre de rutas y sostenibilidad.md>) y [ECL-120](<ECL-120 registro y cierre de rutas.md>) |
| EN-008: parámetros versionados | **Cumplido con observación.** Versionado, fórmulas e instantánea por optimización integrados. El archivo de casos de referencia de RNF-011 solo tiene la cabecera ([ECL-26](<ECL-26 parametros versionados y casos de referencia.md>)). |
| Pendientes de calidad, seguridad y accesibilidad del Sprint 3 | **Cumplido.** ECL-83 (WCAG 2.2.1), ECL-84 (S8703 y cabeceras), ECL-85 (cadena de suministro), ECL-86 (modelo de amenazas) y ECL-87 (code smells) finalizados |
| Retroalimentación del Sprint 3 | **Cumplido.** [ECL-99](https://continental-team-il84x39k.atlassian.net/browse/ECL-99) y [ECL-92](https://continental-team-il84x39k.atlassian.net/browse/ECL-92) (una carpeta por sprint) |
| Demo ejecutable en una PC de laboratorio | **No acreditado al corte.** [ECL-68](https://continental-team-il84x39k.atlassian.net/browse/ECL-68) sigue en «In Review / QA», sin registro de una ejecución en el laboratorio |

## 3. Historias completadas

### 3.1 Historias de usuario

| Historia / Jira | Criterio esperado | Resultado demostrado | Evidencia |
|---|---|---|---|
| **US-006** · [ECL-12](https://continental-team-il84x39k.atlassian.net/browse/ECL-12) · 13 SP · Antony | Plan VRPTW que respete capacidad, ventanas, jornada y descansos. Pedidos no asignados con motivo. ≤ 45 s para 150 pedidos y 15 vehículos (RNF-001). | Optimización real de 150 pedidos y 15 vehículos: `COMPLETADA`, 10 rutas y 2 pedidos inviables con motivo (capacidad y ventana) en la corrida del 12/11/2026. P95 de 20,18 s en 30 corridas. | Subtareas ECL-93 a ECL-96: spike [#88](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/88), contrato [#89](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/89) y [#108](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/108), modelo [#109](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/109), servicio [#111](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/111); [ECL-96](<ECL-96 servicio de optimizacion.md>); benchmark [#113](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/113) |
| **US-008** · [ECL-14](https://continental-team-il84x39k.atlassian.net/browse/ECL-14) · 8 SP · José | Rutas en mapa con paradas, ETA y alertas; alternativa accesible; degradación sin tráfico en vivo. | Mapa Leaflet con OpenStreetMap, lista accesible en el mismo orden y ETA rotuladas como de planificación. axe sin violaciones (ECL-103). | [#104](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/104), [ECL-14](<ECL-14 mapa rutas.md>) |
| **US-009** · [ECL-15](https://continental-team-il84x39k.atlassian.net/browse/ECL-15) · 5 SP · Giancarlo | Indicadores por periodo calculados sobre rutas cerradas: distancia, CO₂, combustible, costo, ahorro y cumplimiento de ventanas. | El Operador registra paradas y cierra la ruta; el dashboard muestra la ruta cerrada. Cierre de `DEMO-004` (5 paradas) con **34,01 %** de ahorro de distancia. | Dashboard [#116](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/116); backend [#117](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/117) (ECL-119); pantalla [#119](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/119) (ECL-120) |

La BDD de las tres historias se definió en
[ECL-97](https://continental-team-il84x39k.atlassian.net/browse/ECL-97) (Frank,
[#91](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/91)) y la ratificó
Julio ([#100](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/100)).

### 3.2 Historias técnicas y tareas

| Historia técnica / Jira | Criterio DoD | Resultado | Evidencia |
|---|---|---|---|
| **EN-003** · [ECL-21](https://continental-team-il84x39k.atlassian.net/browse/ECL-21) · 8 SP · Antony | Benchmark automatizado de RNF-001 | P95 de 20,18 s ≤ 45 s en 30 corridas de extremo a extremo. La parte de cola con worker y RNF-002 pasa a [ECL-121](https://continental-team-il84x39k.atlassian.net/browse/ECL-121). | [#113](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/113), [ECL-21](<ECL-21 benchmark RNF-001.md>) |
| **EN-008** · [ECL-26](https://continental-team-il84x39k.atlassian.net/browse/ECL-26) · 5 SP · Antony | Parámetros versionados y exactitud de cálculos | Versiones sin edición ni borrado, fórmulas sin redondeo intermedio e instantánea por optimización. **Casos de referencia de RNF-011 pendientes** (Julio). | [#110](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/110), [ECL-26](<ECL-26 parametros versionados y casos de referencia.md>) |
| Conductores: [ECL-79](https://continental-team-il84x39k.atlassian.net/browse/ECL-79) (5), [ECL-80](https://continental-team-il84x39k.atlassian.net/browse/ECL-80) (2), [ECL-81](https://continental-team-il84x39k.atlassian.net/browse/ECL-81) (1), [ECL-123](https://continental-team-il84x39k.atlassian.net/browse/ECL-123) (1) | Elegibilidad y RN-005; BDD D8; formato de licencia | Elegibilidad con motivos de asignación; consulta anonimizada para Auditor; licencia validada en backend y frontend según RF-003 V_1_2_0 | [#118](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/118), [#122](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/122), [#125](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/125), [ECL-79](<ECL-79 elegibilidad conductores.md>), [ECL-80/81](<ECL-80-81 decisiones BDD conductores.md>) |
| Incidencias: [ECL-82](https://continental-team-il84x39k.atlassian.net/browse/ECL-82) (2), [ECL-98](https://continental-team-il84x39k.atlassian.net/browse/ECL-98) (3) | I03 de la BDD; validar o descartar | La jornada de la parada se valida (403 si la parada no es de la jornada del conductor). El Operador valida o descarta. | [#115](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/115), [#102](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/102), [ECL-98](<ECL-98 resolucion incidencias.md>), [validación US-012](<VALIDACION_US012_ECL82_V_1_1_0.md>) |
| Calidad y seguridad: [ECL-83](https://continental-team-il84x39k.atlassian.net/browse/ECL-83), [ECL-84](https://continental-team-il84x39k.atlassian.net/browse/ECL-84) (3), [ECL-85](https://continental-team-il84x39k.atlassian.net/browse/ECL-85) (2), [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86) (3), [ECL-87](https://continental-team-il84x39k.atlassian.net/browse/ECL-87) (2) | Cerrar los hallazgos del Sprint 3 | Aviso y renovación de sesión; cabeceras de seguridad y S8703 cerrada; Actions por SHA y auditoría de dependencias bloqueante; STRIDE con alertas; code smells del frontend corregidos | [#107](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/107), [#87](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/87), [#126](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/126), [#120](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/120), [#105](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/105) |
| Green IT: [ECL-108](https://continental-team-il84x39k.atlassian.net/browse/ECL-108) a [ECL-118](https://continental-team-il84x39k.atlassian.net/browse/ECL-118) (20 SP) | Ocho optimizaciones medidas antes y después, con informe | Línea base, ocho optimizaciones, Lighthouse CI, medición después, SWDM v4 e informes 01 y 02 | [#90](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/90), [#93](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/93)–[#97](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/97), [#99](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/99), [#103](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/103), [#106](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/106), [#114](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/114), [#121](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/121); [informe 01](<../reduccion del impacto ambiental/01 Informe de reduccion del impacto ambiental V_1_0_0.md>) |
| Acuerdos de la retrospectiva del Sprint 3: [ECL-88](https://continental-team-il84x39k.atlassian.net/browse/ECL-88) a [ECL-91](https://continental-team-il84x39k.atlassian.net/browse/ECL-91) (5 SP) | A9 a A12 aplicados | Protección de `main` con Code Owners y rama al día; regla A10; guía de entorno local; regla A12 | [#123](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/123), [#92](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/92), [#124](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/124), [guía ECL-90](<guias/GUIA_ENTORNO_LOCAL_ECL90.md>), [ECL-91](<ECL-91 corte de alcance de PR.md>). Su cumplimiento se mide en la Retrospectiva. |
| Organización: [ECL-92](https://continental-team-il84x39k.atlassian.net/browse/ECL-92) (1), [ECL-99](https://continental-team-il84x39k.atlassian.net/browse/ECL-99) (1), [ECL-106](https://continental-team-il84x39k.atlassian.net/browse/ECL-106) (1) | Retroalimentación docente y ensayo | Una carpeta por sprint; plantilla y glosario del Sprint 4; ensayo cronometrado de la exposición | [#85](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/85), [#101](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/101), [convenciones](<CONVENCIONES_Y_GLOSARIO_ECL99.md>) |

## 4. Verificación del Definition of Done

| Criterio del DoD | Resultado al corte |
|---|---|
| Cobertura ≥ 80 % y pruebas en verde | CI exige `--cov-fail-under=80` en backend y umbrales en Vitest. Al corte se recogen **1 329 pruebas unitarias** y **348 de integración** en backend. El frontend pasa **1 018 pruebas en 65 archivos**. |
| SAST sin vulnerabilidades críticas | CodeQL (Python y JS/TS) y SonarCloud en verde sobre `main`. Las cifras del proyecto completo van en el informe de calidad y OWASP ([ECL-102](https://continental-team-il84x39k.atlassian.net/browse/ECL-102)). |
| Revisión por otra persona | Los 42 PR integrados del sprint (#87 a #139) tienen al menos una aprobación de otra persona. Solo 3 de las 90 aprobaciones dicen qué se revisó (regla A10); se analiza en la Retrospectiva. |
| CI en verde al integrar | Checks requeridos en verde en `main` (`8cf6258`): backend unitario e integración, frontend, CodeQL, SonarCloud, navegación de docs, auditoría de dependencias y Lighthouse |
| Despliegue automatizado en Staging / Pruebas | **Sigue como excepción.** [ECL-107](https://continental-team-il84x39k.atlassian.net/browse/ECL-107) no entró al sprint. El entorno de pruebas automatizado es el job de integración con PostGIS efímero. |
| Documentación y OpenAPI | Endpoints de optimización, rutas, cierre y sostenibilidad en OpenAPI (`/docs`) y `backend/README.md`; un documento por ticket en esta carpeta |
| BDD aprobada y evidencia | [ECL-97](https://continental-team-il84x39k.atlassian.net/browse/ECL-97) ratificada por Julio; evidencias por ticket en `evidencias/` |
| Sin defectos bloqueantes | Ninguno abierto. Los hallazgos de la sección 5 no impiden la demo y tienen una alternativa. |

**Conclusión:** US-006, US-008, US-009 y las historias técnicas cumplen el DoD
**salvo el criterio de staging**, que sigue como excepción registrada en ECL-107.
EN-008 se integra con la observación de sus casos de referencia.

## 5. Hallazgos para el siguiente incremento

| Observación | Responsable propuesto | Ticket | Acción |
|---|---|---|---|
| La optimización solo se solicita por la API (Swagger). La pantalla de rutas no tiene botón para generarla. | José y Antony | Por crear | Botón «Optimizar fecha» para el Operador, con estado de la corrida |
| Un conductor no puede reportar una incidencia sobre una parada de `seed_demo` (modelo del Sprint 3): la API responde 403 por la regla I03. | Antony | Por crear | Migrar los datos de demo del Sprint 3 al modelo de rutas, o retirarlos |
| La lista de rutas muestra los km con unos 13 decimales. | José | Por crear | Redondear al presentar (1 o 2 decimales) |
| El menú muestra «Próximamente: Rutas optimizadas», aunque la vista ya existe. | Giancarlo | Por crear | Retirar el texto obsoleto |
| La sesión del Operador se pierde al recargar la página. | Giancarlo y Antony | Por crear | Recuperar la sesión desde la cookie al iniciar la app |
| «Equivalente ambiental: No disponible»: no hay factor de captura con fuente. | Julio | [ECL-26](https://continental-team-il84x39k.atlassian.net/browse/ECL-26) | Registrar la fuente y la versión de `CAPTURA_CO2_ARBOL_ANIO` |
| Casos de referencia de RNF-011 vacíos | Julio | [ECL-26](https://continental-team-il84x39k.atlassian.net/browse/ECL-26) | Completar el CSV con casos calculados a mano |
| Demo en PC de laboratorio sin acreditar | Julio | [ECL-68](https://continental-team-il84x39k.atlassian.net/browse/ECL-68) | Ejecutar la guía de ECL-105 en el laboratorio y registrar tiempos |
| Reoptimización (US-007), cola con worker (RNF-002) y alerta 5xx desplegable | José y Antony | [ECL-13](https://continental-team-il84x39k.atlassian.net/browse/ECL-13), [ECL-121](https://continental-team-il84x39k.atlassian.net/browse/ECL-121), [ECL-122](https://continental-team-il84x39k.atlassian.net/browse/ECL-122) | Backlog para un siguiente incremento |
| Ambiente de staging | Julio | [ECL-107](https://continental-team-il84x39k.atlassian.net/browse/ECL-107) | Cerrar la excepción del DoD |

Ninguno de estos hallazgos impide la demostración: la
[guía de ECL-105](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/143)
indica cómo evitarlos durante la exposición.

## 6. Demostración del Sprint

### 6.1 Ensayo medido del 12/11/2026

| Campo | Registro |
|---|---|
| Quién ejecutó | Antony Munive, con un recorrido automatizado con Playwright |
| Equipo y entorno | Contenedor Linux de 2 CPU; build de producción del frontend, API local y PostgreSQL 16 con PostGIS |
| Datos | `seed_demo_mvp`: 150 pedidos, 15 vehículos y 4 distritos ([#127](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/127); ajuste de fecha en [#142](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/142)) |
| Flujos y roles | Operador: optimizar, mapa, registrar paradas, cerrar ruta, dashboard y validar incidencia. Conductor: itinerario móvil y reporte de incidencia. |
| Resultado observado | Optimización `COMPLETADA` en **20,1 s** con 10 rutas; ruta cerrada; dashboard con rutas cerradas; incidencia validada. Tiempos por paso en la guía de ECL-105. |
| Fallos e impedimentos | Sin `#142`, la fecha de hoy quedaba con 157 pedidos y el motor la rechazaba (límite 150). Los hallazgos de la sección 5. |
| Evidencias | Capturas de mapa, ruta cerrada, dashboard y validación en `evidencias/ECL-105/` ([#143](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/143)) |

Este ensayo mide el tiempo del sistema, sin el tiempo de quien expone. No
reemplaza la validación en el laboratorio de [ECL-68](https://continental-team-il84x39k.atlassian.net/browse/ECL-68).

### 6.2 Registro de la Review del 13/11/2026 (completar después)

| Campo | Registro |
|---|---|
| Quién ejecutó la demostración | Pendiente |
| Fecha y equipo utilizado | 13/11/2026, pendiente |
| Sistema operativo y navegador | Pendiente |
| Flujos y roles demostrados | Pendiente |
| Resultado observado | Pendiente |
| Fallos e impedimentos | Pendiente |
| Retroalimentación del docente | Pendiente |

[Índice del Sprint 4](README.md) · [← Volver al README principal](../../../README.md)
