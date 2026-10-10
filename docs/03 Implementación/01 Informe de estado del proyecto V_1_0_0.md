# Informe de estado del proyecto — Sprint 2

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

## Resumen de avance

El Sprint 2 amplía la base operativa con gestión de conductores y preferencias,
experiencia móvil, almacenamiento offline, observabilidad y análisis de rendimiento.
La captura Jira aportada por Giancarlo muestra cinco elementos principales y las
19 subtareas ECL-46–64 en Finalizada: 27/27 Story Points de padres y 19/19 subtareas.
Son medidas separadas; las subtareas no suman puntos adicionales. Los informes
técnicos aún registran brechas y objetivos no acreditados que deben conciliarse
con ese cierre operativo.

La Review y la retrospectiva de este Sprint se preparan para la exposición.
No se dispone de fecha, asistentes ni acuerdos de una reunión de Sprint 2 realizada.
La captura todavía ofrece Completar sprint: el sprint aparece activo aunque sus
actividades figuren finalizadas. El 100% corresponde a estado Jira; no equivale
a acreditar todos los objetivos de rendimiento o aceptación en una Review.

## Historias de Usuario completadas en este Sprint

Los cinco padres figuran Finalizada en la captura aportada. La tabla registra
el incremento comprobable y los límites técnicos que permanecen en sus fuentes.

| Padre | Subtareas | Incremento disponible | Evaluación al corte |
|---|---|---|---|
| ECL-9 / US-003 — Conductores y disponibilidad | ECL-46–50 / ST-020–024 | Modelo, reglas, API protegida, formulario/listado y pruebas | Gestión implementada y validada; elegibilidad básica no equivale a factibilidad de una ruta |
| ECL-11 / US-005 — Preferencias de entrega | ECL-51–54 / ST-025–028 | GET/PATCH, formulario, validación e aislamiento entre clientes | Gestión contrastada; propuesta en formulario de pedidos pendiente (P8); BDD sigue en borrador |
| ECL-22 / EN-004 — Experiencia móvil y desconexión | ECL-55–58 / ST-029–032 | Diseño, itinerario/siguiente parada/alertas, mejoras móviles, IndexedDB y outbox | Incrementos disponibles; asignaciones reales dependen del planificador; revisión accesible completa pendiente |
| ECL-23 / EN-005 — Capacidad y observabilidad | ECL-59–62 / ST-033–036 | Plan, métricas, sondeos, campaña y procedimientos operativos | Resultados locales disponibles; 100 solicitudes sostenidas y SLA mensual no acreditados |
| ECL-25 / EN-007 — Transferencia y consultas | ECL-63–64 / ST-037–038 | EXPLAIN, mediciones y SELECT EXISTS para cliente | Mejora parcial verificada; payload de dashboard y consultas de rutas pendientes |

## Demostración del trabajo completado

La exposición puede mostrar alta/edición de conductores, rechazo de datos inválidos,
preferencias por cliente, navegación móvil, cola offline y consulta de métricas.
El [guion de Review](<03 Revisión del Sprint V_1_0_0.md>) organiza las demostraciones
y especifica qué datos son sintéticos y qué escenarios se simulan.

| Evidencia de calidad | Resultado documentado | Alcance |
|---|---|---|
| ST-024 | 99 unitarias de conductores; 10 de integración; cobertura específica 98.13% | Validación de ese incremento, no total acumulado actual |
| ST-038 | 556 unitarias backend; 117 integradas verificadas; repositorio afectado 100% | Ejecución de optimización y regresión |
| ST-028 | 56 unitarias de preferencias; 8 integradas; 441 frontend; Chrome/Firefox | Gestión y asociación; P8 observado ausente |
| ST-036 | P95 agregado 1.497054 s; 0% 5xx en poblaciones válidas completas | Diagnóstico local; no acredita concurrencia sostenida ni SLA |
| ST-038 | Cinco campos del cliente → un booleano; 58 → 1 byte de valores internos | Minimización SQL; no equivale a tráfico HTTP ni demuestra aceleración |

Las ejecuciones corresponden a fechas y alcances distintos: sus conteos no se suman.
No se afirma una nueva ejecución de pruebas por actualizar estos documentos.

## Organización del código y configuración

Se conserva la arquitectura existente: backend FastAPI/SQLAlchemy/Alembic;
frontend React/TypeScript/Vite; PostgreSQL/PostGIS y Docker Compose.
Backend y frontend ya están separados en carpetas propias; src/frontend es
un ejemplo de la consigna, no una necesidad de trasladar el código.

.gitignore excluye .env privados, node_modules, entornos Python, caches y
resultados temporales. Las evidencias sintéticas se mantienen en backend/evidencias
y frontend/evidencias. docs/03 Implementación contiene únicamente estos cuatro Markdown.

Los requisitos, reglas y C4 describen el sistema objetivo. Los README técnicos
y validaciones describen la implementación disponible; no se reducen requisitos
para declarar terminadas funciones aún ausentes.

## Pendientes

1. Resolver la propuesta de preferencias en pedidos y ratificar el BDD ST-025.
2. Conectar asignaciones del conductor al planificador y verificar rutas reales.
3. Completar auditoría de accesibilidad y pruebas offline con el despliegue real.
4. Acreditar concurrencia sostenida y disponibilidad durante el periodo operativo.
5. Implementar dashboard/rutas antes de verificar el payload agregado de 250 KB.
6. Registrar fecha, asistentes, feedback y acuerdos de Review/retrospectiva.
7. Conciliar el cierre Jira aportado con los límites de los informes y adjuntar
   revisión/CI correspondientes al commit final de entrega.

## Fuentes y coherencia

- [Conductores: API](../../backend/VALIDACION_ST022.md),
  [interfaz](../../frontend/VALIDACION_ST023.md) y [pruebas](../../backend/VALIDACION_ST024.md).
- [Preferencias: validación integral](../../backend/VALIDACION_ST028.md).
- [Experiencia móvil](../../frontend/VALIDACION_ST030.md) y
  [almacenamiento/sincronización](../../frontend/VALIDACION_ST032.md).
- [Observabilidad](../../backend/VALIDACION_ST034.md),
  [resultados y SLA](../../backend/INFORME_ST036.md),
  [mediciones iniciales](../../backend/INFORME_ST037.md) y
  [optimización](../../backend/VALIDACION_ST038.md).

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 01/10/2026 | Entregable del Sprint 1; contenido anterior conservado en el historial Git. |
| 1.1.0 | 09/10/2026 | Sustitución del contenido por el entregable del Sprint 2, con evidencias y pendientes al corte. |

El nombre V_1_0_0 del archivo se conserva por exigencia de la consigna.
La versión del contenido se incrementa a 1.1.0 para identificar esta actualización.

[← Volver al README principal](../../README.md)
