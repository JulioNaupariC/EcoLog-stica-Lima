# ECL-47 / ST-021 — Reglas y BDD de conductores

> **Estado: BORRADOR.** Pendiente de acuerdo del equipo y aprobación. Estos
> escenarios especifican comportamiento deseado; no acreditan implementación
> ni ejecución de pruebas.

## Trazabilidad y alcance

| Campo | Referencia |
|---|---|
| Subtarea | ECL-47 / ST-021 — Definir reglas de negocio y casos BDD de conductores |
| Historia padre | ECL-9 / US-003 — Gestionar conductores y disponibilidad |
| Requisitos | RF-003; RN-005 |
| Sprint | Sprint 2, según el contenido de Jira proporcionado por el analista |
| Evidencia Jira | Descripción, criterios de aceptación y padre compartidos por el analista; Jira no está conectado en esta sesión |
| Trabajo excluido | Implementación de modelo/API/interfaz y validación posterior; este documento no declara ninguna terminada |

Este archivo es un artefacto BDD separado para ST-021. No modifica los requisitos
ni las reglas de línea base.

## Fuentes consultadas

- [RF-003 — Requisitos funcionales](../../01%20Inicio/06.%20Requisitos%20funcionales%20V_1_0_0.md)
- [RN-002 y RN-005 — Reglas de negocio](../../01%20Inicio/09.%20Reglas%20de%20negocio%20V_1_0_0.md)
- [Perfiles y matriz RBAC](../../01%20Inicio/08.%20Usuarios%20V_1_0_0.md)
- [Modelo lógico de datos](../../01%20Inicio/11.%20Base%20de%20datos%20V_1_0_0.md)
- [Requisitos no funcionales, incluidos RNF-003/RNF-004](../../01%20Inicio/07.%20Requisitos%20no%20funcionales%20V_1_1_0.md)
- [Definition of Done](../01%20Transformando%20a%20%C3%A1gil%20V_1_0_0.md#8-definition-of-done-dod-global)
- `backend/app/core/rbac.py`, `backend/app/api/dependencies.py` y
  `backend/app/services/autenticacion.py`, `backend/app/models/usuario.py` y
  `backend/app/services/credenciales.py` y `backend/README.md` en la base
  `origin/main` `099838bdec64c16c4ecaee04644f2f69ec2c46dc`.

La subtarea Jira, según el contenido aportado, pide escenarios de registro,
actualización de disponibilidad, DNI duplicado y licencia vencida. No se
dispone de acceso a Jira para validar otros campos, comentarios o acuerdos.

## Estado actual observado en la base

El modelo lógico documental incluye `usuario_id`, DNI, licencia,
`experiencia_anios`, teléfono, `disponible_desde/hasta` y punto de partida.
No determina cardinalidad o nulabilidad del vínculo ni define las validaciones
de esos campos. En el código de `origin/main` revisado para este borrador no se
encontraron modelo ORM, migración, repositorio, endpoint ni formulario de
conductores. RBAC sí contiene permisos estáticos y alcances que servirían de
contrato a módulos futuros; no implementa por sí mismo esos recursos ni sus
proyecciones.

## Reglas confirmadas

| ID | Regla respaldada | Consecuencia para los BDD |
|---|---|---|
| RF-003 | Registrar y mantener conductores con nombre, DNI, licencia, experiencia, disponibilidad, contacto y punto de partida. | Los campos están identificados. Las reglas concretas de obligatoriedad, formato y límites de este borrador son propuestas y no quedan aprobadas por RF-003. |
| RN-005 | Una ruta no puede exceder ocho horas de conducción ni cuatro horas continuas sin un descanso de una hora. | Es una restricción de factibilidad de ruta/asignación, no una validación que se satisfaga al guardar disponibilidad. |
| RN-002 | La autorización depende del rol y, para conductores, de la ruta y jornada asignadas cuando corresponda. | La lectura de conductor propio y el acceso a recursos asignados requieren autorización de servidor y contexto confiable. |
| Matriz de usuarios | Administrador: CRUD de conductores; Operador: CRU; Conductor: lectura propia; Analista: lectura agregada; Auditor: lectura anonimizada. | Es la matriz global de referencia, no una ampliación automática de las operaciones comprometidas en ECL-48. Las operaciones y permisos efectivos del endpoint deben concretarse en su contrato. |
| RNF-004 | DNI/contacto de Conductor ajeno y datos personales identificables del Auditor no deben exponerse. | Denegar la consulta de objeto ajeno al Conductor; la lectura autorizada del Auditor debe excluir DNI/contacto identificables. |
| RN-015 | No se permite eliminación física de datos operativos desde la aplicación; se aplica desactivación lógica y auditoría. | Los casos de baja no deben borrar físicamente el conductor. |

### Ambigüedad de la línea base sobre licencia vencida

Los criterios BDD de RF-003 mencionan DNI duplicado **o** licencia vencida al
intentar guardar, pero el criterio de US-003 dice que la licencia vencida
impide habilitar la asignación. Acuerdo de Frank para revisión: permitir guardar
el perfil aunque la licencia esté vencida y marcarlo no asignable hasta que se
renueve. Esto no modifica la línea base; RF-003 requiere aclaración mediante el
proceso de control de cambios. El escenario de guardado vencido queda incluido
abajo para que Antony y Julio revisen esta interpretación.

## Contrato candidato para revisión — no aprobado

Los valores y operaciones siguientes permiten revisar escenarios concretos. Son
una propuesta para ECL-46/ECL-48, no un contrato aprobado ni una afirmación de
que el código exista.

### Modelo y campos propuestos

| Campo | Alternativa propuesta para acordar |
|---|---|
| Cuenta | Acuerdo de Frank, pendiente de revisión de Antony/Julio: todo conductor tiene exactamente una cuenta `USUARIO` con rol `CONDUCTOR`; `conductor.usuario_id` es obligatorio y único. La cuenta del Administrador/Operador que registra es distinta de la nueva cuenta CONDUCTOR (`actor.usuario_id != conductor.usuario_id`). Un usuario no se vincula a más de un conductor. Alta de la cuenta objetivo y del conductor es atómica; el actor autorizado no se convierte ni se vincula como conductor. |
| Credenciales | **Pendiente, bloquea el contrato final de alta:** acordar cómo se establece la credencial de la cuenta nueva (p. ej., contraseña inicial o flujo de invitación/activación). El modelo exige `password_hash` y el servicio interno de credenciales recibe contraseña y rol; no se encontró un endpoint de alta de usuarios. No aceptar ni exponer hashes directamente. |
| `nombre` | Obligatorio; recortar espacios exteriores; entre 1 y 160 caracteres. |
| `dni` | Obligatorio; exactamente 8 dígitos ASCII; unicidad global tras eliminar espacios exteriores; conservar como texto para no perder ceros iniciales. No devolverlo salvo a roles explícitamente autorizados. |
| `licencia_numero` | Obligatorio; texto de 1 a 20 caracteres; recortar espacios exteriores y normalizar letras a mayúsculas; aceptar letras ASCII, dígitos y guion. Confirmar el patrón con el responsable de dominio antes de imponerlo. |
| `licencia_vigente_hasta` | Obligatorio; fecha calendario ISO `YYYY-MM-DD`, sin hora. La licencia es válida hasta el final de esa fecha en `America/Lima`. |
| `experiencia_anios` | Obligatorio; entero no negativo. No proponer máximo de negocio hasta que se confirme; el tipo de almacenamiento debe soportar el valor permitido. |
| `contacto` | Obligatorio; teléfono normalizado a E.164, 8–15 dígitos después de `+`; aceptar prefijo internacional y no inferir un prefijo cuando falte. |
| `punto_partida` | Obligatorio; texto de 1–255 caracteres tras recortar espacios exteriores. Este borrador no presupone geocodificación ni coordenadas. |
| Disponibilidad | Propuesta: se exige un intervalo completo al registrar y para que el conductor sea asignable. En una actualización se puede limpiar enviando ambos extremos como `null`; el perfil permanece, pero queda sin disponibilidad y no asignable hasta guardar un nuevo intervalo. Los dos extremos deben ser ambos no nulos o ambos nulos; no se admite un intervalo parcial. Un único intervalo `[desde, hasta)`; ambos timestamps con offset/zona explícitos, normalizados a UTC al persistir y mostrados en `America/Lima`; `hasta` debe ser posterior a `desde`. Sin recurrencia en el primer contrato. |

Estos límites de campos son propuestas concretas y no derivan de constraints
actuales del modelo de conductor, que no está implementado en la base revisada.
La longitud de `nombre` y `punto_partida`, los formatos de DNI/licencia/teléfono
y la representación temporal requieren aprobación antes de codificarse.

### Operaciones y respuestas candidatas para ECL-48

| Operación propuesta | Acceso propuesto | Resultado HTTP y cuerpo candidato |
|---|---|---|
| `POST /conductores` | Propuesta: Administrador u Operador autenticado, distinto de la nueva cuenta CONDUCTOR. La API crea una cuenta CONDUCTOR distinta y la vincula atómicamente; no acepta que el actor autenticado se convierta en el conductor ni acepta un `usuario_id` arbitrario. La forma de provisionar su credencial queda pendiente. | `201`; cuerpo de respuesta candidato: `conductor_id`, `usuario_id`, `nombre`, disponibilidad y `habilitado_asignacion`. No incluye DNI, licencia ni contacto en la respuesta de creación. |
| `GET /conductores/{conductor_id}` | Acuerdo de Frank para revisión: Administrador/Operador; Conductor solo si el ID corresponde a su vínculo. | `200`; el contrato enumera campos por rol. Conductor propio recibe solo campos aprobados para su uso; consulta ajena responde `403` genérico, sin cuerpo del conductor. |
| `GET /conductores` paginado | Propuesta para ECL-48, solicitada para habilitar ST-023: Administrador/Operador. Sin acceso de listado para Conductor, Analista o Auditor en este contrato mínimo. | Candidato: `page` desde 1 y `page_size` de 1 a 100; orden estable por `conductor_id` ascendente; respuesta de página con `conductor_id`, `nombre`, disponibilidad y `habilitado_asignacion`. No incluir DNI, número de licencia ni contacto. Estos parámetros, campos y límites son propuestas, no contrato existente. |
| `PATCH /conductores/{conductor_id}` | Acuerdo de Frank para revisión: Administrador/Operador. Conductor no actualiza su perfil en esta propuesta. | `200`; recurso actualizado con la misma proyección autorizada. Omitidos conservan valor; entrada inválida devuelve `422` y no modifica el recurso. |
| Desactivación/baja | No incluido en la propuesta de operaciones de ECL-48 aquí descrita. | Requiere alcance y contrato separados. No inferir `DELETE` de la matriz global. |
| Consulta de Auditor | No incluir detalle individual en la API mínima. Si se requiere, proponer una extensión de resumen agregado sin IDs, DNI, contacto ni texto libre. | Extensión pendiente; no es respuesta implementada ni operación comprometida. Enmascarar parcialmente identificadores no basta para anonimizar. |

Las rutas, status, cuerpos, campos y parámetros anteriores son propuestas para
revisión de Antony y Julio, no un contrato implementado o aprobado. El acuerdo
de alcance de Frank incorpora un listado paginado como dependencia de trabajo
de ST-023, sujeto a contrastar con Jira. No se fijan mensajes que puedan
revelar datos personales.

## Escenarios BDD — borrador

Los siguientes ejemplos son sintéticos y ejercitan el contrato candidato
anterior. Los formatos y límites utilizados siguen siendo propuestas
pendientes de aprobación.

### D1 — Registro aceptado con datos válidos

- **Dado** el usuario `admin.frank@example.test`, autenticado con rol
  Administrador, y una cuenta de destino nueva
  `conductor.rosa@example.test`, distinta del Administrador y aún sin conductor
  vinculado.
- **Y** el Administrador registra para esa cuenta distinta la entrada
  propuesta: nombre `Rosa Milagros Quispe Soto`, DNI
  `45678912`, licencia `Q45678912`, vigente hasta `2026-12-31`, experiencia
  `6`, contacto `+51987654321`, punto de partida `Av. Los Jardines 123, SJL`,
  disponibilidad desde `2026-10-09T07:00:00-05:00` hasta
  `2026-10-09T16:00:00-05:00`.
- **Cuando** envía `POST /conductores`.
- **Entonces** la API responde `201`, crea el conductor y lo vincula una sola
  vez a `conductor.rosa@example.test`, no al usuario
  `admin.frank@example.test`, aplica las normalizaciones del contrato si se
  aprueban y devuelve `conductor_id`, `usuario_id`, `nombre`, disponibilidad y
  `habilitado_asignacion: true`.
- **Y** el cuerpo no incluye DNI, licencia ni contacto.

El resultado esperado depende de aprobar los campos/formatos candidatos y la
semántica de cuenta/licencia. La distinción entre actor y cuenta objetivo
también es parte de la propuesta de vínculo y debe confirmarse. Los IDs de
respuesta son valores generados, no literales del fixture. La solicitud
ejecutable y el alta atómica también dependen de acordar el aprovisionamiento
seguro de credenciales; no se prescribe una contraseña en este escenario.

### D2 — DNI duplicado

- **Dado** que ya existe el conductor de prueba con DNI `45678912`.
- **Y** un Operador autorizado intenta registrar
  `Rosa Quispe Soto`, asociando una cuenta CONDUCTOR distinta y enviando el mismo
  DNI `45678912`.
- **Cuando** envía `POST /conductores`.
- **Entonces** la API responde `409` con un error genérico de DNI duplicado, no
  incluye el valor del DNI en el cuerpo, no crea conductor ni vínculo parcial
  y el registro previo permanece idéntico.

Este caso adopta provisionalmente la unicidad global mencionada en el detalle
de ECL-46 compartido por el analista y el formato propuesto de ocho dígitos.
Ambos requieren aprobación.

### D3 — Licencia vencida bloquea asignación

- **Dado** un conductor guardado con licencia vigente hasta `2026-10-08`.
- **Y** una ruta cuya primera conducción está prevista para
  `2026-10-09T08:00:00-05:00`.
- **Cuando** el motor consulta la elegibilidad para asignar la ruta en esa fecha
  local de `America/Lima`.
- **Entonces** no asigna la ruta, porque la licencia dejó de ser válida al
  terminar el día `2026-10-08` en Lima, e informa una causa de licencia vencida
  sin devolver el número de licencia.

**Caso límite propuesto:** para una licencia vigente hasta `2026-10-08`, la
asignación con conducción prevista el `2026-10-08` es elegible respecto de la
licencia, pero una conducción prevista desde `2026-10-09T00:00:00-05:00` no lo
es. El motor evalúa toda la conducción de la ruta contra el instante de fin de
vigencia, no solo la fecha en que se crea el registro.

### D3a — Guardar perfil con licencia vencida

- **Dado** el Administrador autenticado `admin.frank@example.test` y una cuenta
  CONDUCTOR nueva distinta `conductor.rosa@example.test`.
- **Y** la solicitud de alta incluye `licencia_vigente_hasta: "2026-10-07"`
  y los demás campos sintéticos válidos del escenario D1.
- **Cuando** el Administrador envía `POST /conductores` el `2026-10-08`.
- **Entonces** la API acepta y persiste el perfil con el vínculo a la cuenta
  CONDUCTOR distinta, y la respuesta propuesta indica
  `habilitado_asignacion: false`.
- **Y** no se devuelve el número de licencia ni se rechaza el guardado solo por
  su vencimiento.

El resultado de negocio refleja el acuerdo de Frank pendiente de revisión de
Antony/Julio. `POST`, `201`, el campo de respuesta y las validaciones son
propuestas de contrato; RF-003 conserva su texto vigente hasta un cambio
aprobado.

### D4 — Actualización de disponibilidad

- **Dado** un conductor existente cuya disponibilidad es
  `2026-10-09T07:00:00-05:00`–`2026-10-09T16:00:00-05:00`.
- **Y** un Operador autorizado que propone cambiarla a
  `2026-10-10T08:00:00-05:00`–`2026-10-10T17:00:00-05:00`.
- **Cuando** envía `PATCH /conductores/{conductor_id}` con ambos extremos.
- **Entonces** la API responde `200`; la consulta posterior devuelve el nuevo
  intervalo equivalente en UTC y la representación de interfaz lo muestra en
  `America/Lima`.
- **Y** nombre, usuario vinculado, DNI y los demás atributos no cambian.

**Caso inválido propuesto:** si el Operador envía inicio
`2026-10-10T17:00:00-05:00` y fin `2026-10-10T08:00:00-05:00`, la API responde
`422` y la disponibilidad previamente almacenada no cambia.

**Disponibilidad obligatoria y limpieza propuesta:** el requisito de intervalo
completo aplica al alta y a la elegibilidad para asignación, no obliga a que un
perfil ya registrado conserve siempre un intervalo. En PATCH, omitir ambos
campos conserva el intervalo; enviar solo uno devuelve `422`; enviar ambos como
`null` limpia la disponibilidad y conserva el perfil, pero deja al conductor
sin disponibilidad y no asignable hasta registrar un intervalo completo válido.
La limpieza no elimina ni desactiva al conductor. Estos comportamientos son
propuestas pendientes de ratificación.

### D5a — Creación inválida sin registro nuevo

- **Dado** que no existe un conductor con DNI `45678912` ni una cuenta
  `conductor.rosa@example.test`.
- **Y** el Operador autorizado envía el fixture de D1 con DNI `45A78912`.
- **Cuando** solicita `POST /conductores`.
- **Entonces** la API responde `422` e identifica `dni` como inválido sin
  repetir el valor enviado.
- **Y** no crea usuario ni conductor ni deja una relación parcial.

### D5b — Actualización inválida sin alterar el registro

- **Dado** un conductor con disponibilidad
  `2026-10-10T08:00:00-05:00`–`2026-10-10T17:00:00-05:00` y una instantánea
  guardada de todos sus campos.
- **Y** un Operador autorizado envía inicio
  `2026-10-10T17:00:00-05:00` y fin `2026-10-10T08:00:00-05:00`.
- **Cuando** envía `PATCH /conductores/{conductor_id}`.
- **Entonces** la API responde `422` con error de intervalo inválido y una
  lectura posterior coincide con la instantánea anterior en todos los campos.

### D6 — Autorización backend y controles visuales de operaciones propuestas

- **Dado** las operaciones candidatas `POST /conductores`,
  `GET /conductores`, `GET /conductores/{id}` y
  `PATCH /conductores/{id}`.
- **Cuando** Administrador u Operador invocan una de esas operaciones.
- **Entonces** el backend permite la operación dentro del alcance propuesto;
  una sesión ausente recibe `401` y un rol/contexto sin permiso recibe `403`
  sin cambios ni cuerpo de conductor.
- **Y** un Conductor solo puede consultar su propio ID y proyección; solicitar
  otro conductor o el listado recibe `403` sin información protegida.
- **Y** Analista y Auditor no reciben acceso individual ni al listado bajo
  esta propuesta mínima.

El alcance de estos roles/operaciones fue acordado por Frank para revisión de
Antony/Julio. Las rutas y status HTTP siguen siendo propuestas. La matriz global
RBAC no amplía automáticamente el alcance de ECL-48.

**Control visual separado:** la interfaz presenta u oculta/deshabilita acciones
según la experiencia de cada rol, pero alterar el cliente o invocar directamente
la API no concede acceso. La prueba de seguridad debe verificar autorización
real del backend, no solo la ausencia de botones.

**Alcance propuesto para confirmar:** POST, GET por ID, GET paginado y PATCH.
El listado paginado se propone para cubrir la dependencia de ST-023 indicada
por Frank; confirmar contra Jira. No se incluye desactivación. Al momento de
inspección no existen endpoints de conductores en la base consultada.

### D7 — Conductor intenta consultar un conductor ajeno

- **Dado** un Conductor autenticado cuyo `usuario_id` está vinculado al
  conductor `C-100`, mientras `C-200` está vinculado a otra cuenta.
- **Cuando** solicita `GET /conductores/C-200` desde la interfaz o directamente
  al backend.
- **Entonces** la API responde `403` con `{"detail":"Acceso denegado"}`, sin
  incluir ID, DNI, contacto ni otro campo de `C-200`.
- **Y** la interfaz muestra el mismo mensaje genérico sin renderizar una
  respuesta protegida.

`403` y el texto del ejemplo son propuestas para revisión; la denegación de
backend no puede sustituirse por ocultar el control visual.

### D8 — Consulta de Auditor sin datos identificables (extensión propuesta)

- **Dado** un Auditor autenticado y una extensión de consulta agregada aprobada
  fuera del alcance mínimo propuesto para ECL-48.
- **Cuando** solicita el resumen de conductores autorizado.
- **Entonces** la respuesta contiene solo conteos agregados y no incluye
  `conductor_id`, `usuario_id`, nombre, DNI, licencia identificable, contacto,
  punto de partida ni texto libre.

No se considera anonimizada una respuesta que solo enmascara parcialmente DNI o
contacto mientras conserva información que permita identificar a la persona.
Este resumen no es endpoint existente ni se agrega automáticamente a ECL-48.

### D9 — Listado paginado para ST-023 (operación propuesta)

- **Dado** tres conductores existentes con IDs ordenables `C-100`, `C-200` y
  `C-300`, y un Administrador autorizado.
- **Cuando** solicita `GET /conductores?page=1&page_size=2` y luego
  `GET /conductores?page=2&page_size=2`.
- **Entonces** la primera respuesta contiene `C-100` y `C-200`, y la segunda
  contiene `C-300`; ambas incluyen metadatos `page`, `page_size` y `total: 3`.
- **Y** cada elemento contiene `conductor_id`, `nombre`, disponibilidad y
  `habilitado_asignacion`, pero no DNI, número de licencia ni contacto.
- **Y** una cuenta Conductor no autorizada al listado recibe `403` sin datos.

La forma de paginación, los nombres/valores de parámetros, el orden estable y la
proyección son propuestas API que ECL-48 debe confirmar. El listado se incluye
en este borrador para habilitar ST-023 según la relación comunicada por Frank;
la dependencia Jira no se pudo consultar directamente.

## Escenarios RN-005 de ST-021; implementación futura fuera del CRUD

ST-021 documenta estos escenarios de RN-005 para orientar el requisito y el
trabajo posterior. Su implementación y ejecución corresponden al futuro motor
de asignación/planificación, no al CRUD de conductores. Registrar una franja
disponible no demuestra que se cumplan. La fórmula para medir conducción
continua, pausas y bordes debe acordarse antes de automatizarlos.

### F1 — Límite de ocho horas de conducción

- **Dado** dos rutas candidatas cuya conducción total calculada por ruta es
  `8 h` para `ruta-A` y `8 h 1 min` para `ruta-B`, suponiendo que las demás
  restricciones se satisfacen.
- **Cuando** el motor evalúa por separado la factibilidad de cada ruta.
- **Entonces** no rechaza `ruta-A` por exceder el límite total, porque alcanza
  exactamente `8 h`.
- **Y** no asigna `ruta-B` a ese conductor e informa que esa ruta excede el
  límite de ocho horas.

### F2 — Descanso tras cuatro horas continuas

- **Dado** un conductor que, en una ruta candidata, lleva `3 h 59 min` de
  conducción continua sin descanso.
- **Cuando** una parada añade `1 min` de conducción y la siguiente añade
  `1 min` más sin descanso intermedio.
- **Entonces** el motor no considera factible el tramo que reanuda conducción
  después de alcanzar `4 h` continuas hasta insertar un descanso de `1 h`.
- **Y** el descanso de exactamente `1 h` satisface la duración mínima
  documentada y permite volver a evaluar el tramo siguiente.

El cómputo se refiere a la conducción de cada ruta evaluada, no a disponibilidad
ni a una suma de rutas distintas. La forma de contar inicio/fin de conducción y
descanso, y cómo insertar la pausa en una ruta, deben definirse en el contrato
del motor. Estos son escenarios BDD de ST-021; implementación y ejecución
siguen fuera del CRUD.

## Decisiones pendientes y bloqueos

| Decisión | Propuesta para revisar | Fuente / justificación | Impacto | Confirman |
|---|---|---|---|---|
| Vínculo Conductor–Usuario | Acuerdo de Frank para revisión: uno-a-uno obligatorio; la cuenta CONDUCTOR es distinta del Administrador/Operador que registra; crear cuenta y perfil atómicamente. | El modelo lógico nombra `usuario_id` pero no cardinalidad ni actor creador; separación explícita de actor y usuario sujeto. | FK unique/not null, transacción de alta y asociación autenticada; la creación de cuenta sigue siendo propuesta API. | Frank acuerda; Antony/Julio revisan antes de cerrar. |
| Provisión de credenciales | Pendiente: acordar contraseña inicial o invitación/activación antes de fijar el cuerpo de alta. No aceptar hashes suministrados por el cliente. | `Usuario.password_hash` es obligatorio; `CredentialService.create` recibe email/contraseña/rol y hashea internamente; el README indica que no se crean usuarios automáticamente. | Bloquea el esquema de entrada y la transacción completa de `POST /conductores`; no cambiar la cuenta autenticada por la cuenta del conductor. | Frank, Antony y Julio; Antony define factibilidad y seguridad. |
| Campos obligatorios, formatos y límites | Nombre 1–160; DNI obligatorio de 8 dígitos único; licencia obligatoria 1–20 alfanumérico/guion; experiencia entero ≥0; contacto obligatorio E.164; punto de partida texto 1–255. | RF-003 solo enumera campos; formatos y límites no están aprobados en los requisitos. | Esquema, validadores y errores 409/422; fixtures D1/D2/D5. | Julio y Frank por dominio; Antony por factibilidad. |
| Disponibilidad | Propuesta: intervalo completo al alta y para asignar; omitir ambos extremos en PATCH conserva; ambos `null` limpia el intervalo y mantiene el perfil no asignable; un solo extremo es inválido. | El modelo lógico sugiere `disponible_desde/hasta`; no define nulabilidad o actualización. | Constraints, validación de alta/PATCH y elegibilidad; D1/D4/D5b. | Frank propone; Antony/Julio revisan. |
| Licencia vencida al guardar | Acuerdo de Frank para revisión: guardar perfil vencido y marcarlo no asignable; vigencia durante el día de vencimiento en Lima, asignación desde el siguiente día local impedida. | US-003 impide habilitar asignación; BDD de RF-003 parece rechazar guardado. La línea base requiere aclaración, no se cambia aquí. | Validación de alta, campo de respuesta y motor futuro; D3/D3a. | Frank acuerda; Antony/Julio revisan y aclaran RF-003. |
| Permisos | Acuerdo de Frank para revisión: Administrador/Operador POST/GET listado/GET por ID/PATCH; Conductor solo GET propio; otros roles sin listado ni detalle individual. | Referencia a la matriz RBAC global, acotada a las operaciones candidatas de ECL-48. | Autorización, proyecciones, pruebas; D6/D7. | Frank acuerda; Antony/Julio revisan. |
| Listado y dependencia ST-023 | Propuesta para ECL-48: GET paginado, para habilitar ST-023; no listado para Conductor/Analista/Auditor; campos no sensibles en el resumen. | Relación de dependencia indicada por Frank; Jira no está conectado y la relación debe comprobarse allí. | Ruta/contrato de paginación y proyección; D6 y trabajo dependiente ST-023. | Frank propone; Antony/Julio validan Jira y API. |
| Proyección de Auditor | Si se necesita lectura, extensión separada de resumen agregado sin IDs, DNI, contacto ni texto libre; no usar masking parcial como anonimización. | RNF-004 y matriz de lectura anonimizada; riesgo de reidentificación. | Fuera del ECL-48 mínimo; D8 sujeto a aprobación y revisión de privacidad. | Julio y Frank; Antony por factibilidad. |
| RN-005 | Evaluar límite total y conducción continua por ruta; los umbrales exactos siguen siendo los de RN-005. | Límites expresos de RN-005. | Contrato y pruebas del motor futuro; no agrega lógica al CRUD. | Antony por motor; Julio/Frank por interpretación. |

## Condición para convertir el borrador en criterios ejecutables

Las entradas, respuestas y formatos de los escenarios son ejemplos concretos de
una propuesta para revisión, no un acuerdo. Tras la decisión de Julio, Antony y
Frank, conservar, ajustar o retirar cada regla candidata y alinear los BDD con
el contrato aprobado. Cualquier cambio a RF-003/RN-005 debe tramitarse mediante
control de cambios; este documento no declara pruebas ejecutadas.
