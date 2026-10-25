# ECL-54 / ST-028 — Matriz de validación de preferencias y clientes

**Trazabilidad:** ECL-54 / ST-028 → ECL-11 / US-005 → RF-005 y RN-006.
**Fecha:** 09/10/2026. **Base Git:** `3798d57`.
**Rama:** `test/ECL-54-validacion-preferencias-clientes`.
**Resultado:** validación ejecutada; nueve escenarios BDD compatibles con el
comportamiento observado y una brecha en P8. No acredita completar US-005.
**Actualización 13/10/2026:** D-01 corregido y reprobado en Chrome y Firefox;
ver [Reprueba de D-01](#reprueba-de-d-01--13102026).

## Fuente y límites de aprobación

Se contrastó el archivo ECL-51/ST-025 de docs/02 Planificación/BDD.
**La fuente continúa marcada BORRADOR**, con ratificación de contrato pendiente.
Se conservó intacta: ejecutar pruebas no constituye aprobar sus reglas.
Su apartado de estado inicial describe una versión antigua, anterior a la API
y formulario actuales; esa descripción histórica no representa esta base Git.

Se utilizaron el contrato implementado en ST-026, el formulario de ST-027,
las reglas RF-005/RN-006 y los observables del BDD.
Los resultados acreditan comportamientos medidos; la aprobación de reglas,
el estado Jira y el cierre funcional corresponden al equipo.

## Entorno y ejecución

- Python 3.13.3, PostgreSQL 16.9/PostGIS 3.5.2.
- Base nueva ecologistica_ecl54_api_test para pruebas integradas con migraciones.
- Base independiente ecologistica_ecl54_preview_test para navegador.
- Datos y cuentas exclusivamente sintéticos; sin cambios sobre datos compartidos.
- API en 127.0.0.1:18054; Vite en 127.0.0.1:15154.
- Chrome 154.0.8037.98 / Administrador; Firefox 157.0 / Operador.
- Conductor autenticado contrastado en ambos navegadores.
- Analista/Auditor y sesiones sin autenticar contrastados por HTTP integrado.
- Las pruebas integradas usan TestClient con app real y PostgreSQL;
  el navegador utiliza solicitudes HTTP reales al servidor local.
- Solo el aviso 503 en navegador se simuló mediante interceptación PATCH.
  El rollback por error de persistencia tiene una prueba integrada separada,
  que inyecta SQLAlchemyError tras flush en la base de pruebas.

## Matriz de escenarios y resultados

Referencias de evidencia:
**A:** test_preferencias_bdd.py; **B:** test_preferencias_http_e2e.py;
**U:** pruebas unitarias existentes de preferencias; **N:** instrumento de
navegador verify-preferences-bdd.mjs y capturas ECL-54.

| Caso | BDD / regla | Acción y observable contrastados | Resultado | Evidencia |
|---|---|---|---|---|
| M01 | P1 | Cliente existente con campos null; PATCH válido y GET devuelven ID y valores exactos | Aprobado | A, B, N 01–03 |
| M02 | P2 | Actualizar terna completa; misma asociación y lectura posterior persistida | Aprobado | A, B |
| M03 | P3 | Límites inclusivos 120/255/255 aceptados en cada campo | Aprobado | A, U |
| M04 | P3 | 121/256/256 rechazados con 422, campo identificado y valores previos intactos | Aprobado | A, U; N 04 para horario |
| M05 | P4a | PATCH parcial conserva campos omitidos y nombre del cliente | Aprobado | A, B |
| M06 | P4b | null limpia solo la restricción; horario y referencia conservados | Aprobado | A, B, N |
| M07 | P4c | Vacío y espacios rechazados para cada campo; sin cambios persistidos | Aprobado | A, U |
| M08 | P5 | GET/PATCH sobre UUID inexistente devuelven 404; no se crean clientes ni asociaciones | Aprobado | A, B; N 07 para GET |
| M09 | P6 | Cambiar A conserva valores no nulos de B, su ID y nombre; dos filas permanecen | Aprobado | A, N |
| M10 | P7 | Administrador y Operador pueden consultar y actualizar; proyección solo de preferencias | Aprobado | A, B, N |
| M11 | P7 | Conductor, Analista y Auditor reciben 403 en GET/PATCH, sin cambios | Aprobado | B; N 08 para Conductor |
| M12 | P7 | Sin sesión, GET/PATCH devuelven 401 | Aprobado | B |
| M13 | Robustez | Número, booleano, lista, objeto y NUL rechazados para cada campo; error no refleja input | Aprobado | A, U |
| M14 | Contrato PATCH | Objeto vacío, campos extra y cambio de cliente_id rechazados; asociación intacta | Aprobado | A, B, U |
| M15 | Atomicidad | Error después de flush devuelve 503 sanitizado y revierte preferencias | Aprobado | B |
| M16 | Pedido / RN-006 | Llamador consulta preferencia y selecciona referencia explícitamente al POST; pedido y cliente permanecen independientes | Aprobado a nivel API | B |
| M17 | P8 / RF-005 | Seleccionar cliente en formulario de pedido debe proponer preferencias y acción explícita de copia | 09/10: brecha reproducida (D-01). 13/10: aprobado en reprueba | N 09 (09/10); R 09–10 (13/10) |
| M18 | Interfaz | Guardar, recuperar, conservar edición ante 503 simulado, 404 real, Tab y ancho 360 px | Aprobado para estas comprobaciones | N 01–08 |

M16 no sustituye M17: copiar mediante código de prueba no acredita una propuesta
en el formulario. La agrupación BDD es P1, P2, P3, P4a, P4b, P4c, P5, P6, P7
contrastados satisfactoriamente y P8 con brecha. Los casos adicionales amplían
observables; no son nuevas reglas aprobadas.

## Registro de defectos y diferencias

### D-01 — No se proponen preferencias al registrar pedidos

- **Clasificación:** brecha funcional reproducida contra P8 y RF-005;
  prioridad alta propuesta, pendiente de triage.
- **Base y alcance:** frontend actual, ambos navegadores; no es un fallo del
  guardado de preferencias ni una pérdida de asociación.
- **Precondición:** usuario Administrador u Operador y cliente A con preferencias
  guardadas, consultables por GET.
- **Pasos:** entrar en Registrar pedido; introducir el UUID del cliente A;
  revisar el formulario y la actividad de red.
- **Esperado según P8 propuesto:** mostrar horario/restricción como contexto
  y ofrecer Usar como referencia del pedido, sin modificar ventanas ni cliente.
- **Observado:** no hay consulta de preferencias ni acción de copia; se mantiene
  la referencia manual y las ventanas introducidas. El formulario no propone
  los valores guardados.
- **Impacto:** el usuario debe consultar y transcribir fuera del flujo de pedido.
- **Evidencia:** capturas chrome/firefox-09-P8-propuesta-ausente.png y
  P8OrderProposalAvailable: false en resultados.json.
- **Seguimiento propuesto:** Julio/Frank ratifican la interacción y alcance;
  José/Giancarlo implementan la propuesta visual con el contrato de Antony.
  Retestar propuesta, copia editable, ausencia de copia implícita y aislamiento.
- **Estado:** registrado localmente, sin ticket nuevo en Jira ni comentario remoto.
- **Corrección (13/10/2026):** rama `fix/ECL-53-propuesta-preferencias-pedido`,
  commits `215a8cb` (endpoint `GET /clientes`) y `074fd27` (selector y
  propuesta). Reprueba aprobada; el cierre depende de la revisión del PR.

### DOC-01 — BDD todavía en borrador

La fuente mantiene aprobación pendiente y afirmaciones históricas de API/UI
inexistentes. No se reescribió ni se aprobó desde esta validación.
Julio/Frank deben revisar estado y contrato con Antony antes de aceptar
formalmente los BDD. No se atribuye esta decisión a una ejecución automatizada.

## Resultados automatizados

| Conjunto | Resultado |
|---|---|
| HTTP integrado de preferencias, BDD y aislamiento | 8 pruebas aprobadas, sin omisiones |
| Unitarias API/schema/service de preferencias | 56 aprobadas |
| Cobertura backend de esos tres componentes | 99.02% líneas; schemas y service 100% |
| Regresión frontend completa | 441 pruebas / 27 archivos aprobados |
| Cobertura global frontend | 95.65% statements, 93.93% branches, 96.06% functions, 97.76% lines |
| Chrome y Firefox contra HTTP real | Gestión de preferencias aprobada; P8 observado ausente |
| Ruff del nuevo test y lint frontend | Aprobados |

No hay cambios de código de producto. Se añadieron comprobaciones, matriz y
evidencia; no se corrigió D-01 ni se amplió el alcance de implementación.
No es una auditoría completa WCAG ni una prueba de concurrencia.
CI/SAST del nuevo PR y revisión humana siguen pendientes.

## Evidencia y reproducción

- [JUnit de integración](../../../../backend/evidencias/ECL-54/api-tests.xml).
- [JUnit de unitarias](../../../../backend/evidencias/ECL-54/unit-tests.xml).
- [Resultados consolidados y hashes](../../../../backend/evidencias/ECL-54/resultados.json).
- [Guía de ejecución backend](../../../../backend/evidencias/ECL-54/README.md).
- [Capturas y navegador](../../../../frontend/evidencias/ECL-54/README.md).
- [Resultados de navegador](../../../../frontend/evidencias/ECL-54/resultados.json).
- [Test BDD](../../../../backend/tests/integration/test_preferencias_bdd.py).
- [Instrumento de navegador](../../../../frontend/scripts/verify-preferences-bdd.mjs).

La evidencia no equivale a aprobación del contrato ni a cierre de US-005.
El equipo puede revisar ST-028 con esta matriz y su registro de diferencias.

## Reprueba de D-01 — 13/10/2026

**Cambio probado:** el formulario «Registrar pedido» selecciona el cliente con
un buscador accesible (`GET /clientes`) y, al elegirlo, muestra sus
preferencias. Horario y restricción de acceso se muestran como información
del cliente y no se copian al pedido (RN-006). La referencia solo se copia con
el botón «Usar como referencia del pedido».

**Entorno:** API FastAPI y vista previa del frontend en `127.0.0.1`, base
desechable `ecologistica_ecl54_preview_test` (PostgreSQL 16.15 + PostGIS
3.6.2) con dos clientes y tres cuentas sintéticas. Instrumento
[`verify-preferences-bdd.mjs`](../../../../frontend/scripts/verify-preferences-bdd.mjs)
con Playwright 1.58.2 y Node 22.18.0: Chrome 155.0.8059.40 como Administrador
y Firefox 146.0.1 (compilación de Playwright) como Operador. El 09/10 se usó
Firefox 157.0. El instrumento escribe ahora en una carpeta `retest-<fecha>` y
no sobrescribe la evidencia del 09/10.

| Tipo de ruta | Escenario | Resultado esperado | Resultado observado | Evidencia | Estado |
|---|---|---|---|---|---|
| Dorada | Operador/Administrador elige al cliente A y pulsa «Usar como referencia del pedido» | La referencia guardada pasa al campo del pedido; ventanas y cliente sin cambios; ningún `POST /pedidos` | Coincide en ambos navegadores | R 10 y `P8ExplicitReferenceCopy`, `P8WindowsUnchanged`, `P8ClientUnchanged` | Aprobado |
| Feliz | Cliente A con horario, referencia y restricción | Las tres preferencias se muestran como contexto; sin la acción, la referencia propia del pedido se conserva | Coincide en ambos navegadores | R 09 y `P8OrderProposalAvailable` | Aprobado |
| Infeliz | Identificador de cliente inexistente en el buscador | Sin opciones seleccionables; la API devuelve 404 para ese ID | «No se encontraron clientes con ese texto.» y 404 | R 07 | Aprobado |
| Infeliz | Conductor intenta abrir preferencias | Acceso denegado en interfaz y 403 en API | Coincide | R 08 | Aprobado |
| Borde | Fallo al cargar preferencias, cliente sin preferencias, cambio de cliente y referencia ya igual | Pedido registrable, «Sin registrar», recarga del panel y acción deshabilitada | Cubierto por pruebas de componente | [`OrderCreatePage.test.tsx`](../../../../frontend/src/pages/OrderCreatePage.test.tsx) | Aprobado (automatizado) |

R = [capturas de la reprueba](../../../../frontend/evidencias/ECL-54/retest-D01-20261013/README.md).
Los escenarios P1–P7 del instrumento se repitieron en la misma ejecución con
el nuevo selector y también pasaron.

**Límite:** la BDD ECL-51 sigue marcada BORRADOR. La aceptación formal de
US-005 requiere que Julio y Frank la ratifiquen; esta reprueba acredita el
comportamiento de P8 tal como está redactado.

[↑ Índice del Sprint 2](../README.md)

[← Volver al README principal](../../../../README.md)
