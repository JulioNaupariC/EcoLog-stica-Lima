# Registro de impedimentos

**Nombre del Proyecto:** EcoLogística Lima, para DistriRápido S.A.C.

**Líder del Proyecto:** Julio Armando Naupari Camarena

**Versión:** 1.0.0

**Fecha de corte:** noche del 01/10/2026 (America/Lima; hora exacta no registrada)

**Estado de preparación:** registro previo a inspección; fechas históricas y responsables sin evidencia se mantienen explícitamente pendientes.

La **fecha de registro** de estas filas es la incorporación al presente documento; no representa la fecha en que surgió el impedimento. La fecha de detección se consigna en comentarios cuando consta. Las fechas objetivo nuevas son propuestas de seguimiento, no compromisos aceptados.

| Impedimento # | Fecha de Registro | Descripción del Impedimento así como el Impacto en el Proyecto | Prioridad | Reportado por | Fecha tope de Resolución | Estado | Fecha de Resolución | Resolución/Comentarios |
|---|---|---|---|---|---|---|---|---|
| IMP-01 | 01/10/2026 | La política CORS impedía integrar desde el navegador las solicitudes con cookie al API en los orígenes documentados; afectaba la demostración de login y pedidos. | Alta | No registrado; falta atribución del reporte inicial. | No registrado; no consta plazo histórico. | Resuelto | No registrado; falta fecha de cierre en Jira. | Resuelto mediante [ECL-45](https://continental-team-il84x39k.atlassian.net/browse/ECL-45), que figura **Finalizada** en el corte. El [README backend](../../../backend/README.md#integración-navegadorapi--ecl-45) y el [README frontend](../../../frontend/README.md#configuración-de-entorno) documentan la configuración de integración. Fecha de detección: **No registrado**; falta historial del ticket. |
| IMP-02 | 01/10/2026 | Al inicio faltaba `.env` en la raíz para validar el arranque Docker; la validación del entorno de ECL-29 quedó interrumpida hasta disponer de configuración local. No se registran valores ni secretos. | Alta | No registrado; falta atribución del reporte inicial. | No registrado; no consta plazo histórico. | Superado en validación local; ECL-29 continúa In Review / QA. | No registrado; falta bitácora fechada de la solución local. | La falta inicial fue superada en la implementación y validación local de [ECL-29](https://continental-team-il84x39k.atlassian.net/browse/ECL-29) aportadas por Antony al [PR #20](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/20), según el coordinador. Esto no acredita Compose integrado en `main` ni cierre del ticket. Fecha de detección: **No registrado**; falta bitácora. |
| IMP-03 | 01/10/2026 | `alembic check` tiene una limitación al comparar objetos espaciales de PostGIS; puede producir una comprobación de esquema no concluyente y dificulta usar ese comando como única prueba de migraciones. | Media | No registrado; falta reporte con autor. | **02/10/2026, propuesta** para definir verificación alternativa; aceptación pendiente de confirmar. | Pendiente | Pendiente de realizar. | Conservar la limitación como conocida; contrastar migraciones y pruebas de integración contra PostGIS y documentar el resultado. El [README backend](../../../backend/README.md#postgresql-16-y-postgis) documenta el comando, pero no esta limitación. La fuente del hallazgo es el dato del coordinador sobre validación local de [ECL-29](https://continental-team-il84x39k.atlassian.net/browse/ECL-29) en el [PR #20](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/20); falta log fechado. Fecha de detección: **No registrado**. |
| IMP-04 | 01/10/2026 | Falta que un segundo integrante reproduzca el arranque siguiendo el README de ECL-29; sin esa prueba independiente no se acredita la reproducibilidad del entorno ni el DoD del enabler ECL-19. | Alta | No registrado; falta asignación formal del hallazgo. | **02/10/2026, propuesta** antes de la inspección; aceptación pendiente de confirmar. | Pendiente | Pendiente de realizar. | Solicitar evidencia del segundo integrante: comandos, entorno, resultado y errores sin secretos. [ECL-29](https://continental-team-il84x39k.atlassian.net/browse/ECL-29) está **In Review / QA** en [PR #20](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/20); [RNF-013](https://github.com/JulioNaupariC/EcoLog-stica-Lima/blob/sprint-1/docs/01%20Inicio/07.%20Requisitos%20no%20funcionales%20V_1_1_0.md) exige instalación independiente. Fecha de detección: **No registrado**; falta primer aviso fechado. |

## Fuentes y evidencia

- Estado de ECL-29 y ECL-45, validación local y pendientes comunicados por el coordinador para el corte del 01/10/2026. El [PR #20](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/20) aporta trazabilidad de ECL-29, no prueba de merge.
- [Artefactos Jira V_1_0_0](../../02%20Planificación/02%20Artefactos%20Jira%20V_1_0_0.md), [requisitos no funcionales V_1_1_0](https://github.com/JulioNaupariC/EcoLog-stica-Lima/blob/sprint-1/docs/01%20Inicio/07.%20Requisitos%20no%20funcionales%20V_1_1_0.md), [README backend](../../../backend/README.md) y [README frontend](../../../frontend/README.md).
- La consigna HTML y la plantilla Markdown `Registro de Impedimentos.md` del ZIP proporcionan los nueve campos. No se acreditaron fechas históricas de detección/resolución, autores originales ni acuerdos sobre plazos propuestos.

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 01/10/2026 | Cuatro impedimentos acreditados, con fecha de registro diferenciada de detección y resolución. |

[Volver al índice del Sprint 1](README.md) · [← Volver al README principal](../../../README.md)

## Actualización posterior al corte — 02/10/2026

El contenido V_1_0_0 anterior conserva el corte histórico del 01/10. La [adenda operativa V_1_0_1](<../../02 Planificación/02 Artefactos Jira V_1_0_1.md>) registra la reprogramación ya aplicada en Jira, los merges de PR #20 y #21, la validación independiente de Giancarlo y el nuevo estado de padres/subtareas. Los pendientes sobre aprobación e integración de esos PR corresponden al corte anterior y están superados; demo, feedback, retrospectiva y aceptación siguen sin evidencia de realización.
