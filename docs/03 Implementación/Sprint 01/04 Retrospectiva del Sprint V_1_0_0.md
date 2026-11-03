# Retrospectiva del Sprint

**Nombre del Proyecto:** EcoLogística Lima, para DistriRápido S.A.C.

**Líder del Proyecto:** Julio Armando Naupari Camarena

**Versión:** 1.0.0

**Fecha de corte:** noche del 01/10/2026 (America/Lima; hora exacta no registrada)

**Estado de preparación:** análisis previo basado en evidencia; **reunión retrospectiva y validación del equipo pendientes de realizar**. Ninguna acción o persona propuesta equivale a un acuerdo aceptado.

## ¿Qué aprendimos?

- Un estado **Finalizada** en Jira, una implementación revisada en una rama y una aceptación del stakeholder son evidencias distintas. ECL-19 sigue **Tareas por hacer** aunque 18/19 subtareas del Sprint figuren **Finalizada** y ECL-29 tenga validación local en PR #20.
- La integración navegador/API depende de configuración de origen, cookie y credenciales. El impedimento CORS se resolvió mediante ECL-45; la falta inicial de `.env` raíz para validar Docker fue superada localmente, pero la reproducción independiente aún falta.
- La cobertura de 89,29 % y los resultados de CI/CodeQL se atribuyen a la ejecución del PR #20. Ese pipeline no construye ni arranca Compose; sus resultados no prueban reproducibilidad del entorno ni metas del optimizador.
- La diferencia entre las 18 subtareas de la planificación inicial y las 19 del corte, junto con el fin 25/09 aún visible en Jira, muestra la necesidad de fechar las actualizaciones operativas sin modificar la línea base histórica.

## ¿Qué estamos haciendo bien?

- Se mantuvo trazabilidad entre requisitos, historias, enablers y subtareas; el corte permite distinguir **23/28 SP** de padres finalizados de **18/19 subtareas** finalizadas sin duplicar estimaciones.
- ECL-35 quedó integrado por PR #19 con CodeQL y protección de `main`; la rama de evidencia se conserva según coordinación.
- El PR #20 dispone de validación local de Antony, CI #13 y CodeQL #4 exitosos, y auditoría remota `READY FOR HUMAN REVIEW` (B0/H0/M0/L0/N2). Son insumos concretos para revisión humana.
- Los README de backend y frontend documentan configuración de CORS, roles y límites de la interfaz de vehículos, lo que ayuda a preparar una demostración fiel.

## ¿Qué podemos hacer mejor?

### Personas

La reproducción del README de ECL-29 depende todavía de un segundo integrante. El equipo debe comprobar que otra persona pueda levantar el entorno y explicar los errores sin depender del autor de la implementación. No consta reunión del equipo que confirme esta apreciación: **pendiente de validar**.

### Relaciones

La propuesta de mover el fin del Sprint al 02/10/2026 16:00 no tiene confirmación de aplicación en Jira. Conviene acordar quién registra y comunica las decisiones de calendario y quién documenta feedback de la inspección, sin atribuir acuerdos que aún no existen. **Pendiente de validar con el equipo**.

### Procesos

La línea base del 25/09 y los estados operativos posteriores deben leerse en capas fechadas. El PR #20 aún requiere aprobación humana y merge, y el DoD de reproducibilidad necesita evidencia independiente. La Review del 02/10 debe producir un registro de asistencia, observaciones y decisión, si se realiza. **Pendiente de validar con el equipo**.

### Herramientas

La planificación inicial y el README describen 18 subtareas; la consulta Jira al corte incluye 19, incluida ECL-45. `alembic check` tiene una limitación con objetos espaciales de PostGIS; CI no ejercita Compose. Se propone un control de sincronización Jira/GitHub, una verificación alternativa de migraciones y una auditoría separada del arranque. **Pendiente de validar con el equipo**.

### Acciones a realizar

Las siguientes son **propuestas para la retrospectiva**, no asignaciones ni compromisos aceptados. Las fechas propuestas usan America/Lima y requieren confirmación del equipo. Si no se realiza la reunión, registrar **Pendiente de realizar** y reprogramar con evidencia.

| Problema | Acción propuesta | Responsable propuesto | Fecha propuesta | Criterio verificable de éxito |
|---|---|---|---|---|
| Reproducibilidad no comprobada por otra persona | Validación cruzada del README de ECL-29 en un entorno limpio, anotando comandos y resultados sin secretos. | José Samuel Delgadillo Pantoja | 02/10/2026 antes de la inspección | Registro fechado de arranque o de fallos reproducibles por segundo integrante, adjunto a la revisión de PR #20. |
| Demo sin cuentas y datos confirmados | Preparar cuentas por rol y operaciones de prueba autorizadas con vehículos y pedidos sintéticos en un entorno de prueba; comprobar acceso, rechazos y limpieza posterior. No afectar datos reales ni ejecutar asignación u optimización fuera del alcance implementado. | Giancarlo Marcio Soto Escobar | 02/10/2026 antes de las 15:40 | Lista de comprobación con roles, operaciones de prueba y resultados; ninguna credencial en repositorio ni capturas. |
| Desfase entre planificación, Jira y README | Conciliar ECL-27 a ECL-45 y el estado de ECL-19/ECL-29; registrar decisión sobre fecha fin manteniendo 25/09 como línea base. | Julio Armando Naupari Camarena | 02/10/2026 | Consulta Jira fechada, decisión de calendario trazable y propuesta de adenda V_1_0_1 para Artefactos Jira; README ajustado solo tras confirmación. |
| Validaciones concentradas en un solo flujo | Realizar auditorías independientes: revisión humana de PR #20 y prueba de Compose fuera del CI actual; anotar también la limitación de `alembic check` y verificación alternativa. | Antony Munive Ríos para facilitar evidencia; revisor independiente por confirmar | 03/10/2026 | Aprobación humana registrada y reporte separado de arranque/Compose y migraciones; merge solo cuando corresponda. |
| Feedback de stakeholder aún inexistente | Tras la inspección G5117, registrar asistentes efectivos, observaciones, decisiones y acciones con fuente y fecha. | Frank Roy Yupanqui Acevedo | 02/10/2026 después de las 16:00 | Minuta o acta de Review con feedback real, o constancia de que la sesión no se realizó. |

## Fuentes y evidencia

- [Acta de constitución](../../01%20Inicio/02.%20Acta%20de%20constitución%20V_1_1_0.md), [Artefactos Jira](../../02%20Planificación/02%20Artefactos%20Jira%20V_1_0_0.md), [registro de riesgos](../../02%20Planificación/03%20Registro%20de%20riesgos%20V_1_0_0.md), [requisitos no funcionales](https://github.com/JulioNaupariC/EcoLog-stica-Lima/blob/sprint-1/docs/01%20Inicio/07.%20Requisitos%20no%20funcionales%20V_1_1_0.md), [README backend](../../../backend/README.md) y [README frontend](../../../frontend/README.md).
- Estados y resultados de auditoría comunicados por el coordinador al corte del 01/10/2026; [PR #19](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/19) integrado y [PR #20](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/20) abierto. Falta acta de retrospectiva y confirmación de responsables, fechas y acuerdos.
- Se conserva la estructura de la plantilla Markdown `Retrospectiva del Sprint.md` del ZIP: aprendizajes, aciertos, Personas, Relaciones, Procesos, Herramientas y acciones.

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 01/10/2026 | Análisis previo y acciones propuestas, pendientes de validación por el equipo. |

[Volver al índice del Sprint 1](README.md) · [← Volver al README principal](../../../README.md)

## Actualización posterior al corte — 02/10/2026

El contenido V_1_0_0 anterior conserva el corte histórico del 01/10. La [adenda operativa V_1_0_1](<../../02 Planificación/02 Artefactos Jira V_1_0_1.md>) registra la reprogramación ya aplicada en Jira, los merges de PR #20 y #21, la validación independiente de Giancarlo y el nuevo estado de padres/subtareas. Los pendientes sobre aprobación e integración de esos PR corresponden al corte anterior y están superados; demo, feedback, retrospectiva y aceptación siguen sin evidencia de realización.
