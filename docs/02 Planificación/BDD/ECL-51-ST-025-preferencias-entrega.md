# ECL-51 / ST-025 — Reglas y BDD de preferencias de entrega

> **Estado: APROBADO.** Ratificado por Julio el 26/10/2026 en el PR #64,
> según su comentario explícito enlazado abajo. La aprobación documental no
> declara implementadas las diferencias y extensiones pendientes del backlog.

| Metadato | Valor |
|---|---|
| Versión | 1.0.0 |
| Fecha de revisión | 25/10/2026, America/Lima |
| Autor de la revisión | Frank Roy Yupanqui Acevedo — @FrankRoyYA |
| Ratificación de Julio | 26/10/2026 a las 12:13 (America/Lima) en el [PR #64](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/64#pullrequestreview-5656082598) |
| Ticket de ratificación | [ECL-71](https://continental-team-il84x39k.atlassian.net/browse/ECL-71) |
| Base contrastada | `main` en `dc148e7` |

## Trazabilidad y alcance

| Campo | Referencia |
|---|---|
| Subtarea | ECL-51 / ST-025 — Definir reglas y casos BDD de preferencias de entrega |
| Historia padre | ECL-11 / US-005 — Gestionar preferencias de entrega de clientes |
| Requisitos | RF-005; RN-006 |
| Sprint | BDD del Sprint 2; ratificación en el Sprint 3 mediante ECL-71 |
| Evidencia Jira | Ticket ECL-71 contrastado durante la revisión; no se atribuye aprobación de Julio |
| Trabajo excluido | Implementación de API/formulario y validación posterior ECL-54 / ST-028 |

Este archivo es un artefacto BDD separado para ST-025. No modifica requisitos de
línea base ni propone una entidad de preferencias adicional.

## Fuentes consultadas

- [RF-005 — Requisitos funcionales](../../01%20Inicio/06.%20Requisitos%20funcionales%20V_1_1_0.md)
- [RN-002 y RN-006 — Reglas de negocio](../../01%20Inicio/09.%20Reglas%20de%20negocio%20V_1_1_0.md)
- [Perfiles y matriz RBAC](../../01%20Inicio/08.%20Usuarios%20V_1_0_0.md)
- [Modelo lógico de datos](../../01%20Inicio/11.%20Base%20de%20datos%20V_1_1_0.md)
- [Requisitos no funcionales](../../01%20Inicio/07.%20Requisitos%20no%20funcionales%20V_1_2_0.md)
- [Definition of Done](../01%20Transformando%20a%20%C3%A1gil%20V_1_0_0.md#8-definition-of-done-dod-global)
- `backend/app/models/cliente.py`, `backend/app/models/pedido.py`,
  `backend/alembic/versions/0006_create_cliente_pedido.py`,
  `backend/app/api/pedidos.py`, `backend/app/schemas/pedido.py` y
  `backend/app/services/pedidos.py` en la base `origin/main`
  `099838bdec64c16c4ecaee04644f2f69ec2c46dc`.

La subtarea Jira, según el contenido aportado, solicita horarios preferidos,
referencias de ubicación y restricciones de acceso por cliente; el criterio
requiere casos de preferencias válidas, inválidas y actualización. ECL-71
contrasta esos casos con las pruebas y validaciones del Sprint 2; no se
atribuyen comentarios ni acuerdos no registrados.

## Estado observado y actualización ECL-71

El estado del borrador original corresponde a `099838b`, anterior a ST-026 y
ST-027. En `main` `dc148e7` ya existen GET/PATCH de preferencias, formulario,
selector de clientes y propuesta explícita de referencia al registrar pedidos.
Se reutilizan las columnas nullable de Cliente (120/255/255); no existe una
entidad nueva de preferencias. Pedido conserva su referencia y ventana propias.

La verificación abajo inspecciona pruebas y código, y cita las validaciones
ST-026/ST-027/ST-028. D-01 de P8 fue corregido y reprobado el 13/10/2026 según
ST-028; no se registra como un defecto abierto ni se duplica en Jira.

## Reglas confirmadas

| ID | Regla respaldada | Consecuencia para los BDD |
|---|---|---|
| RF-005 | Administrar por cliente horarios preferidos, puntos de referencia y restricciones de acceso; la preferencia debe proponerse al crear pedidos. | Las preferencias pertenecen al Cliente y deben estar disponibles en el flujo de pedido, con interacción pendiente de concretar. |
| Modelo/migración 0006 | Cliente tiene `horario_preferido VARCHAR(120) NULL`, `referencia VARCHAR(255) NULL` y `restriccion_acceso VARCHAR(255) NULL`. | Límites técnicos de almacenamiento: 120/255/255 caracteres; los campos pueden omitirse/ser nulos en persistencia. |
| Modelo y servicio Pedido | Pedido tiene `cliente_id` FK y su propio campo `referencia`; `POST /pedidos` comprueba existencia del cliente. | La referencia de Cliente y la del Pedido son datos distintos. No se copian sin una regla y selección acordadas. |
| RN-006 | Un **pedido** requiere `ventana_inicio < ventana_fin` y ubicación por coordenadas válidas o referencia verificable. | Esta regla temporal no convierte ni valida el texto de `horario_preferido`. |
| Matriz de usuarios/RBAC | Administrador: CRUD de clientes; Operador: CRU; Conductor: lectura según asignación/jornada; Analista: agregada; Auditor: anonimizada. La desactivación corresponde al Administrador. | Es una referencia global. No amplía automáticamente ECL-52 a todas las operaciones o permisos; el contrato de la subtarea debe identificar operaciones comprometidas y sus permisos. |

Los tamaños indicados describen el esquema físico aprobado y existente, no una
regla sobre el significado de una preferencia ni un formato de horario. No hay
regla aprobada que declare inválidos texto vacío, espacios, un horario textual
con cierta sintaxis u otro contenido semántico.

## Contrato candidato para revisión — no aprobado

- Reutilizar las tres columnas actuales de Cliente; no crear una entidad de
  preferencias ni interpretar `horario_preferido` como fecha/hora.
- Propuesta de API: `GET /clientes/{cliente_id}/preferencias` devuelve
  `cliente_id`, `horario_preferido`, `referencia` y `restriccion_acceso`;
  `PATCH /clientes/{cliente_id}/preferencias` actualiza solo campos incluidos
  sobre un Cliente existente. No propone un endpoint para registrar preferencias
  sin Cliente existente; ambas rutas están implementadas en ST-026.
- Acuerdo de Frank para revisión: en PATCH, campo omitido conserva su valor;
  `null` limpia el campo nullable; `""` y texto compuesto solo por espacios se
  rechazan sin cambios. Las cadenas con espacios alrededor se preservan tal como
  fueron enviadas; no se recortan ni normalizan silenciosamente. Antony y Julio
  deben revisar este acuerdo antes de cerrar el contrato.
- El esquema actual permite como máximo 120 caracteres para
  `horario_preferido` y 255 para `referencia` y `restriccion_acceso`. Propuesta
  pendiente para la API: validar esos límites antes de persistir y devolver un
  error por campo sin alterar valores existentes. Los tamaños del esquema son
  hechos observados; la validación HTTP está implementada y probada en
  ST-026/ST-028, pendiente de ratificación documental de Julio.
- Propuesta de formulario de pedido: mostrar horario y restricción como
  información contextual, sin convertirlos ni copiarlos. Ofrecer la referencia
  del Cliente mediante una acción explícita “Usar como referencia del pedido”;
  copiarla al campo independiente del Pedido no guarda hasta que el Operador
  confirme el pedido. La selección no modifica la preferencia del Cliente.
- Acuerdo de Frank para revisión: solo Administrador y Operador autorizados
  consultan y actualizan las preferencias del Cliente objetivo en ECL-52.
  Conductor, Analista y Auditor no reciben esta proyección en ese alcance.
  El backend aplica autorización aunque el frontend oculte acciones; Antony y
  Julio deben ratificarlo.

Los endpoints, la semántica omitido/null/vacío y los permisos se observaron en
la implementación de ST-026. En esta versión se presentan para ratificación de
Julio; la existencia de código y pruebas no equivale a aprobar el contrato.

## Datos sintéticos de referencia

Los ejemplos son valores ficticios en español y no añaden reglas semánticas:

| Cliente de prueba | `horario_preferido` | `referencia` | `restriccion_acceso` |
|---|---|---|---|
| `cliente-A` | `Mañana (preferido)` | `Puerta junto al parque` | `Ingreso por puerta lateral` |
| `cliente-B` | `Tarde (preferido)` | `Recepción principal` | `Avisar al llegar` |

Estos textos están por debajo de las capacidades actuales de sus columnas. No
significan que “mañana” o “tarde” sean ventanas de pedido ni autorizan
conversiones automáticas.

## Escenarios BDD — borrador

### P1 — Registrar y consultar preferencias válidas

- **Dado** un Cliente existente `cliente-A` cuyas tres preferencias son `null`
  y un Administrador u Operador autorizado.
- **Cuando** inicializa las preferencias de ese Cliente mediante el PATCH
  candidato con los valores sintéticos de la tabla y luego consulta
  `cliente-A`.
- **Entonces** cada valor queda guardado en su campo del registro de `cliente-A`
  y una consulta autorizada devuelve `cliente_id: cliente-A` y los tres valores
  sin alterarlos.

**Observables:** el identificador del cliente no cambia; se devuelve la misma
terna de valores; no se crea una fila en una entidad nueva de preferencias.
La operación y las rutas son propuestas; este caso inicializa datos sobre un
Cliente ya existente, no crea un Cliente ni una asociación independiente.

### P2 — Actualizar preferencias existentes

- **Dado** `cliente-A` con preferencias consultables y una nueva terna de valores
  sintéticos, por ejemplo `Tarde (preferido)`, `Recepción principal` e
  `Ingreso por puerta lateral`.
- **Cuando** un usuario autorizado envía los tres campos en la actualización
  propuesta.
- **Entonces** una lectura posterior de `cliente-A` refleja los nuevos valores
  y conserva el vínculo al mismo Cliente.

P4a–P4c concretan por separado el acuerdo de Frank sobre la semántica PATCH,
pendiente de revisión de Antony y Julio. Las rutas y la implementación de la
operación parcial siguen siendo propuestas.

### P3 — Valor que excede capacidad documentada

- **Dado** un Cliente existente y un valor sintético de longitud 121 para
  `horario_preferido`, o 256 para `referencia` o `restriccion_acceso`.
- **Cuando** un usuario autorizado intenta guardarlo.
- **Entonces** el sistema rechaza la entrada antes de persistirla, identifica el
  campo que excede el máximo técnico y mantiene intactos los valores previos.

**Base verificable:** límites físicos de las columnas existentes: 120, 255 y
255 caracteres. La validación anticipada por API, el rechazo de longitudes
excesivas con error por campo y la conservación de valores previos son
comportamientos propuestos, no reglas de negocio ya aprobadas.

### P5 — Cliente inexistente

- **Dado** el UUID sintético
  `00000000-0000-4000-8000-000000000099`, confirmado como inexistente.
- **Cuando** se intenta registrar o consultar preferencias asociadas a ese ID
  mediante el contrato futuro de Clientes.
- **Entonces** se informa que el Cliente no existe y no se crea una asociación
  ni se altera ningún Cliente existente.

**Contrato observado:** GET y PATCH de preferencias devuelven 404 cuando el
UUID objetivo no existe, sin crear clientes ni asociaciones; ST-028 lo
contrasta separadamente de la validación de Cliente en POST /pedidos.

### P6 — Asociación correcta y aislamiento

- **Dado** `cliente-A` y `cliente-B` con las preferencias iniciales de la tabla.
- **Cuando** un Operador autorizado cambia solo las preferencias de
  `cliente-A`.
- **Entonces** la consulta de `cliente-A` refleja los valores nuevos, la de
  `cliente-B` conserva exactamente `Tarde (preferido)`, `Recepción principal`
  y `Avisar al llegar`, y ningún valor queda asociado al otro cliente.

**Observables:** ambas lecturas mantienen su `cliente_id`; solo cambian las
columnas del cliente objetivo. La forma de detectar errores de concurrencia o
aislamiento requiere definir el contrato de persistencia/API.

### P7 — Permisos backend y presentación visual

- **Dado** un usuario autenticado con rol Administrador u Operador, autorizado
  sobre el Cliente `cliente-A` conforme al acuerdo de Frank pendiente de
  ratificación.
- **Cuando** consulta o actualiza preferencias a través del endpoint candidato.
- **Entonces** el backend permite la operación autorizada y devuelve o persiste
  solo los campos de preferencias de `cliente-A`.
- **Y** si un usuario sin permiso invoca directamente el mismo endpoint, el
  backend deniega la operación y no modifica datos ni revela preferencias.
- **Y** una sesión con rol Conductor, Analista o Auditor recibe denegación para
  esta proyección dentro del alcance candidato de ECL-52.

La matriz global RBAC orienta los permisos, pero este escenario no compromete
automáticamente todas sus capacidades ni operaciones como parte de ECL-52.
La limitación a Administrador/Operador es un acuerdo de Frank para revisión,
pendiente de ratificación de Antony/Julio.

**Control visual separado:** el frontend muestra las acciones permitidas como
ayuda de uso, pero la prueba debe invocar también el backend directamente con
sesión/rol y contexto; ocultar un botón no es autorización. Los alcances por
campo, en especial referencia/restricción de acceso, requieren acuerdo. No se
omite la verificación de servidor: existen endpoints GET/PATCH probados en
ST-026 y ST-028.

### P8 — Proponer preferencias al crear un pedido

- **Dado** `cliente-A` con `Mañana (preferido)`, `Puerta junto al parque` e
  `Ingreso por puerta lateral`.
- **Cuando** el Operador crea un pedido para `cliente-A`.
- **Entonces** el formulario presenta `Mañana (preferido)` y
  `Ingreso por puerta lateral` como información identificada como preferencia
  del Cliente, sin convertirlos ni copiarlos a los campos del Pedido.
- **Y** junto a `Puerta junto al parque` ofrece una acción explícita para
  copiarla al campo `referencia` del Pedido.
- **Y** si el Operador no selecciona esa acción, conserva sin cambios la
  referencia, `ventana_inicio` y `ventana_fin` que haya ingresado para el
  Pedido.
- **Y** si la selecciona, muestra `Puerta junto al parque` en el campo
  `referencia` del Pedido antes de guardar; el Operador puede editar el valor y
  confirmar el Pedido sin que cambie `cliente-A`.

**Contrato existente:** el `POST /pedidos` recibe `ventana_inicio`,
`ventana_fin` y `referencia` propios del pedido; no lee las preferencias del
Cliente. El formulario implementa la consulta y la
acción explícita de copia; P8 fue reprobado el 13/10 según ST-028. La API de
Pedido mantiene esa separación y no copia automáticamente preferencias.

## Decisiones pendientes y bloqueos

| Decisión | Alternativa recomendada (propuesta) | Fuente / justificación | Impacto en modelo/API/BDD | Confirman |
|---|---|---|---|---|
| Recurso y operaciones ECL-52 | GET/PATCH sobre Cliente existente, sin entidad nueva de preferencias. | Implementado y probado en ST-026/ST-028; modelo/migración 0006. | P1/P2/P5/P7. | Frank verificó; Julio ratifica mediante PR. |
| Actualización parcial y campos omitidos | Acuerdo de Frank para revisión: PATCH parcial; omitir conserva exactamente el valor persistido. | El esquema no define semántica de actualización; evita alterar campos no enviados. | Semántica de PATCH y P4a; posible concurrencia. | Frank acuerda; Antony/Julio revisan. |
| Significado de `null` | Acuerdo de Frank para revisión: `null` limpia el campo nullable y la lectura devuelve null. | Las columnas actuales permiten NULL; la limpieza debe ser explícita en PATCH. | Validación/esquema y P4b. | Frank acuerda; Antony/Julio revisan. |
| Texto vacío/espacios | Acuerdo de Frank para revisión: rechazar `""` y solo espacios, sin cambiar datos; conservar texto no vacío tal como fue enviado. | El esquema no define regla semántica; este comportamiento requiere validación de aplicación. | Validadores, error y P4c. | Frank acuerda; Antony/Julio revisan. |
| Límites técnicos | 120/255/255, con rechazo anticipado 121/256/256 y conservación de los valores anteriores. | Implementado en schemas y pruebas de ST-026/ST-028. | P3. | Frank verificó; Julio pendiente. |
| Horario y restricción al crear Pedido | Mostrar como información del Cliente; no convertir ni copiar al pedido. | `horario_preferido` es texto; RN-006 regula ventana del Pedido y no lo interpreta. | UI y P8; mantiene separados los campos. | Julio/Frank negocio; Giancarlo/José UX e interfaz; Antony integración. |
| Copia de referencia | Acción explícita “Usar como referencia del pedido”; rellena el campo separado del Pedido, editable antes de confirmar; nunca altera Cliente ni copia silenciosamente. | RF-005 pide proponer preferencias; modelo Pedido contiene `referencia` propia. | Formulario, propuesta de valores y P8; no implica cambiar POST automáticamente. | Julio/Frank; Giancarlo/José interacción; Antony integración. |
| Campos visibles por rol | Acuerdo de Frank para revisión: solo Administrador/Operador autorizados leen y actualizan; no exponer esta proyección a Conductor/Analista/Auditor dentro de ECL-52. | Matriz RBAC global orienta, pero no determina campos ni alcance de ECL-52. | Autorización backend y proyección; P7; control visual complementario. | Frank acuerda; Antony/Julio revisan; José/Giancarlo UI. |
| Asociación con Cliente y aislamiento | El ID del recurso identifica al Cliente; validar existencia y actualizar solo ese registro. | Cliente ya contiene las columnas; Pedido referencia Cliente por FK. | Resolver Cliente, 404 candidato y transacción; P5/P6. | Antony contrato; Julio/Frank aceptación. |

### P4 — Semántica acordada por Frank, pendiente de ratificación

Cada `Entonces` refleja el acuerdo de Frank registrado en esta conversación,
pendiente de ratificación de Antony y Julio. Los endpoints y respuestas API
siguen siendo propuestas.

#### P4a — Campo omitido conserva el valor

- **Dado** `cliente-A` con `horario_preferido: "Mañana (preferido)"` y los otros
  dos valores ya guardados.
- **Cuando** un Operador autorizado envía
  `PATCH {"referencia":"Entrada norte"}` sin incluir `horario_preferido` ni
  `restriccion_acceso`.
- **Entonces** la lectura posterior devuelve el mismo horario, la nueva
  referencia `"Entrada norte"` y la restricción previa sin cambios.
- **Y** ningún otro campo ni cliente cambia.

#### P4b — `null` limpia un campo

- **Dado** `cliente-A` con `restriccion_acceso: "Ingreso por puerta lateral"`.
- **Cuando** un Operador autorizado envía
  `PATCH {"restriccion_acceso":null}`.
- **Entonces** la actualización se acepta y la lectura posterior devuelve
  `restriccion_acceso: null`, conservando horario y referencia.

#### P4c — Vacío o espacios se rechazan sin cambios

- **Dado** `cliente-A` con `horario_preferido: "Mañana (preferido)"`.
- **Cuando** un Operador autorizado intenta, en solicitudes separadas,
  `PATCH {"horario_preferido":""}` y
  `PATCH {"horario_preferido":"   "}`.
- **Entonces** cada solicitud se rechaza como entrada inválida, identifica
  `horario_preferido` y la lectura posterior conserva exactamente el valor
  previo y los otros campos.

## Verificación contra lo implementado

Revisión estática de Frank al 25/10/2026 sobre `main` `dc148e7`. **Cubierto**
significa código y pruebas inspeccionados con validación histórica enlazada;
no es una ejecución nueva de las suites. **Diferencia** identifica una brecha
o precisión pendiente; **Sin prueba**, ausencia de un caso que la acredite.
No se modificaron archivos de evidencias ni se reejecutaron pruebas de producto.

Referencias: [BDD integrada](../../../backend/tests/integration/test_preferencias_bdd.py)
(`test_bdd_preferences_matrix`),
[HTTP real](../../../backend/tests/integration/test_preferencias_http_e2e.py),
[schemas](../../../backend/tests/unit/test_preferencias_schemas.py),
[servicio](../../../backend/tests/unit/test_preferencias_service.py),
[API](../../../backend/tests/unit/test_preferencias_api.py),
[UI de preferencias](../../../frontend/src/pages/DeliveryPreferencesPage.test.tsx),
[App/RBAC](../../../frontend/src/app/App.preferences.test.tsx),
[UI de pedidos](../../../frontend/src/pages/OrderCreatePage.test.tsx),
[componente de propuesta](../../../frontend/src/components/ClientPreferencesProposal.test.tsx),
[ST-026](<../../03 Implementación/Sprint 02/validaciones/VALIDACION_ST026.md>),
[ST-027](<../../03 Implementación/Sprint 02/validaciones/VALIDACION_ST027.md>) y
[ST-028](<../../03 Implementación/Sprint 02/validaciones/VALIDACION_ST028.md>).

| Escenario | Prueba o evidencia que lo cubre | Resultado |
|---|---|---|
| P1 — inicializar y consultar | BDD integrada, HTTP real `test_preferences_association_validation_and_order_preparation`; ST-028 M01; UI «representa preferencias vacías y permite inicializarlas». | Cubierto: misma terna, mismo cliente, sin entidad nueva. |
| P2 — actualizar terna | BDD integrada y HTTP real; ST-028 M02 y UI «envía solo cambios una vez y actualiza la base local después del ACK». | Cubierto: consulta posterior y vínculo conservado. |
| P3 — capacidad de columnas | BDD integrada (cada campo y borde); schemas `test_limits_nullable_and_omitted`, `test_bad_values_rejected`; ST-028 M03/M04. | Cubierto: 120/255/255 inclusive y 422 sin cambios para el siguiente carácter. |
| P4a — omitido conserva | BDD integrada, servicio `test_update_locks_and_commits_only_supplied_fields`; ST-028 M05; UI de preferencias. | Cubierto: modificación parcial y conservación de campos omitidos. |
| P4b — null limpia | BDD integrada y HTTP real; ST-028 M06; UI «limpia explícitamente con null sin alterar las demás preferencias». | Cubierto: solo limpia el campo explícito. |
| P4c — vacío/espacios | BDD integrada y schemas `test_bad_values_rejected`; ST-028 M07 y validación UI. | Cubierto: 422 por campo sin cambios persistidos. |
| P5 — cliente inexistente | BDD integrada y HTTP real; ST-028 M08; API `test_safe_service_errors`. | Cubierto: GET/PATCH 404 sin crear asociación. Se retira la afirmación histórica de endpoint inexistente. |
| P6 — asociación y aislamiento | BDD integrada comprueba ID, nombre y preferencias pobladas de A/B y número de filas; servicio `test_repository_targets_one_id_and_locks`; ST-028 M09. | Cubierto para aislamiento entre clientes. No acredita concurrencia de usuarios, fuera del escenario definido. |
| P7 — permisos y presentación | HTTP real `test_disallowed_roles_and_unauthenticated_cannot_read_or_change`; API `test_permissions_and_target_binding`; App/RBAC y ST-028 M10–M12. | Cubierto: Administrador/Operador y 403 para Conductor/Analista/Auditor en esta proyección; 401 sin sesión. |
| P8 — propuesta y copia explícita | UI de pedidos «ruta dorada: propone las preferencias y copia la referencia solo con la acción explícita» y «ruta feliz: sin la acción, no copia horario, restricción ni referencia al pedido (RN-006)»; componente de propuesta; ST-028 M17 y reprueba del 13/10. | Cubierto. D-01 era diferencia el 09/10; la reprueba del 13/10 acredita su corrección. No se abre un duplicado en backlog. |

### Diferencias y ratificación

La diferencia documental era afirmar que API/UI no existían y presentar P8
como trabajo futuro. Se actualiza ese estado y se conserva la trazabilidad a
ST-028, que separa el fallo inicial y su reprueba. No se debilitan escenarios
ni se modifican requisitos para hacer coincidir el documento con el código.

No se encontraron brechas funcionales abiertas en P1–P8 en las fuentes
inspeccionadas; esto no declara ausencia de todo defecto posible ni sustituye
CI o aprobación humana. La lectura restringida de preferencias no revoca la
matriz global ni crea nuevas proyecciones. Julio debe ratificar esta versión
y los acuerdos de omitido/null/vacío y copia explícita mediante revisión del PR.

## Condición para convertir el borrador en criterios ejecutables

Tras resolver las decisiones, fijar rutas/métodos y respuestas observables, y
ratificar o modificar las propuestas de rutas y uso en pedidos. Los acuerdos de
Frank sobre omitido/null/vacío y roles deben quedar revisados por Antony y Julio.
Los ejemplos sintéticos respetan las capacidades existentes; ninguna
validación semántica adicional queda aprobada por este borrador. No se declaran
pruebas ejecutadas.

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 0.2.0 | 25/10/2026 | Revisión ECL-71: verificación de P1–P8 y P4a/P4b/P4c contra pruebas y validaciones del Sprint 2; actualización del estado histórico y de la corrección de D-01. Ratificación de Julio pendiente. |
| 1.0.0 | 26/10/2026 | Ratificación documental de Julio en el PR #64: «Ratifico ECL-47 y ECL-51 según esta verificación». Se conserva la verificación y la trazabilidad a las validaciones del Sprint 2. |

La ratificación se registra por el contenido explícito del comentario de Julio.
GitHub registra esa revisión como COMMENTED, no como APPROVED; la aprobación
formal del PR y la revisión del nuevo commit siguen siendo requisitos previos
al merge. No se atribuye aprobación previa a la implementación ni pruebas nuevas.

[↑ Índice del Sprint 3](<../../03 Implementación/Sprint 03/README.md>)

[← Volver al README principal](../../../README.md)
