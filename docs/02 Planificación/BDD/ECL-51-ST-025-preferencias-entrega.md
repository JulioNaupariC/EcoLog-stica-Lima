# ECL-51 / ST-025 — Reglas y BDD de preferencias de entrega

> **Estado: BORRADOR.** Pendiente de acuerdo del equipo y aprobación. Estos
> escenarios especifican comportamiento deseado; no acreditan implementación
> ni ejecución de pruebas.

## Trazabilidad y alcance

| Campo | Referencia |
|---|---|
| Subtarea | ECL-51 / ST-025 — Definir reglas y casos BDD de preferencias de entrega |
| Historia padre | ECL-11 / US-005 — Gestionar preferencias de entrega de clientes |
| Requisitos | RF-005; RN-006 |
| Sprint | Sprint 2, según el contenido de Jira proporcionado por el analista |
| Evidencia Jira | Descripción, criterios de aceptación y padre compartidos por el analista; Jira no está conectado en esta sesión |
| Trabajo excluido | Implementación de API/formulario y validación posterior ECL-54 / ST-028 |

Este archivo es un artefacto BDD separado para ST-025. No modifica requisitos de
línea base ni propone una entidad de preferencias adicional.

## Fuentes consultadas

- [RF-005 — Requisitos funcionales](../../01%20Inicio/06.%20Requisitos%20funcionales%20V_1_0_0.md)
- [RN-002 y RN-006 — Reglas de negocio](../../01%20Inicio/09.%20Reglas%20de%20negocio%20V_1_0_0.md)
- [Perfiles y matriz RBAC](../../01%20Inicio/08.%20Usuarios%20V_1_0_0.md)
- [Modelo lógico de datos](../../01%20Inicio/11.%20Base%20de%20datos%20V_1_0_0.md)
- [Requisitos no funcionales](../../01%20Inicio/07.%20Requisitos%20no%20funcionales%20V_1_1_0.md)
- [Definition of Done](../01%20Transformando%20a%20%C3%A1gil%20V_1_0_0.md#8-definition-of-done-dod-global)
- `backend/app/models/cliente.py`, `backend/app/models/pedido.py`,
  `backend/alembic/versions/0006_create_cliente_pedido.py`,
  `backend/app/api/pedidos.py`, `backend/app/schemas/pedido.py` y
  `backend/app/services/pedidos.py` en la base `origin/main`
  `099838bdec64c16c4ecaee04644f2f69ec2c46dc`.

La subtarea Jira, según el contenido aportado, solicita horarios preferidos,
referencias de ubicación y restricciones de acceso por cliente; el criterio
requiere casos de preferencias válidas, inválidas y actualización. No se dispone
de acceso a Jira para inspeccionar comentarios u otros acuerdos.

## Estado actual observado en la base

Cliente ya contiene los campos `horario_preferido`, `referencia` y
`restriccion_acceso`. La migración 0006 los crea como `VARCHAR(120)`,
`VARCHAR(255)` y `VARCHAR(255)`, respectivamente, y los permite nulos. El modelo
no contiene validaciones adicionales de contenido para estos campos. Se
reutilizan estos campos existentes; no se propone una tabla nueva.

Pedido referencia Cliente mediante FK. El `POST /pedidos` actual comprueba que
el cliente exista, recibe `referencia` y la ventana de pedido, pero no lee ni
propone automáticamente las preferencias almacenadas en Cliente. No se
encontraron endpoints de gestión/consulta de Cliente. En consecuencia, los casos
de preferencias y su propuesta en el formulario describen comportamiento
futuro, no funcionalidades ya disponibles.

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
  sin Cliente existente; estas rutas aún no existen.
- Acuerdo de Frank para revisión: en PATCH, campo omitido conserva su valor;
  `null` limpia el campo nullable; `""` y texto compuesto solo por espacios se
  rechazan sin cambios. Las cadenas con espacios alrededor se preservan tal como
  fueron enviadas; no se recortan ni normalizan silenciosamente. Antony y Julio
  deben revisar este acuerdo antes de cerrar el contrato.
- El esquema actual permite como máximo 120 caracteres para
  `horario_preferido` y 255 para `referencia` y `restriccion_acceso`. Propuesta
  pendiente para la API: validar esos límites antes de persistir y devolver un
  error por campo sin alterar valores existentes. Los tamaños del esquema son
  hechos observados; el comportamiento de validación HTTP no está implementado
  ni aprobado.
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

Los endpoints y su contrato permanecen propuestos, no implementados. La
semántica de omitido/null/vacío y el alcance de permisos reflejan acuerdos de
Frank para revisión, pendientes de ratificación de Antony y Julio. Los tamaños
físicos son los del esquema existente; su validación anticipada por API es una
propuesta.

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

**Distinción del código actual:** `POST /pedidos` sí valida el cliente y
responde `404 Cliente no encontrado`; eso no equivale a un endpoint de
preferencias, que actualmente no se encontró.

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
han observado endpoints de Cliente en la base consultada.

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
Cliente. El comportamiento descrito arriba es una alternativa concreta
propuesta, no comportamiento actual.

## Decisiones pendientes y bloqueos

| Decisión | Alternativa recomendada (propuesta) | Fuente / justificación | Impacto en modelo/API/BDD | Confirman |
|---|---|---|---|---|
| Recurso y operaciones ECL-52 | Propuesta: reutilizar columnas de Cliente y ofrecer GET/PATCH sobre Cliente existente; no crear un recurso independiente ni asumir CRUD completo. | Modelo/migración 0006; la base consultada no tiene endpoints Cliente/preferencias. | Rutas, esquemas y permisos limitados; P1/P2/P5/P7. | Julio define alcance; Antony API/modelo; Frank trazabilidad. |
| Actualización parcial y campos omitidos | Acuerdo de Frank para revisión: PATCH parcial; omitir conserva exactamente el valor persistido. | El esquema no define semántica de actualización; evita alterar campos no enviados. | Semántica de PATCH y P4a; posible concurrencia. | Frank acuerda; Antony/Julio revisan. |
| Significado de `null` | Acuerdo de Frank para revisión: `null` limpia el campo nullable y la lectura devuelve null. | Las columnas actuales permiten NULL; la limpieza debe ser explícita en PATCH. | Validación/esquema y P4b. | Frank acuerda; Antony/Julio revisan. |
| Texto vacío/espacios | Acuerdo de Frank para revisión: rechazar `""` y solo espacios, sin cambiar datos; conservar texto no vacío tal como fue enviado. | El esquema no define regla semántica; este comportamiento requiere validación de aplicación. | Validadores, error y P4c. | Frank acuerda; Antony/Julio revisan. |
| Límites técnicos | Propuesta API: rechazar longitudes 121 para horario y 256 para referencia/restricción; error identifica campo y conserva valores previos. | Columnas actuales `VARCHAR(120/255/255)`; validación HTTP anticipada no está implementada. | Schema/API y P3. | Antony contrato técnico; Julio/Frank aceptación. |
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

## Trabajo futuro fuera de ST-025

ECL-54 / ST-028 — Validar preferencias y su asociación con clientes cuando estén
disponibles la API y el formulario — no se ejecuta ni se declara iniciada aquí.
La integración real debe comprobar después asociación correcta, aislamiento
entre clientes, permisos y uso en el flujo de pedido contra el contrato
aprobado.

## Condición para convertir el borrador en criterios ejecutables

Tras resolver las decisiones, fijar rutas/métodos y respuestas observables, y
ratificar o modificar las propuestas de rutas y uso en pedidos. Los acuerdos de
Frank sobre omitido/null/vacío y roles deben quedar revisados por Antony y Julio.
Los ejemplos sintéticos respetan las capacidades existentes; ninguna
validación semántica adicional queda aprobada por este borrador. No se declaran
pruebas ejecutadas.
