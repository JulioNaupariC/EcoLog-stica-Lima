# Retrospectiva del Sprint — Sprint 2

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

**Estado:** análisis de evidencias y propuestas para la retrospectiva.
No se dispone de acta, asistentes ni acuerdos adoptados del Sprint 2.
Las observaciones se basan en los informes; no se atribuyen opiniones individuales.

## ¿Qué aprendimos?

El trabajo paralelo exige dependencias claras: modelo y reglas preceden a API,
API precede a formulario y pruebas integradas, y plan de carga precede a métricas
y consolidación. La colisión de migraciones de conductores/reportes mostró que
cada rama debe comprobar su revisión previa antes de integrarse.

Las pruebas verdes de una API no acreditan un flujo completo de producto:
ST-028 comprobó persistencia y aislamiento, pero P8 sigue ausente del formulario.
De igual forma, una mediana favorable no acredita carga sostenida ni SLA mensual,
y reducir valores de una consulta no demuestra disminuir el payload del dashboard.

## ¿Qué estamos haciendo bien?

Se separan frontend, servicios, repositorios y esquemas. La autorización se
comprueba en backend, además de ocultar enlaces. Las pruebas usan bases aisladas,
cuentas sintéticas y casos negativos con comprobación de ausencia de cambios.

Los informes conservan versiones, planes, capturas, escenarios y límites.
Las preferencias no alteran silenciosamente un pedido y los ejemplos móviles
se identifican como demostración. La optimización ECL-64 se aplicó al hallazgo
medido, con comparación y regresión funcional, manteniendo los índices existentes.

## ¿Qué podemos hacer mejor?

### Personas

Organizar revisión cruzada por componente para que otra persona pueda reproducir
el flujo y entender su contrato. Cada responsable debe explicar también límites
y errores, evitando que la exposición dependa de quien ejecutó las pruebas.
La colaboración de Giancarlo en entregables de otras líneas debe reflejarse
como trabajo del equipo, sin atribuir commits o pruebas a autores ficticios.

### Relaciones

Acordar con anticipación contratos, dependencias y decisiones de aceptación.
La preferencia del cliente y el dato del pedido tienen semánticas diferentes;
negocio, UX y backend necesitan ratificar la interacción de P8.
Registrar qué se acordó y quién participó ayuda a resolver diferencias entre
documentación, implementación y expectativas de compañeros.

### Procesos

Usar una rama por unidad de trabajo y revisar compatibilidad con main y
migraciones antes del merge. Incluir una lista de criterios de aceptación y
evidencia por escenario en cada PR. Al cerrar padres Jira, comprobar pendientes
del producto y dependencias, además de la entrega de las subtareas.

Programar pruebas que cubran asociación entre clientes, roles negativos, rollback,
reconexión e idempotencia. En carga, separar campañas completas e interrumpidas,
registrar condiciones del host y no promediar percentiles. Las reuniones deben
producir acta con fecha, feedback, decisiones y acciones aceptadas.

### Herramientas

Mantener enlaces entre Jira, commits, PR e informes con nomenclatura ECL.
Conservar artefactos de CI y capturas por navegador sin secretos.
Asegurar un único head Alembic y comparar revisiones antes de aplicar migraciones.
Revisar dependencias y el aviso histórico registrado en ST-032 con evidencia actual.

Los sondeos de disponibilidad deben cubrir el periodo comprometido, y las
consultas/bytes del dashboard deben medirse cuando su endpoint exista.
Las simulaciones siguen siendo útiles, identificadas junto con sus límites.

### Acciones a realizar

Responsables y fechas siguientes son propuestas, pendientes de aceptación.
La fecha 23/10/2026 corresponde al cierre planificado comunicado; no es una
promesa registrada de cada integrante.

| Acción | Responsable propuesto | Plazo propuesto | Criterio verificable |
|---|---|---|---|
| Ratificar ST-025 y decidir propuesta en pedido | Frank y Julio, con Antony y Giancarlo | Antes del cierre de US-005 | Contrato aprobado y decisión sobre P8 registrada |
| Implementar y retestar propuesta explícita | José/Giancarlo con revisión de Antony | Plan acordado antes del 23/10/2026 | Contexto visible, copia editable sin cambio del cliente ni ventanas; prueba E2E |
| Revisar dependencias de asignaciones y planificador | Antony y José | Plan acordado antes del 23/10/2026 | Asignación válida consultada por su dueño; reporte offline sincronizado una vez |
| Validar migraciones por revisión cruzada | Antony y revisor de otra línea | Antes de cada merge con esquema | Único head, upgrade/rollback y pruebas en base aislada |
| Repetir campaña con concurrencia acreditable | José con Julio | Plan antes del 23/10/2026 | Serie de solicitudes en vuelo y huecos explicitados, población válida conciliada |
| Definir periodo de disponibilidad y responsables de sondeos | Julio y Antony | Antes de declarar SLA | Cobertura 05:00–22:00, fórmula, huecos y mantenimiento registrados |
| Medir dashboard y rutas al existir su contrato | Giancarlo y Antony | Antes de aceptar RNF-012 | JSON sin mapa ≤250,000 bytes y planes reales documentados |
| Revisar accesibilidad y dependencias actuales | José y Giancarlo | Plan antes del cierre de EN-004 | Checklist de teclado/foco/contraste y resultados de análisis con fecha |
| Registrar Review/retrospectiva y actualizar seguimiento | Julio y Frank | Después de la exposición o sesión real | Fecha, asistentes, feedback y responsables aceptados en acta |

## Fuentes del análisis

- [Estado del Sprint 2](<01 Informe de estado del proyecto V_1_0_0.md>) y
  [registro de impedimentos](<02 Registro de Impedimentos V_1_0_0.md>).
- [Preferencias y brechas](../../backend/VALIDACION_ST028.md).
- [Offline y límites](../../frontend/VALIDACION_ST032.md).
- [Resultados de capacidad/SLA](../../backend/INFORME_ST036.md).
- [Decisiones de optimización](../../backend/VALIDACION_ST038.md).

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 01/10/2026 | Entregable del Sprint 1; contenido anterior conservado en el historial Git. |
| 1.1.0 | 09/10/2026 | Sustitución del contenido por el entregable del Sprint 2, con evidencias y pendientes al corte. |

El nombre V_1_0_0 del archivo se conserva por exigencia de la consigna.
La versión del contenido se incrementa a 1.1.0 para identificar esta actualización.

[← Volver al README principal](../../README.md)
