# Revisión del Sprint — Sprint 2

**Nombre del Proyecto:** EcoLogística Lima — optimizador de rutas sostenibles para DistriRápido S.A.C.

**Líder del Proyecto:** Julio Armando Naupari Camarena.

**Asignatura:** Taller de Proyectos 2 — Ingeniería de Sistemas e Informática.

**Sprint:** Sprint 2 — Gestión operativa y experiencia del conductor.

**Periodo planificado:** 08/10/2026–23/10/2026, según el tablero compartido.

**Fecha de corte:** 13/10/2026, America/Lima.

**Versión del contenido:** 1.2.0.

**Fuente del corte técnico:** `main` en `480b4f3` (PR #47–#53 integrados) y PR #54 abierto.

**Estado de la ceremonia:** Review realizada el 09/10/2026 sin demostración; demostración complementaria preparada.

## Resultado del Sprint

| Elemento | SP | Jira | Criterios acreditados |
|---|---:|---|---|
| ECL-9 / US-003 Conductores y disponibilidad | 5 | Finalizada | Parcial |
| ECL-11 / US-005 Preferencias de entrega | 3 | Finalizada | Cumple (BDD pendiente de ratificar) |
| ECL-22 / EN-004 Experiencia móvil, accesible y offline | 8 | Finalizada | Parcial |
| ECL-23 / EN-005 Capacidad, disponibilidad y observabilidad | 8 | Finalizada | Parcial |
| ECL-25 / EN-007 Transferencia de datos y consultas | 3 | Finalizada | No cumple |

Solo se presenta como completo lo que se demuestra a continuación. Los criterios
proceden de las BDD de [Transformando a ágil](<../02 Planificación/01 Transformando a ágil V_1_0_0.md>).
Los datos de la demostración son ficticios y se crean con `backend/scripts/seed_demo.py`.

## Criterios de aceptación por historia y enabler

### ECL-9 / US-003 — Gestionar conductores y disponibilidad

| Tipo de ruta | Escenario | Resultado esperado | Resultado observado | Evidencia | Estado |
|---|---|---|---|---|---|
| Dorada | El Administrador registra un conductor con licencia vigente y disponibilidad válida | Queda habilitado para asignación | `habilitado_asignacion = true`; alta auditada | `verify-drivers.mjs` (Chrome y Firefox, 13/10), [`test_conductor_audit.py`](../../backend/tests/integration/test_conductor_audit.py) | Cumple |
| Feliz | El Operador cambia la disponibilidad de un conductor habilitado | La nueva franja se guarda | PATCH 200; evento `CONDUCTOR_ACTUALIZADO` con los campos modificados, sin valores personales | [`test_conductor_audit.py`](../../backend/tests/integration/test_conductor_audit.py) | Cumple |
| Feliz | La nueva franja se usa en planificaciones posteriores | El planificador la considera | No existe planificador de rutas | — | Pendiente (ECL-12, Sprint 3) |
| Infeliz | Conductor con licencia vencida | El sistema impide su asignación e informa la restricción | Aparece «No habilitado» y «Licencia vencida» en el perfil; no hay asignación de rutas que bloquear | Demo: «Conductor Demo Licencia Vencida»; [ST-024](<Sprint 2/validaciones/VALIDACION_ST024.md>) | Parcial |
| Infeliz | Registro con un DNI ya registrado | Conflicto sin cambios | HTTP 409 y alerta; los datos no cambian | `verify-drivers.mjs`, [ST-024](<Sprint 2/validaciones/VALIDACION_ST024.md>) | Cumple |
| Borde | Conductor sin franja de disponibilidad | No habilitado | «Sin disponibilidad» y «No habilitado» | [`test_seed_demo.py`](../../backend/tests/integration/test_seed_demo.py) | Cumple |
| Borde | Listado de 100 conductores | Sin consultas por fila | 2 consultas SQL por página (antes 102) | [`test_conductor_list_queries.py`](../../backend/tests/integration/test_conductor_list_queries.py) | Cumple |

### ECL-11 / US-005 — Gestionar preferencias de entrega

| Tipo de ruta | Escenario | Resultado esperado | Resultado observado | Evidencia | Estado |
|---|---|---|---|---|---|
| Dorada | El Operador busca el cliente al registrar un pedido | Ve sus preferencias como contexto y copia la referencia solo con una acción explícita | Horario y restricción visibles sin copiarse; referencia copiada con «Usar como referencia del pedido»; ventanas sin cambios | [Reprueba D-01](<Sprint 2/validaciones/VALIDACION_ST028.md>) (Chrome y Firefox, 13/10) | Cumple |
| Feliz | Guardar una preferencia válida y consultarla después | Queda asociada al cliente | Persistida y recuperada; otros clientes sin cambios | [ST-028](<Sprint 2/validaciones/VALIDACION_ST028.md>) M01–M09 | Cumple |
| Infeliz | Preferencia vacía o de 121 caracteres | Se pide corrección y no se guarda | 422 asociado al campo; datos previos intactos | ST-028 M13–M14 | Cumple |
| Infeliz | Conductor, Analista o Auditor intentan consultar o editar | Acceso denegado | 403 sin cambios | ST-028 M11 | Cumple |
| Borde | Cliente sin preferencias y búsqueda con `%` literal | «Sin registrar» sin acción de copia; el comodín no amplía la búsqueda | Coincide | [`OrderCreatePage.test.tsx`](../../frontend/src/pages/OrderCreatePage.test.tsx), [`test_clientes_http_e2e.py`](../../backend/tests/integration/test_clientes_http_e2e.py) | Cumple |

La aceptación formal requiere ratificar la BDD ECL-51, que sigue en BORRADOR (impedimento I-03).

### ECL-22 / EN-004 — Experiencia accesible, responsive y tolerante a desconexión

| Tipo de ruta | Escenario | Resultado esperado | Resultado observado | Evidencia | Estado |
|---|---|---|---|---|---|
| Dorada | El conductor consulta su ruta a 360 px | Ve la siguiente parada sin desplazamiento horizontal y con WCAG 2.1 AA | Tarjeta destacada de la siguiente parada; 0 violaciones axe; sin desbordamiento a 360/768/1280 px | [Accesibilidad](../../frontend/evidencias/ECL-22-rediseno/README.md), capturas `07-itinerario-*` | Cumple |
| Feliz | Pierde y recupera la conexión con reportes pendientes | Conserva el itinerario y sincroniza | 10 rondas por navegador; 20 reportes persistidos una sola vez | [Reprueba ECL-58](../../frontend/evidencias/ECL-58/retest-20261013/README.md) (Chrome 155 y Firefox 157), PR #54 | Cumple |
| Infeliz | La API no responde al reconectar | Reintenta sin duplicar | Reintento con espera creciente; sin duplicados | Ronda 2 de la reprueba | Cumple |
| Infeliz | Falla la carga sin itinerario guardado | Mensaje claro y opción de reintentar | «No se pudo cargar tu itinerario» con «Reintentar» | [`DriverItineraryPage.test.tsx`](../../frontend/src/pages/DriverItineraryPage.test.tsx) | Cumple |
| Borde | Alertas operativas en la ruta | Visibles junto a la siguiente parada | Solo existen en el ejemplo ficticio; no hay fuente real de alertas | — | Pendiente (ECL-14, Sprint 3) |
| Borde | Uso con lector de pantalla | Navegación comprensible | No evaluado con lector de pantalla | — | Pendiente (Sprint 3) |

### ECL-23 / EN-005 — Capacidad, disponibilidad y observabilidad

| Tipo de ruta | Escenario | Resultado esperado | Resultado observado | Evidencia | Estado |
|---|---|---|---|---|---|
| Dorada | Carga representativa sobre el registro de pedidos | P95 ≤2 s | 1,75 s / 1,22 s / 1,10 s en tres corridas | [ST-036](<Sprint 2/informes/INFORME_ST036.md>) | Cumple |
| Feliz | Errores del servidor durante la carga | 5xx <1 % | 0 % en 55 414, 70 395 y 77 989 solicitudes | ST-036 | Cumple |
| Feliz | Observar disponibilidad, errores y latencias | Métricas registradas | Endpoints de salud y métricas protegidas instrumentados | [ST-034](<Sprint 2/validaciones/VALIDACION_ST034.md>) | Cumple |
| Infeliz | 100 solicitudes concurrentes sostenidas | ≥100 en vuelo durante la prueba | Solo en el 19–21 % de los segundos | [ST-035](<Sprint 2/validaciones/VALIDACION_ST035.md>), ST-036 | No cumple |
| Borde | SLA ≥99,5 % entre 05:00 y 22:00 | SLA calculado sobre un mes | Sin un mes operativo observado | ST-036 | Pendiente |

### ECL-25 / EN-007 — Transferencia de datos y consultas

| Tipo de ruta | Escenario | Resultado esperado | Resultado observado | Evidencia | Estado |
|---|---|---|---|---|---|
| Dorada | Consulta normal del dashboard | Respuesta ≤250 KB sin mapa | El dashboard no existe; no hay respuesta que medir | [ST-037](<Sprint 2/informes/INFORME_ST037.md>) | No cumple |
| Feliz | Plan de las consultas de pedidos | Índices o justificación, sin datos innecesarios | Existencia de cliente con un booleano (de 58 a 1 byte de valores); índices justificados | [ST-038](<Sprint 2/validaciones/VALIDACION_ST038.md>) | Cumple |
| Infeliz | Listado con una consulta por fila (N+1) | Detectado y corregido | De 22 a 2 consultas por página | ST-038, [PR #48](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/48) | Cumple |
| Borde | Consultas de rutas optimizadas | Revisadas | No existen todavía | — | Pendiente (ECL-12, Sprint 3) |

## Guion de demostración

Duración: 15 minutos. Base `ecologistica_demo` sembrada el mismo día con
`seed_demo.py` (contraseñas solo en variables de entorno). La conduce Antony
Munive Ríos; Julio Armando Naupari Camarena controla el tiempo.

| Tiempo | Paso | Qué se muestra | Tipo de ruta |
|---|---|---|---|
| 00:00–01:00 | Contexto | Datos ficticios, objetivo del Sprint 2 y tabla de resultados de esta revisión | — |
| 01:00–02:30 | Login por rol | Administrador: menú lateral e inicio con datos reales (5 vehículos, 4 conductores, 2 habilitados). Conductor: navegación inferior | Dorada |
| 02:30–05:00 | Conductores | Listado; «Conductor Demo Licencia Vencida» (No habilitado, Licencia vencida) y «Conductora Demo Sin Disponibilidad»; edición de un teléfono y su evento de auditoría | Borde e infeliz |
| 05:00–07:30 | Pedido | Buscar «Bodega», ver sus preferencias y usar la referencia (feliz); buscar un identificador inexistente sin resultados y enviar sin cliente seleccionado (infeliz) | Feliz e infeliz |
| 07:30–10:00 | Itinerario del conductor | `conductor.demo`: siguiente parada 09:00 y recorrido hasta las 13:00; sin conexión, «Marcar como entregado», recarga y reconexión hasta ver «Entregado» | Dorada y feliz |
| 10:00–11:30 | Métricas | Salud y métricas protegidas; resultados de capacidad, incluido lo no acreditado (concurrencia sostenida y SLA) | Infeliz |
| 11:30–13:00 | Rediseño | Capturas antes/después, tema oscuro y vista a 360 px | — |
| 13:00–15:00 | Pendientes | Tabla de pendientes y preguntas del stakeholder | — |

## Acta de la Review — 09/10/2026

| Campo | Registro |
|---|---|
| Fecha y hora | Viernes 09/10/2026, 15:38 |
| Formato | Exposición del Sprint 2 en clase ante el docente |
| Asistentes del equipo | Julio Armando Naupari Camarena (líder), Frank Roy Yupanqui Acevedo (analista de requisitos), Giancarlo Marcio Soto Escobar (UX/UI), Antony Munive Ríos (backend y optimización), José Samuel Delgadillo Pantoja (frontend y QA) |
| Stakeholder evaluador | Daniel Gamarra Moreno, docente de Taller de Proyectos 2 |
| Demostración | No se realizó |
| Decisión | Sprint evaluado con **14/20** |

### Calificación por criterio de la rúbrica

Registro comunicado por Antony Munive Ríos.

| Criterio | Nota (sobre 4) |
|---|---:|
| 1. Informe de estado | 3 |
| 2. Registro de impedimentos | 3 |
| 3. Revisión del Sprint | 2 |
| 4. Retrospectiva | 3 |
| 5. Estructura y .gitignore | 3 |
| 6. Coherencia y versionado | 4 |
| 7. Ubicación y README | 2 |

### Feedback del docente y acción que lo atiende

| Comentario del docente | Acción | Referencia |
|---|---|---|
| «Los archivos del Sprint 2 deben estar dentro de la carpeta de implementación.» | Validaciones, informes y guías movidos a `docs/03 Implementación/Sprint 2/` con mapa de reubicación | [PR #47](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/47) |
| «Algunos impedimentos se pueden gestionar como parte del proyecto.» | El registro separa impedimentos de defectos y brechas, que pasan al backlog con su clave Jira | [Registro de impedimentos 1.2.0](<02 Registro de Impedimentos V_1_0_0.md>), PR de la Fase 4 |
| «Los criterios de aceptación deben considerar las rutas doradas (golden paths), las rutas felices, las rutas infelices y las rutas de borde.» | Pruebas nombradas por tipo de ruta y tablas de criterios por ruta en esta revisión | [PR #48](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/48)–[#54](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/54) |
| «Las acciones por realizar son compromisos que deben cumplirse.» | Plan de acción con métrica verificable y seguimiento de las acciones del Sprint 1 | [Retrospectiva 1.2.0](<04 Retrospectiva del Sprint V_1_0_0.md>) |
| «La documentación no incluye la navegación por todos los archivos MD.» | README con enlaces de ida y vuelta a todos los `.md` y verificador `check_docs.py` en CI | [PR #47](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/47) |
| «No se realizó la demostración de las funcionalidades.» | Datos de demostración, rediseño de la interfaz y guion con tiempos; demostración complementaria | [PR #52](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/52), [PR #53](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/53) |

## Demostración complementaria posterior

Sigue el [guion de demostración](#guion-de-demostración) sobre `main` con los
PR #47–#54 integrados. Estado al 13/10/2026: preparada y no ejecutada. Al
realizarla se registrarán aquí su fecha real y el enlace a la grabación o a
las capturas.

## Pendientes

| Pendiente | Clave Jira | Sprint de destino |
|---|---|---|
| Planificador VRPTW y asignación real de rutas | ECL-12, ECL-21 | Sprint 3 |
| Reoptimización ante incidencias | ECL-13 | Sprint 3 |
| Versionado de parámetros y exactitud de cálculos | ECL-26 | Sprint 3 |
| Dashboard y medición del payload ≤250 KB | ECL-15, ECL-25 | Sprint 3 |
| Mapa con alertas operativas reales | ECL-14 | Sprint 3 |
| Carga sostenida de 100 solicitudes y SLA mensual | ECL-23 | Sprint 3 |
| Ratificación de las BDD de conductores y preferencias | ECL-47, ECL-51 | Sprint 2 (antes del cierre) |
| Revisión e integración de la reconexión sin evento `online` | ECL-58 (PR #54) | Sprint 2 |
| Prueba con lector de pantalla | ECL-22 | Sprint 3 |

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 01/10/2026 | Entregable del Sprint 1; contenido anterior conservado en el historial Git. |
| 1.1.0 | 09/10/2026 | Sustitución del contenido por el entregable del Sprint 2, con evidencias y pendientes al corte. |
| 1.2.0 | 13/10/2026 | Criterios por tipo de ruta, guion de demostración con datos ficticios, acta de la Review del 09/10 y pendientes con clave Jira. |

El nombre V_1_0_0 del archivo se conserva por exigencia de la consigna.

[← Volver al README principal](../../README.md)
