# Revisión del sprint

**Nombre del Proyecto:** EcoLogística Lima

**Líder del Proyecto:** Julio Armando Naupari Camarena

| Metadato | Valor |
|---|---|
| Ticket | [ECL-69 — Documentar la Revisión del Sprint 3](https://continental-team-il84x39k.atlassian.net/browse/ECL-69) |
| Sprint | Sprint 3 «Calidad y Seguridad», sprint 38 de Jira |
| Periodo | 26/10/2026 al 30/10/2026 (America/Lima) |
| Objetivo del sprint | Entregar el registro de incidencias del conductor (US-012) y acreditar la calidad de código (SonarCloud), la seguridad (OWASP Top 10 2025) y la accesibilidad (WCAG 2.1 AA), dejando la aplicación ejecutable en una PC de laboratorio sin permisos de administrador para la demostración del 30/10/2026. |
| Versión | 1.0.0 |
| Fecha de corte | 29/10/2026 |
| Autor | Julio Armando Naupari Camarena — @JulioNaupariC |
| Fuentes | Jira sprint 38, PR y documentos de validación del repositorio; hechos disponibles hasta el 29/10/2026 |

**Alcance temporal.** Este informe es un estado **previo** a la Review del 30/10/2026. No presenta como realizada una demostración ante el docente que aún no ha ocurrido.

## Historias de Usuario completadas en este Sprint

### Estado del backlog y criterio de terminado

En la fotografía actualizada de Jira del sprint 38 al 29/10/2026 figuran **15 elementos: 13 en «Finalizada»** ([ECL-18](https://continental-team-il84x39k.atlassian.net/browse/ECL-18), [ECL-65](https://continental-team-il84x39k.atlassian.net/browse/ECL-65), [ECL-66](https://continental-team-il84x39k.atlassian.net/browse/ECL-66), [ECL-67](https://continental-team-il84x39k.atlassian.net/browse/ECL-67), [ECL-70](https://continental-team-il84x39k.atlassian.net/browse/ECL-70), [ECL-71](https://continental-team-il84x39k.atlassian.net/browse/ECL-71), [ECL-72](https://continental-team-il84x39k.atlassian.net/browse/ECL-72), [ECL-73](https://continental-team-il84x39k.atlassian.net/browse/ECL-73), [ECL-74](https://continental-team-il84x39k.atlassian.net/browse/ECL-74), [ECL-75](https://continental-team-il84x39k.atlassian.net/browse/ECL-75), [ECL-76](https://continental-team-il84x39k.atlassian.net/browse/ECL-76), [ECL-77](https://continental-team-il84x39k.atlassian.net/browse/ECL-77) y [ECL-78](https://continental-team-il84x39k.atlassian.net/browse/ECL-78)) y **2 sin finalizar**: [ECL-68](https://continental-team-il84x39k.atlassian.net/browse/ECL-68) «En curso» y [ECL-69](https://continental-team-il84x39k.atlassian.net/browse/ECL-69) en revisión, que se finalizará con la aprobación e integración de este PR. El estado Jira no sustituye la verificación de la [Definition of Done (DoD) global](<../../02 Planificación/01 Transformando a ágil V_1_0_0.md#8-definition-of-done-dod-global>).

### Cumplimiento del objetivo y velocidad

| Parte del objetivo | Resultado |
|---|---|
| Registro de incidencias del conductor (US-012) | Cumplido ([ECL-18](https://continental-team-il84x39k.atlassian.net/browse/ECL-18) Finalizada; I03 con jornada pendiente en [ECL-82](https://continental-team-il84x39k.atlassian.net/browse/ECL-82)) |
| Calidad de código con SonarCloud | Cumplido: Quality Gate PASSED, cobertura 94,5 %, duplicación 0,0 % |
| Seguridad OWASP Top 10 2025 | Cumplido con 1 vulnerabilidad Media pendiente (S8703, [ECL-84](https://continental-team-il84x39k.atlassian.net/browse/ECL-84)) |
| Accesibilidad WCAG 2.1 AA | Cumplido con el criterio 2.2.1 pendiente ([ECL-83](https://continental-team-il84x39k.atlassian.net/browse/ECL-83)) |
| App ejecutable en una PC de laboratorio sin administrador | No cumplido: validada solo en la laptop de desarrollo; pasa al Sprint 4 ([ECL-68](https://continental-team-il84x39k.atlassian.net/browse/ECL-68)) |

**Velocidad:** **20 SP finalizados de 26 planificados** al corte ([ECL-18](https://continental-team-il84x39k.atlassian.net/browse/ECL-18) 5, [ECL-65](https://continental-team-il84x39k.atlassian.net/browse/ECL-65) 3, [ECL-66](https://continental-team-il84x39k.atlassian.net/browse/ECL-66) 3, [ECL-67](https://continental-team-il84x39k.atlassian.net/browse/ECL-67) 3, [ECL-77](https://continental-team-il84x39k.atlassian.net/browse/ECL-77) 5 y [ECL-78](https://continental-team-il84x39k.atlassian.net/browse/ECL-78) 1). [ECL-69](https://continental-team-il84x39k.atlassian.net/browse/ECL-69), [ECL-70](https://continental-team-il84x39k.atlassian.net/browse/ECL-70) y [ECL-71](https://continental-team-il84x39k.atlassian.net/browse/ECL-71) suman **3 SP adicionales** al integrarse los documentos de cierre. Esta métrica de 20 SP corresponde al corte funcional informado, mientras el conteo de 13/15 refleja el estado Jira actualizado.

El DoD global exige simultáneamente: cobertura ≥80 % y pruebas obligatorias en verde; análisis SAST (SonarQube y/o CodeQL) sin vulnerabilidades críticas abiertas; revisión por una persona técnica distinta del autor; despliegue automatizado ejecutable en staging/pruebas; documentación y OpenAPI cuando aplique; BDD aprobada, evidencia y trazabilidad; y ausencia de defectos bloqueantes. En los apartados siguientes se distingue **integración / estado Jira** de **evidencia suficiente para afirmar cada condición del DoD**.

### US-012 — Registrar incidencias de operación y seguridad vial

**[ECL-18](https://continental-team-il84x39k.atlassian.net/browse/ECL-18) — 5 SP, «Finalizada».** Implementación integrada de acuerdo con la BDD y las dependencias técnicas:

| Componente | Responsable | Trabajo y evidencia |
|---|---|---|
| [ECL-72](https://continental-team-il84x39k.atlassian.net/browse/ECL-72) — BDD | Frank | [PR #62](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/62) (borrador inicial) y [PR #63](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/63) (ratificación/aprobación de Julio); escenarios de incidencia de operación y seguridad vial |
| [ECL-73](https://continental-team-il84x39k.atlassian.net/browse/ECL-73) — Modelo y API | Antony | [PR #61](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/61) y [PR #65](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/65); migración `0013`, `POST /conductor/incidencias` idempotente por `operation_id`, `GET /incidencias` para Administrador y Operador |
| [ECL-74](https://continental-team-il84x39k.atlassian.net/browse/ECL-74) — Formulario móvil | José | [PR #69](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/69); reporte de incidencia, borrador y cola sin conexión |
| [ECL-75](https://continental-team-il84x39k.atlassian.net/browse/ECL-75) — Operación | Giancarlo | [PR #70](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/70); vista de incidencias pendientes y restricciones por rol |
| [ECL-76](https://continental-team-il84x39k.atlassian.net/browse/ECL-76) — Pruebas por ruta | José | [PR #73](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/73); matriz I01–I16, campaña con API y PostGIS reales: **10/10 en Chrome y 10/10 en Firefox** |

**Trazabilidad y evidencia:** [matriz de US-012](<validaciones/VALIDACION_US012.md>), [validación del formulario](<validaciones/VALIDACION_ST041.md>), [validación de la vista de Operación](<validaciones/VALIDACION_ST042.md>) y [evidencias de la campaña](<validaciones/evidencias/ECL-76/cierre-20261027/README.md>). La incidencia enviada offline se sincroniza al reconectar sin duplicarla según el contrato de idempotencia. La **validación de jornada del caso I03 sigue parcial** y se transfiere a [ECL-82](https://continental-team-il84x39k.atlassian.net/browse/ECL-82), dependiente del modelo de rutas del Sprint 4.

### US-013 — Restablecer contraseña de un usuario

**[ECL-77](https://continental-team-il84x39k.atlassian.net/browse/ECL-77) — 5 SP, «Finalizada».** Antony implementó en el [PR #59](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/59) el restablecimiento mediante contraseña temporal de **24 horas**, válida para un solo ciclo, cambio obligatorio a una contraseña definitiva de **al menos 12 caracteres**, revocación de sesiones anteriores y registro de auditoría. El flujo y los controles se documentan en la [validación de US-013](<validaciones/VALIDACION_US013.md>) y las [evidencias visuales ECL-77](<validaciones/evidencias/ECL-77/README.md>).

**Complemento [ECL-78 / EN-013](https://continental-team-il84x39k.atlassian.net/browse/ECL-78) — 1 SP, «Finalizada»:** script de restablecimiento para la demo, [PR #60](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/60). Es un apoyo a la demostración, no una HU independiente.

### Enablers y tareas técnicas: calidad, seguridad y accesibilidad

| Entregable | Responsable y estado | Resultados comprobados y límite |
|---|---|---|
| [ECL-65 / EN-009](https://continental-team-il84x39k.atlassian.net/browse/ECL-65) — SonarCloud, 3 SP | Antony; Finalizada | CI en [PR #67](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/67) y [documento de calidad en PR #80](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/80). [Reporte de calidad](<03 Calidad de código V_1_0_0.md>): **Quality Gate PASSED**, cobertura **94,5 %**, duplicación **0,0 %**. Calidad agregada; no sustituye pruebas por HU. |
| [ECL-66 / EN-010](https://continental-team-il84x39k.atlassian.net/browse/ECL-66) — OWASP Top 10 2025, 3 SP | Antony; Finalizada | [PR #77](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/77) (dependencias), [PR #78](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/78) (hallazgos), [PR #79](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/79) (reporte). [Reporte OWASP](<04 OWASP V_1_0_0.md>): vulnerabilidades de **2 a 1**, queda **S8703** mitigada en código, pendiente de cierre en [ECL-84](https://continental-team-il84x39k.atlassian.net/browse/ECL-84); no declarar 0 vulnerabilidades. |
| [ECL-67 / EN-011](https://continental-team-il84x39k.atlassian.net/browse/ECL-67) — WCAG 2.1 AA, 3 SP | Giancarlo; Finalizada | [PR #71](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/71) y [PR #72](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/72); [evaluación WCAG](<05 WCAG V_1_0_0.md>). Criterio **2.2.1** (aviso de sesión de 60 minutos) pendiente en [ECL-83](https://continental-team-il84x39k.atlassian.net/browse/ECL-83); no declarar cumplimiento sin observaciones. |

### Verificación del Definition of Done

| Criterio del DoD | US-012 | US-013 | Enablers (ECL-65, 66, 67) |
|---|---|---|---|
| Cobertura ≥80 % y pruebas en verde | CI con `--cov-fail-under=80` en backend y umbrales de Vitest; SonarCloud en código nuevo: 93,3 % ([#69](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/69)) y 98,2 % ([#70](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/70)); 868 pruebas unitarias del backend | Mismo gate del backend en el [#59](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/59); 868 pruebas unitarias del backend | 96,6 % en código nuevo ([#71](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/71)) y 100 % ([#78](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/78)); total del proyecto 94,5 % |
| SAST sin vulnerabilidades críticas | CodeQL en todos los PR; SonarCloud desde el [#67](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/67) | CodeQL en el [#59](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/59) | 0 críticas; 1 Media pendiente (S8703, [ECL-84](https://continental-team-il84x39k.atlassian.net/browse/ECL-84)) |
| Peer review por otra persona | Sí: [#61](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/61) Frank, [#62](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/62) Antony, [#63](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/63) Julio, [#65](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/65) Julio, [#69](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/69) Antony, [#70](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/70) José, [#73](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/73) Giancarlo | Sí: [#59](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/59) José, [#60](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/60) José | Sí: [#67](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/67) y [#78](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/78) Julio; [#71](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/71) y [#72](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/72) José; [#77](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/77) Giancarlo y Julio; [#79](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/79) y [#80](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/80) Frank |
| CI en verde al integrar | Todos los checks en verde (7 antes del [#67](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/67), 9 desde el [#67](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/67)) | Todos los checks en verde | Todos los checks en verde |
| Despliegue automatizado en Staging / Pruebas | **Excepción:** no existe ambiente de staging; entorno de pruebas automatizado: job «Backend / Integration» del CI con PostGIS efímero y demo local reproducible de [ECL-68](https://continental-team-il84x39k.atlassian.net/browse/ECL-68) | Misma excepción | Misma excepción |
| Documentación y OpenAPI | Endpoints de incidencias en OpenAPI y `backend/README.md`; validaciones [ST-041](<validaciones/VALIDACION_ST041.md>), [ST-042](<validaciones/VALIDACION_ST042.md>) y [US-012](<validaciones/VALIDACION_US012.md>) | `backend/README.md` y [VALIDACION_US013](<validaciones/VALIDACION_US013.md>) | Documentos [03 Calidad](<03 Calidad de código V_1_0_0.md>), [04 OWASP](<04 OWASP V_1_0_0.md>) y [05 WCAG](<05 WCAG V_1_0_0.md>) |
| BDD aprobada y evidencia | [ECL-72](https://continental-team-il84x39k.atlassian.net/browse/ECL-72) aprobada por Julio ([#63](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/63)); matriz I01–I16 | Criterios por ruta en [VALIDACION_US013](<validaciones/VALIDACION_US013.md>) | Criterios del ticket con evidencia en [ECL-65](<evidencias/ECL-65/README.md>), [ECL-66](<evidencias/ECL-66/README.md>) y [ECL-67](<evidencias/ECL-67/README.md>) |
| Sin defectos bloqueantes | Ninguno abierto; I03 parcial trazado a [ECL-82](https://continental-team-il84x39k.atlassian.net/browse/ECL-82) | Ninguno abierto | Ninguno abierto |

**Conclusión:** US-012, US-013 y los enablers cumplen el DoD **salvo el criterio de staging**, que no existe en el proyecto; se registra expresamente como excepción y se propone tratarlo en el Sprint 4. Los hallazgos no bloqueantes siguen trazados a sus tickets.

### Otros entregables y estado de gestión

- **[ECL-71](https://continental-team-il84x39k.atlassian.net/browse/ECL-71):** Frank ratificó las BDD de conductores y preferencias en [PR #64](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/64), integrado el **26/10/2026**. Estado actual de Jira: **«Finalizada»**.
- **Ítem 6 — estructura y `.gitignore`:** trabajo de Julio en [PR #66](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/66).
- **Ítem 7 — versionamiento de requisitos:** trabajo de Frank en [PR #68](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/68).
- **[ECL-70](https://continental-team-il84x39k.atlassian.net/browse/ECL-70) — Retrospectiva:** documento de Frank en [PR #81](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/81), [Retrospectiva del Sprint 3](<02 Retrospectiva del Sprint V_1_0_0.md>). Estado actual de Jira: **«Finalizada»**.

## Demostración del trabajo completado

Demostración a los stakeholders de las funcionalidades implementadas.

### Guion previsto para la Review del 30/10/2026

La demostración **aún no se presenta como ejecutada ante los stakeholders**. Se propone este orden con las cuentas y roles preparados mediante `seed_demo.py`, sin revelar contraseñas:

| Orden | Rol / área | Acciones previstas y criterio visible |
|---|---|---|
| 1 | **Administrador — US-013** | Iniciar sesión; restablecer la contraseña de un usuario mediante el flujo autorizado; comprobar el cambio obligatorio y la gestión de sesiones sin exponer credenciales |
| 2 | **Conductor — US-012** | Abrir itinerario → reportar incidencia en línea → quedar sin conexión → recargar → registrar en cola → reconectar y comprobar **una única sincronización** |
| 3 | **Operador — US-012** | Abrir la vista de incidencias pendientes y localizar la incidencia enviada por el conductor; verificar la presentación y la autorización por rol |
| 4 | **Calidad y seguridad** | Mostrar el **Quality Gate PASSED** y métricas de SonarCloud; resumir el reporte OWASP 2025 y declarar el hallazgo S8703 pendiente |
| 5 | **Accesibilidad** | Mostrar una interacción por teclado (orden del foco y control accesible); mencionar la reserva de WCAG 2.2.1 |

**Entorno previsto:** laptop de Julio conectada por **HDMI**; aplicación en `http://127.0.0.1:5173`; [guía local ECL-68](<guias/GUIA_DEMO_LABORATORIO.md>) con [video de respaldo](https://drive.google.com/file/d/1sx-a97hDRjneDUoZ5CvitxmUftrTEZIK/view?usp=sharing). Se confirmó la ejecución en la laptop de desarrollo Windows 11 (commit `85dd92b`); **no** se ha validado una computadora del laboratorio sin permisos administrativos.

**Ensayo previo:** 28/10/2026, grabado y enlazado en la guía, según la acción A6 de la [Retrospectiva](<02 Retrospectiva del Sprint V_1_0_0.md>). Es un **ensayo**, no evidencia de la Review frente al docente. Las pruebas offline Chrome y Firefox referidas arriba acreditan la campaña técnica, no una demostración pública.

### Registro a completar después de la Review

**Lugar, fecha y ejecución frente al docente:** se documentarán con los hechos de la Review del 30/10/2026, mediante un PR de actualización pequeño. Solo entonces se indicará quién asistió realmente, qué flujos se mostraron y qué observaciones se recibieron, vinculando cada acción nueva con su ticket Jira.

Asistentes y feedback del docente: se registrarán después de la Review del 30/10/2026.

## Pendientes

| Ticket / seguimiento | Motivo y próximo paso |
|---|---|
| [ECL-68 / EN-012](https://continental-team-il84x39k.atlassian.net/browse/ECL-68), 3 SP | La demo y scripts están en [PR #74](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/74) y [PR #76](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/76); la ejecución está **validada solo en la laptop Windows 11** (commit `85dd92b`). Falta validación en una PC real del laboratorio sin administrador. Riesgo: `scripts/lab/diagnostico-consola.cs` se compila con `Add-Type`, posiblemente restringido en laboratorio. Pasa al Sprint 4; Jira figura **«En curso»**. |
| [ECL-82](https://continental-team-il84x39k.atlassian.net/browse/ECL-82) | Cerrar la validación de jornada I03 cuando esté disponible el modelo de rutas del Sprint 4. |
| [ECL-83](https://continental-team-il84x39k.atlassian.net/browse/ECL-83) | Resolver WCAG 2.2.1, aviso de sesión de 60 minutos. |
| [ECL-84](https://continental-team-il84x39k.atlassian.net/browse/ECL-84) | Cerrar hallazgo S8703 (SSRF), cabeceras HTTP de seguridad y respuestas 422 saneadas en pedidos y vehículos. |
| [ECL-85](https://continental-team-il84x39k.atlassian.net/browse/ECL-85) | Fijar GitHub Actions por SHA, activar Dependabot y reforzar Code Owners. |
| [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86) | Elaborar modelo de amenazas y alertas de seguridad. |
| [ECL-87](https://continental-team-il84x39k.atlassian.net/browse/ECL-87) | Revisar code smells del frontend detectados en SonarCloud. |
| [ECL-79](https://continental-team-il84x39k.atlassian.net/browse/ECL-79), [ECL-80](https://continental-team-il84x39k.atlassian.net/browse/ECL-80), [ECL-81](https://continental-team-il84x39k.atlassian.net/browse/ECL-81) | Dar seguimiento a la ratificación documental de las BDD asociadas a ECL-71. |

**Retrospectiva, acciones A9–A12:** seguimiento [ECL-88](https://continental-team-il84x39k.atlassian.net/browse/ECL-88) (Code Owners y rama actualizada), [ECL-89](https://continental-team-il84x39k.atlassian.net/browse/ECL-89) (comentarios de revisión), [ECL-90](https://continental-team-il84x39k.atlassian.net/browse/ECL-90) (entorno local para cinco integrantes) y [ECL-91](https://continental-team-il84x39k.atlassian.net/browse/ECL-91) (control de alcance de PR), según [02 Retrospectiva del Sprint V_1_0_0.md](<02 Retrospectiva del Sprint V_1_0_0.md>).

**Después de la Review:** registrar asistentes reales y feedback docente mediante PR pequeño; no cerrar el Sprint 3 en Jira sin acuerdo expreso del equipo, porque el cierre es irreversible. Tras la evaluación y el merge final, acordar la creación/protección de la rama `sprint-3` y la limpieza de ramas de trabajo (acuerdo R4). Estas acciones **no se ejecutan en este PR**.

[Volver al índice del Sprint 3](README.md) · [← Volver al README principal](../../../README.md)
