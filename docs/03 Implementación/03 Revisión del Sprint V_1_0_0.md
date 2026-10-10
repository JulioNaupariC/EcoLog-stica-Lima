# Revisión del Sprint — Sprint 2

**Nombre del Proyecto:** EcoLogística Lima — optimizador de rutas sostenibles para DistriRápido S.A.C.

**Líder del Proyecto:** Julio Armando Naupari Camarena.

**Asignatura:** Taller de Proyectos 2 — Ingeniería de Sistemas e Informática.

**Sprint:** Sprint 2 — Gestión operativa y experiencia del conductor.

**Periodo planificado:** 08/10/2026–23/10/2026, según el tablero compartido.

**Fecha de corte:** 09/10/2026, America/Lima.

**Versión del contenido:** 1.1.0.

**Fuente del corte técnico:** repositorio local en `df55c72` y sus informes de validación.

**Estado Jira aportado:** cinco padres y 19 subtareas finalizados; 27/27 SP de padres.
Fuente: captura del tablero compartida por Giancarlo; sprint visible como activo.

**Estado de la ceremonia:** preparada para la exposición; sin acta aportada.
Fecha, asistentes efectivos, observaciones y aceptación pendientes de registrar.

## Historias de Usuario completadas en este Sprint

La captura aportada registra los cinco padres y las 19 subtareas como Finalizada
(27/27 SP de padres y 19/19 subtareas). El incremento técnico se muestra por padre
y se explica junto con los criterios todavía no acreditados en los informes.

| Historia/enabler | Trabajo demostrable | Evidencia | Elementos pendientes de aceptación |
|---|---|---|---|
| ECL-9 / US-003 | Alta, consulta, edición y disponibilidad de conductores; RBAC, DNI/licencia y errores | ST-022, ST-023 y ST-024 | Confirmar aceptación del equipo; elegibilidad no certifica optimización |
| ECL-11 / US-005 | Consultar/guardar preferencias por UUID, limpiar un campo y rechazar inválidos | ST-026, ST-027 y ST-028 | P8 en formulario de pedido y aprobación BDD |
| ECL-22 / EN-004 | Diseño móvil, siguiente parada, alertas, estado sin asignación y almacenamiento/cola | ST-029–032 | Planificador, rutas reales y validación accesible completa |
| ECL-23 / EN-005 | Métricas protegidas, salud, sondeos y campaña documentada | ST-033–036 | Concurrencia sostenida, periodo de SLA y cobertura dashboard |
| ECL-25 / EN-007 | EXPLAIN y consulta mínima de existencia de cliente | ST-037–038 | Payload real de dashboard y planes de rutas |

La aprobación de código, la ejecución de pruebas y la aceptación del stakeholder
son registros distintos. El cierre del 100% mostrado es operativo en Jira; la
captura no acredita feedback ni aceptación en una reunión de Review. El sprint
aparece activo con la acción Completar sprint.

## Demostración del trabajo completado

### Preparación

Usar ambiente de pruebas con cuentas por rol y datos sintéticos. Comprobar login,
migraciones y endpoints antes de la exposición. No mostrar contraseñas, cookies
ni variables privadas. La siguiente agenda es un guion propuesto, no una demo
ya realizada ante stakeholders.

| Tiempo propuesto | Demostración | Resultado observable / límite |
|---|---|---|
| 0–2 min | Objetivo del Sprint y cinco líneas de trabajo | Incrementos y pendientes del informe de estado |
| 2–5 min | Administrador/Operador registra y edita conductor | Persistencia y errores claros; datos inválidos rechazados |
| 5–8 min | Preferencias de clientes A y B | Actualizar A conserva B; limpieza con null y rechazo de exceso de longitud |
| 8–10 min | Crear pedido para el cliente | Mostrar referencia manual independiente; explicar brecha de propuesta P8 |
| 10–13 min | Experiencia móvil a 360 px | Siguiente parada, alertas y detalle del ejemplo rotulado; estado real sin asignación |
| 13–16 min | Consulta previa y cola offline | Mostrar snapshot/outbox en pruebas; distinguir transporte simulado de integración real pendiente |
| 16–18 min | Salud de API/BD y métricas con sesión autorizada | Latencias, solicitudes y 5xx; /health no equivale a disponibilidad histórica |
| 18–20 min | Campaña y comparación SQL | P95 agregado 1.497054 s; 5xx 0% en población válida; SELECT de cinco campos reducido a EXISTS |
| 20–22 min | Preguntas y feedback | Registrar observaciones reales, decisiones y responsables acordados |

### Evidencia disponible para apoyar la exposición

- [Conductores: capturas y validación](../../frontend/VALIDACION_ST023.md).
- [Preferencias: matriz](../../backend/VALIDACION_ST028.md) y
  [capturas Chrome/Firefox](../../frontend/evidencias/ECL-54/README.md).
- [Diseño de referencia](../../frontend/VALIDACION_ST030.md).
- [Interfaz móvil](../../frontend/VALIDACION_ST030.md) y
  [offline/sincronización](../../frontend/VALIDACION_ST032.md).
- [Métricas API/BD](../../backend/VALIDACION_ST034.md).
- [Capacidad y SLA](../../backend/INFORME_ST036.md).
- [Comparación antes/después](../../backend/VALIDACION_ST038.md).

### Registro de la sesión

Al corte no hay registro de fecha de Sprint Review 2, asistentes, demostración
a stakeholders, feedback ni decisión de aceptación. Julio y Frank podrán
completar esa evidencia después de la exposición. Las capturas de pruebas
locales respaldan funcionalidades; no sustituyen asistencia o aceptación real.

## Pendientes

- Resolver y retestar D-01/P8; ratificar ST-025.
- Conectar planificador y comprobar reportes offline con asignaciones reales.
- Acreditar auditoría de accesibilidad con el alcance correspondiente.
- Repetir condiciones de concurrencia y ampliar sondeos para SLA 05:00–22:00.
- Obtener payload de dashboard sin mapa y planes de rutas antes de cerrar RNF-012.
- Adjuntar feedback y actualizar decisiones del backlog tras la Review.

Consultar el [registro de impedimentos](<02 Registro de Impedimentos V_1_0_0.md>)
para prioridad, seguimiento propuesto y evidencia de cada diferencia.

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 01/10/2026 | Entregable del Sprint 1; contenido anterior conservado en el historial Git. |
| 1.1.0 | 09/10/2026 | Sustitución del contenido por el entregable del Sprint 2, con evidencias y pendientes al corte. |

El nombre V_1_0_0 del archivo se conserva por exigencia de la consigna.
La versión del contenido se incrementa a 1.1.0 para identificar esta actualización.

[← Volver al README principal](../../README.md)
