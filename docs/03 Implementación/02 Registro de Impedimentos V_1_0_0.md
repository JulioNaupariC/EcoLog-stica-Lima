# Registro de impedimentos — Sprint 2

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

## Criterio del registro

Los hallazgos se registran al corte documental del 09/10; esa fecha no atribuye
una fecha de detección histórica que no consta. Los responsables de seguimiento
y plazos son propuestas para confirmar en la retrospectiva. Ninguna fila vacía
ni marcador de plantilla se presenta como dato real.

| Impedimento # | Fecha de Registro | Descripción e impacto en el proyecto | Prioridad | Reportado por | Fecha tope de Resolución | Estado | Fecha de Resolución | Resolución/Comentarios |
|---|---|---|---|---|---|---|---|---|
| S2-01 | 09/10/2026, consolidación | Colisión de revisión Alembic de conductores/reportes; podía dejar varias ramas de migración incompatibles | Alta | Coordinador Giancarlo; conversación de integración | Superado al corte | Resuelto en código | Verificado al corte; fecha exacta de corrección no registrada | 0008_driver_reports depende de 0007_create_conductor. Mantener orden y pruebas; fuente ST-032 |
| S2-02 | 09/10/2026 | Formulario de pedidos no propone las preferencias guardadas; impide el flujo P8/RF-005 | Alta | Validación ECL-54; consolidada por Giancarlo | Antes del cierre 23/10/2026, propuesta | Pendiente | No resuelto al corte | D-01 reproducido en Chrome/Firefox. Julio/Frank ratifican interacción; José/Giancarlo preparan UI con contrato de Antony |
| S2-03 | 09/10/2026 | Planificador no conectado a provisionamiento de asignaciones; no hay itinerarios reales derivados de optimización | Alta | Informe ST-032 | Antes de aceptar rutas reales, plazo por acordar | Pendiente de integración | No resuelto al corte | Endpoint puede devolver lista vacía. Antony propone integración; José valida E2E. Los ejemplos se rotulan como demostración |
| S2-04 | 09/10/2026 | Dashboard y consultas de rutas ausentes; impide medir payload agregado y cerrar RNF-012 | Alta | Informes ST-037/ST-038 | Antes de cerrar ECL-25, propuesta 23/10/2026 para revisión | Pendiente | No resuelto al corte | Dependencias ECL-15, ECL-12 y ECL-13. No sustituir dashboard por bundle o pedidos; Giancarlo/Antony coordinan medición |
| S2-05 | 09/10/2026 | Campaña no acredita 100 POST sostenidos ni cobertura mensual del horario operativo; SLA no medido | Alta | Consolidación ST-036 | Plan de repetición antes del 23/10/2026, propuesta; medición mensual requiere periodo completo | Pendiente de acreditación | No resuelto al corte | P95 y 5xx favorables solo en población válida. Julio/José revisan concurrencia, sondeos y condiciones del host |
| S2-06 | 09/10/2026 | BDD de preferencias sigue en borrador; dificulta aceptar formalmente escenarios y resolver diferencias | Media | DOC-01 de ST-028 | Antes de aceptar US-005, propuesta 23/10/2026 | Pendiente de ratificación | No resuelto al corte | Frank/Julio y Antony confirman reglas; actualizar estado con evidencia, sin inferir aprobación de tests verdes |
| S2-07 | 09/10/2026 | Validación accesible/offline limitada; no acredita lector de pantalla, dispositivos o rutas reales | Media | Límites ST-030/ST-032 | Antes de cerrar EN-004, propuesta de plan al 23/10/2026 | Pendiente de ampliación | No resuelto al corte | José/Giancarlo proponen pruebas reales de desconexión, aislamiento, teclado y lector; conservar estados sin asignación |
| S2-08 | 09/10/2026 | Review y retrospectiva sin acta del Sprint 2; falta evidencia de feedback y acuerdos | Media | Preparación documental solicitada por Giancarlo | Fecha de exposición/reunión por confirmar | Pendiente de reunión o registro | No consta realización | Julio coordina, Frank registra asistentes y acuerdos; usar el guion sin atribuir una reunión ya realizada |
| S2-09 | 09/10/2026 | ST-032 registró un aviso de dependencia alta en su instalación; falta conclusión vigente sobre ese hallazgo | Media | Informe ST-032, registro histórico | Revisar antes de entrega final, propuesta 23/10/2026 | Pendiente de verificación actual | No consta cierre en la fuente | Antony/José verifican versión y resultado actual del análisis; no se declara vulnerabilidad vigente ni solución sin evidencia |

## Acciones de seguimiento

Priorizar S2-02 y S2-06 para preferencias; S2-03 y S2-07 para experiencia móvil;
S2-04/S2-05 para cerrar objetivos de rendimiento. Cada resolución debe indicar
commit, prueba o decisión y fecha efectiva. Los impedimentos de reuniones se
resuelven con actas reales, no únicamente mediante actualización del Markdown.

## Fuentes

- [ST-028: matriz y defectos](../../backend/VALIDACION_ST028.md).
- [ST-032: límites, migración y validación](../../frontend/VALIDACION_ST032.md).
- [ST-036: resultados y SLA](../../backend/INFORME_ST036.md).
- [ST-037](../../backend/INFORME_ST037.md) y [ST-038](../../backend/VALIDACION_ST038.md).

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 01/10/2026 | Entregable del Sprint 1; contenido anterior conservado en el historial Git. |
| 1.1.0 | 09/10/2026 | Sustitución del contenido por el entregable del Sprint 2, con evidencias y pendientes al corte. |

El nombre V_1_0_0 del archivo se conserva por exigencia de la consigna.
La versión del contenido se incrementa a 1.1.0 para identificar esta actualización.

[← Volver al README principal](../../README.md)
