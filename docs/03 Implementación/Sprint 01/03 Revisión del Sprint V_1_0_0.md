# Revisión del Sprint

**Nombre del Proyecto:** EcoLogística Lima, para DistriRápido S.A.C.

**Líder del Proyecto:** Julio Armando Naupari Camarena

**Versión:** 1.0.0

**Fecha de corte:** noche del 01/10/2026 (America/Lima; hora exacta no registrada)

**Estado de preparación:** guion previo a la inspección G5117 del 02/10/2026, 15:40–16:00. **Demostración y feedback pendientes de realizar**.

El Sprint 1 (ID 4, board 3) comprometió seis elementos principales y 28 SP. Al corte, cinco figuran **Finalizada**: 23/28 SP = **82,14 %** por estado de padres; ECL-19 (5 SP) sigue **Tareas por hacer**. De ECL-27 a ECL-45 hay 18 de 19 subtareas **Finalizada** (**94,74 %**); ECL-29 permanece **In Review / QA**. Las subtareas no aportan SP adicionales al total de padres. Estas cifras no son velocidad final ni aceptación del stakeholder.

## Historias de Usuario completadas en este Sprint

| HU / Jira | Estado Jira y SP | Alcance acreditado para el guion | Límite que debe explicarse |
|---|---|---|---|
| US-001 / ECL-7: autenticación y acceso por rol | Finalizada, 3 SP | Login, sesión por cookie HttpOnly y control de acceso por rol; interfaz de acceso y estados de error según ECL-36 a ECL-38. | La UI conserva identidad solo en memoria; tras recargar solicita iniciar sesión nuevamente. La autorización real corresponde al backend. |
| US-002 / ECL-8: vehículos | Finalizada, 5 SP | API de vehículos y, por ECL-41, **formulario de registro y listado** con restricciones visuales por rol. | No afirmar que se mostró CRUD completo en la UI: ECL-41 no implementó edición, desactivación, reactivación, filtros ni paginación frontend. |
| US-004 / ECL-10: pedidos | Finalizada, 5 SP | Reglas y casos BDD, API con validaciones, y formulario de registro de pedidos según ECL-42 a ECL-44. | Registrar un pedido lo deja disponible para planificación posterior; no crea ruta ni ejecuta optimización. |

**Enablers técnicos, separados de las HU:** ECL-20 (seguridad OWASP/RBAC, 5 SP) y ECL-24 (CI/CD y puertas de calidad, 5 SP) figuran **Finalizada**. ECL-35 se integró mediante [PR #19](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/19), merge `f0356d69fbecd752313ae6c2b8cf8dfb52561fde`, con CodeQL y protección de `main`; la rama de evidencia se conserva según coordinación. ECL-19 (arquitectura reproducible, 5 SP) sigue **Tareas por hacer**: su subtarea ECL-29 está en revisión del [PR #20](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/20), head `8881b07f68ffe0e6ff095697d81fba7f1f6efd33`.

## Demostración del trabajo completado

**Demostración y feedback pendientes de realizar.** La inspección G5117 está programada para el 02/10/2026 de 15:40 a 16:00, después de este corte. No hay asistentes efectivos, capturas de la sesión, aceptación ni comentarios del stakeholder registrados.

| Minutos propuestos | Guion de 20 minutos | Evidencia que debe prepararse |
|---|---|---|
| 0–2 | Estado del Sprint, objetivo y diferencia entre Jira, código integrado y aceptación. | Tablero Jira al corte y lista de seis padres; mantener visibles ECL-19 y ECL-29. |
| 2–6 | Autenticación y roles: acceso válido, rechazo de credenciales inválidas y restricción por rol. | Cuentas de demostración de prueba con permisos conocidos; verificar que no se muestran credenciales ni datos reales. |
| 6–10 | Vehículos: alta y listado con los roles admitidos. | Datos sintéticos y validaciones del formulario; mencionar explícitamente las operaciones UI ausentes. |
| 10–14 | Pedidos: registro válido y rechazo de ventana o ubicación inválida. | Cliente y pedido sintéticos preparados, sin ejecutar asignación ni optimización. |
| 14–17 | Calidad e infraestructura: resultados de CI/CodeQL y estado del PR #20. | Logs de CI #13 (`36947681206`, success) y CodeQL #4 (`36947681199`, success) del PR #20; 244 pruebas frontend, 281 unitarias backend con cobertura 89,29 % y 98 de integración backend, **según logs revisados por auditor remoto**. CI no construye ni arranca Compose. |
| 17–20 | Pendientes y preguntas. | Lista de ECL-19/ECL-29, reproducción por segundo integrante, aprobación humana y merge; espacio para registrar feedback real. |

**Preparación y demostración en entorno de prueba:** se permiten operaciones de prueba autorizadas, como iniciar sesión y registrar o consultar vehículos y pedidos sintéticos dentro del alcance implementado. Comprobar antes de la sesión que el entorno responde, que las cuentas de demo tienen el rol previsto y que los enlaces a logs/PR funcionan. No afectar datos reales ni ejecutar asignación u optimización fuera del alcance implementado. Registrar resultados y limitaciones; no presentar esta agenda como ejecución efectiva.

## Pendientes

1. ECL-19 permanece **Tareas por hacer** y ECL-29 **In Review / QA**. La implementación y validación local de Antony y la auditoría remota `READY FOR HUMAN REVIEW` (B0/H0/M0/L0/N2) no sustituyen reproducción del README por un segundo integrante, aprobación humana ni merge. Docker/Compose no se declaran integrados en `main`.
2. Resolver o documentar la limitación de `alembic check` con objetos espaciales de PostGIS y conservar verificación alternativa.
3. Confirmar en Jira si se aplicó el fin propuesto **02/10/2026 16:00**. La planificación y la consulta actual conservan **25/09/2026**; la desviación no está cerrada.
4. Realizar la inspección y recoger asistentes, evidencia, observaciones y decisión de aceptación. **Pendiente de realizar**; falta acta o registro de feedback.
5. Continuar los módulos futuros de optimización, mapas y dashboard según backlog; su cumplimiento y las metas del MVP no se infieren de este Sprint.

## Fuentes y evidencia

- [Planificación ágil](../../02%20Planificación/01%20Transformando%20a%20ágil%20V_1_0_0.md), [Artefactos Jira](../../02%20Planificación/02%20Artefactos%20Jira%20V_1_0_0.md), [requisitos funcionales](https://github.com/JulioNaupariC/EcoLog-stica-Lima/blob/sprint-1/docs/01%20Inicio/06.%20Requisitos%20funcionales%20V_1_0_0.md), [README backend](../../../backend/README.md) y [README frontend](../../../frontend/README.md).
- Estados Jira, programación G5117, hashes y resultados CI aportados por el coordinador al corte del 01/10/2026; trazabilidad de código en [PR #19](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/19) y [PR #20](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/20). Falta evidencia de la demostración efectiva.
- La estructura de tres secciones sigue la plantilla Markdown auténtica `Revisión del Sprint.md` del ZIP de la consigna.

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 01/10/2026 | Revisión preparatoria: HU, enablers, guion y pendientes diferenciados. |

[Volver al índice del Sprint 1](README.md) · [← Volver al README principal](../../../README.md)

## Actualización posterior al corte — 02/10/2026

El contenido V_1_0_0 anterior conserva el corte histórico del 01/10. La [adenda operativa V_1_0_1](<../../02 Planificación/02 Artefactos Jira V_1_0_1.md>) registra la reprogramación ya aplicada en Jira, los merges de PR #20 y #21, la validación independiente de Giancarlo y el nuevo estado de padres/subtareas. Los pendientes sobre aprobación e integración de esos PR corresponden al corte anterior y están superados; demo, feedback, retrospectiva y aceptación siguen sin evidencia de realización.
