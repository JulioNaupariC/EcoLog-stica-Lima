# Informe de estado del proyecto

**Nombre del Proyecto:** EcoLogística Lima, para DistriRápido S.A.C.

**Líder del Proyecto:** Julio Armando Naupari Camarena

**Versión:** 1.0.0

**Fecha de corte:** noche del 01/10/2026 (America/Lima; hora exacta no registrada)

**Periodo del informe:** Sprint 1, desde el 11/09/2026 hasta el corte; la línea base fijaba el fin el 25/09/2026.

**Estado de preparación:** informe previo a la inspección G5117 del 02/10/2026, 15:40–16:00; demostración y aceptación pendientes de realizar.

## Estado del proyecto

| Variable de control | Descripción del estado al corte |
|---|---|
| **Alcance** | Jira Sprint 1 (ID 4, board 3): seis elementos principales, 28 SP comprometidos. ECL-7 (3), ECL-8 (5), ECL-10 (5), ECL-20 (5) y ECL-24 (5) figuran **Finalizada**; ECL-19 (5) figura **Tareas por hacer**. Avance por estado de padres: **23/28 SP = 82,14 %**, cinco de seis elementos. ECL-27 a ECL-45: 18 de 19 subtareas **Finalizada** (94,74 %); ECL-29 sigue **In Review / QA**. Son métricas distintas; no se suman SP de padres y subtareas. No equivalen a velocidad final ni a aceptación del stakeholder. |
| **Cronograma** | La planificación versionada y la consulta Jira conservan fin **25/09/2026 09:00**. Al corte del 01/10 hay desviación respecto de esa línea base y ECL-19 sigue abierto. Se propuso terminar el **02/10/2026 16:00**, pero falta evidencia de que el cambio se haya aplicado y aprobado en Jira. No se declara cumplimiento en plazo. |
| **Costos** | Línea base empresarial: techo de desarrollo **S/ 500 000 (≈ USD 135 000)**; estimación detallada **USD 127 680** (USD 114 000 de subtotal más USD 13 680 de contingencia). **S/ 120 000 anuales** de mantenimiento y soporte posteriores son una línea separada. El gasto académico real y la ejecución financiera al corte **no están registrados**; faltan comprobantes, horas valorizadas y reporte de consumo. Por ello no pueden calcularse consumo real ni variación frente al presupuesto. |
| **Calidad** | Según los logs revisados por el auditor remoto para el PR #20: CI #13 (`36947681206`) y CodeQL #4 (`36947681199`) terminaron en `success`; 244 pruebas frontend, 281 unitarias backend con cobertura **89,29 %**, y 98 de integración backend. Estas cifras corresponden a esa ejecución del PR, no al estado integrado de `main`. La auditoría remota quedó `READY FOR HUMAN REVIEW`, B0/H0/M0/L0/N2. No hay recuento consolidado de defectos del Sprint: **No registrado**. CI no construye ni arranca Compose; falta reproducción del README por un segundo integrante, aprobación humana y merge. |

El alcance implementado del Sprint cubre acceso/roles, registro y listado de vehículos, registro de pedidos y controles de CI/CodeQL conforme a las subtareas acreditadas. La API de vehículos tiene operaciones adicionales, pero ECL-41 solo añadió formulario y listado en la interfaz; no se acredita edición, desactivación, filtros ni paginación frontend. El motor de optimización, mapas y dashboard pertenecen a incrementos futuros y no se declaran completos. ECL-29 aporta implementación y validación local por Antony en el PR #20 abierto (`8881b07f68ffe0e6ff095697d81fba7f1f6efd33`), todavía sin integración a `main`. ECL-35 sí quedó integrado mediante PR #19, merge `f0356d69fbecd752313ae6c2b8cf8dfb52561fde`; se establecieron CodeQL y protección de `main`, y se conserva la rama de evidencia según coordinación.

## Riesgos

| Riesgo | Responsable según registro de riesgos | Mitigación y situación al corte |
|---|---|---|
| RSK-05: desviación del cronograma o cambio tardío de alcance | Julio Armando Naupari Camarena | Mantener el 25/09 como línea base; confirmar en Jira cualquier ajuste y dejar ECL-19/ECL-29 visibles hasta cumplir revisión e integración. |
| RSK-06: seguridad o exposición de datos | Antony Munive Ríos | Mantener RBAC, pruebas y CodeQL. El éxito de CI/CodeQL del PR #20 no sustituye aprobación humana ni revisión del incremento integrado. |
| RSK-09: evidencia de prueba insuficiente para aceptación | Frank Roy Yupanqui Acevedo | Preparar cuentas y datos sintéticos de demostración, conservar resultados y registrar feedback real tras la inspección. Las métricas de CI no prueban las metas del optimizador. |
| RSK-10: dependencia de conocimiento para reproducir el entorno | Julio Armando Naupari Camarena | Un segundo integrante debe repetir el arranque documentado y registrar comandos, resultado y obstáculos antes de dar por cerrado ECL-29. |

## Próximos avances

1. Reproducir el README de ECL-29 con un segundo integrante y conservar evidencia; completar revisión humana del PR #20 y decidir su integración sin anticipar el resultado.
2. Confirmar con coordinación si se aplicará en Jira el fin propuesto del 02/10/2026 16:00, registrando aprobación y diferencia frente al 25/09.
3. Preparar la demostración de 20 minutos para G5117 con operaciones de prueba autorizadas y datos sintéticos en un entorno de prueba. No afectar datos reales ni ejecutar asignación u optimización fuera del alcance implementado; registrar asistencia, resultado y feedback después, sin anticipar aceptación.
4. Solicitar un registro de gasto académico real y de defectos del Sprint si se requiere medir costo y calidad más allá de las ejecuciones citadas.

## Notas y coherencia documental

- El [README principal](../../../README.md) y [Artefactos Jira V_1_0_0](../../02%20Planificación/02%20Artefactos%20Jira%20V_1_0_0.md) describen **18 subtareas** de la planificación inicial. La consulta operativa verificada para este corte comprende **19** (ECL-27 a ECL-45, incluida ECL-45). Cambio posterior mínimo propuesto: nota fechada en README y adenda de estado en Artefactos Jira **V_1_0_1**, preservando la fotografía original del compromiso.
- El README y Artefactos Jira muestran Sprint activo con fin 25/09 como línea base; la propuesta de 02/10 no está confirmada aplicada. Cambio posterior mínimo propuesto: incorporar fecha real de cierre y decisión de replanificación solo cuando exista evidencia Jira; **V_1_0_1** para la adenda de Artefactos Jira. No alterar retroactivamente el [acta V_1_1_0](../../01%20Inicio/02.%20Acta%20de%20constitución%20V_1_1_0.md) ni sus hitos.
- El [modelo C4](../../01%20Inicio/12.%20Modelo%20C4%20V_1_0_0.md) y los [requisitos funcionales](https://github.com/JulioNaupariC/EcoLog-stica-Lima/blob/sprint-1/docs/01%20Inicio/06.%20Requisitos%20funcionales%20V_1_0_0.md) describen el sistema objetivo. Un ajuste posterior de documentación de implementación podría marcar explícitamente qué contenedores y funciones ya están integrados, sin rebajar requisitos para acomodarlos al avance. Los README de backend/frontend son las fuentes actuales para límites de la implementación.
- La plantilla Markdown auténtica `Informe de Estado del Proyecto.md` del ZIP se usó para esta estructura; el HTML de la consigna duplica por error la plantilla de Review bajo el nombre de informe.

## Fuentes y evidencia

- [Acta de constitución V_1_1_0](../../01%20Inicio/02.%20Acta%20de%20constitución%20V_1_1_0.md), [planificación ágil](../../02%20Planificación/01%20Transformando%20a%20ágil%20V_1_0_0.md), [Artefactos Jira](../../02%20Planificación/02%20Artefactos%20Jira%20V_1_0_0.md), [presupuesto](../../02%20Planificación/04%20Presupuesto%20del%20proyecto%20V_1_0_0.md) y [riesgos](../../02%20Planificación/03%20Registro%20de%20riesgos%20V_1_0_0.md).
- [Requisitos no funcionales V_1_1_0](https://github.com/JulioNaupariC/EcoLog-stica-Lima/blob/sprint-1/docs/01%20Inicio/07.%20Requisitos%20no%20funcionales%20V_1_1_0.md), [README backend](../../../backend/README.md) y [README frontend](../../../frontend/README.md).
- Datos de estado, inspección y logs suministrados por el coordinador para el corte del 01/10/2026; trazabilidad: [PR #20](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/20), [PR #19](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/19), Jira ECL-7, ECL-8, ECL-10, ECL-19, ECL-20, ECL-24 y ECL-27 a ECL-45. La inspección y la aceptación aún carecen de acta.

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 01/10/2026 | Informe previo a inspección con estado Jira, integración GitHub y datos pendientes separados. |

[Volver al índice del Sprint 1](README.md) · [← Volver al README principal](../../../README.md)

## Actualización posterior al corte — 02/10/2026

El contenido V_1_0_0 anterior conserva el corte histórico del 01/10. La [adenda operativa V_1_0_1](<../../02 Planificación/02 Artefactos Jira V_1_0_1.md>) registra la reprogramación ya aplicada en Jira, los merges de PR #20 y #21, la validación independiente de Giancarlo y el nuevo estado de padres/subtareas. Los pendientes sobre aprobación e integración de esos PR corresponden al corte anterior y están superados; demo, feedback, retrospectiva y aceptación siguen sin evidencia de realización.
