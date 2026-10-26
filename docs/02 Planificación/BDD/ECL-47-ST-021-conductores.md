# ECL-47 / ST-021 — Reglas y BDD de conductores

> **Estado: BORRADOR.** Revisión de Frank preparada para ratificación de Julio
> mediante el PR de ECL-71. No hay fecha de aprobación registrada. Las
> diferencias y extensiones pendientes no se declaran implementadas.

| Metadato | Valor |
|---|---|
| Versión | 0.2.0 |
| Fecha de revisión | 25/10/2026, America/Lima |
| Autor de la revisión | Frank Roy Yupanqui Acevedo — @FrankRoyYA |
| Ratificación de Julio | Pendiente; sin fecha ni aprobación atribuida |
| Ticket de ratificación | [ECL-71](https://continental-team-il84x39k.atlassian.net/browse/ECL-71) |
| Base contrastada | `main` en `dc148e7` |

## Trazabilidad y alcance

| Campo | Referencia |
|---|---|
| Subtarea | ECL-47 / ST-021 — Definir reglas de negocio y casos BDD de conductores |
| Historia padre | ECL-9 / US-003 — Gestionar conductores y disponibilidad |
| Requisitos | RF-003; RN-005 |
| Sprint | BDD del Sprint 2; ratificación en el Sprint 3 mediante ECL-71 |
| Evidencia Jira | ECL-71 y seguimientos ECL-79/ECL-80/ECL-81 consultados o creados durante esta revisión |
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
actualización de disponibilidad, DNI duplicado y licencia vencida. En ECL-71
se consultó Jira y se registraron los seguimientos ECL-79/ECL-80/ECL-81; no se
atribuyen acuerdos que no estén registrados.

## Estado observado y actualización ECL-71

El borrador inicial inspeccionó `099838b`, anterior al CRUD del Sprint 2. En
`main` `dc148e7` sí existen modelo, migración, repositorio, servicio, API y
formulario. La verificación de esta versión utiliza esos archivos y las
pruebas enlazadas abajo, junto con ST-022/ST-023/ST-024.

`habilitado_asignacion` es elegibilidad básica al consultar, no factibilidad de
una ruta futura. D3 y F1/F2 siguen sin implementación del motor. D8 es una
extensión condicional fuera del CRUD; se registra sin declararla disponible.

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

Los valores y operaciones siguientes se presentan para ratificación. La
verificación ECL-71 identifica cuáles están implementados y cuáles siguen
pendientes; esta revisión no equivale a un contrato aprobado por Julio.

### Modelo y campos propuestos

| Campo | Alternativa propuesta para acordar |
|---|---|
| Cuenta | Acuerdo de Frank, pendiente de revisión de Antony/Julio: todo conductor tiene exactamente una cuenta `USUARIO` con rol `CONDUCTOR`; `conductor.usuario_id` es obligatorio y único. La cuenta del Administrador/Operador que registra es distinta de la nueva cuenta CONDUCTOR (`actor.usuario_id != conductor.usuario_id`). Un usuario no se vincula a más de un conductor. Alta de la cuenta objetivo y del conductor es atómica; el actor autorizado no se convierte ni se vincula como conductor. |
| Credenciales | Implementado en ST-022 para ratificación: `email` obligatorio, formato básico y máximo 255 caracteres; `password` de solo escritura, de 1 a 1024 caracteres, sin recorte. El servidor genera hash Argon2id. Cuenta CONDUCTOR y perfil se crean en una transacción, separados del actor. No aceptar hash ni `usuario_id` del cliente. |
| `nombre` | Obligatorio; recortar espacios exteriores; entre 1 y 160 caracteres. |
| `dni` | Obligatorio; exactamente 8 dígitos ASCII; unicidad global tras eliminar espacios exteriores; conservar como texto para no perder ceros iniciales. No devolverlo salvo a roles explícitamente autorizados. |
| `licencia_numero` | Implementado: obligatorio, 1–20 caracteres tras recorte y normalización a mayúsculas. El patrón ASCII alfanumérico/guion del borrador no está implementado ni aprobado; ECL-81 debe ratificarlo o descartarlo, sin darlo por cubierto. |
| `licencia_vigente_hasta` | Obligatorio; fecha calendario ISO `YYYY-MM-DD`, sin hora. La licencia es válida hasta el final de esa fecha en `America/Lima`. |
| `experiencia_anios` | Entero no negativo, sin booleanos ni fracciones; máximo técnico 2147483647 de Integer de PostgreSQL, no máximo de negocio. |
| `telefono` | Nombre HTTP implementado del contacto: E.164 obligatorio, 8–15 dígitos tras `+`, primer dígito entre 1 y 9; no se infiere país. El borrador denominaba este campo `contacto`. |
| `punto_partida` | Obligatorio; texto de 1–255 caracteres tras recortar espacios exteriores. Este borrador no presupone geocodificación ni coordenadas. |
| Disponibilidad | Propuesta: se exige un intervalo completo al registrar y para que el conductor sea asignable. En una actualización se puede limpiar enviando ambos extremos como `null`; el perfil permanece, pero queda sin disponibilidad y no asignable hasta guardar un nuevo intervalo. Los dos extremos deben ser ambos no nulos o ambos nulos; no se admite un intervalo parcial. Un único intervalo `[desde, hasta)`; ambos timestamps con offset/zona explícitos, normalizados a UTC al persistir y mostrados en `America/Lima`; `hasta` debe ser posterior a `desde`. Sin recurrencia en el primer contrato. |

Los límites anteriores se contrastaron con el esquema implementado en ST-022.
La revisión no aprueba retroactivamente A4 ni modifica RF-003/RN-005. ECL-81
conserva las diferencias normativas pendientes sobre licencia.

### Operaciones y respuestas candidatas para ECL-48

| Operación propuesta | Acceso propuesto | Resultado HTTP y cuerpo candidato |
|---|---|---|
| `POST /conductores` | Administrador/Operador; alta atómica con email y contraseña inicial de una cuenta CONDUCTOR nueva e independiente. No admite `usuario_id` arbitrario. | `201`; `conductor_id`, `usuario_id`, `nombre`, disponibilidad, `estado` y `habilitado_asignacion`; sin DNI, licencia ni teléfono. |
| `GET /conductores/{conductor_id}` | Administrador/Operador: perfil de mantenimiento; Conductor: solo su vínculo real. | `200`; Administrador/Operador reciben ConductorResponse con los campos del perfil; Conductor propio recibe ConductorSummary con IDs, nombre, disponibilidad, estado y elegibilidad, sin DNI, licencia, teléfono ni punto de partida. Consulta ajena: `403` genérico. |
| `GET /conductores` paginado | Administrador/Operador. Conductor, Analista y Auditor no acceden a este listado individual. | `200`; `page` desde 1, `page_size` 1–100 (default 20), orden por `conductor_id` ascendente; items con ID, nombre, disponibilidad, estado y elegibilidad, sin DNI, licencia ni teléfono; metadatos page/page_size/total. |
| `PATCH /conductores/{conductor_id}` | Acuerdo de Frank para revisión: Administrador/Operador. Conductor no actualiza su perfil en esta propuesta. | `200`; recurso actualizado con la misma proyección autorizada. Omitidos conservan valor; entrada inválida devuelve `422` y no modifica el recurso. |
| Desactivación/baja | No incluido en la propuesta de operaciones de ECL-48 aquí descrita. | Requiere alcance y contrato separados. No inferir `DELETE` de la matriz global. |
| Consulta de Auditor | No incluir detalle individual en la API mínima. Si se requiere, proponer una extensión de resumen agregado sin IDs, DNI, contacto ni texto libre. | Extensión pendiente; no es respuesta implementada ni operación comprometida. Enmascarar parcialmente identificadores no basta para anonimizar. |

Las operaciones del CRUD anteriores están implementadas y documentadas en
ST-022, sujetas a ratificación de Julio en ECL-71. El listado habilita ST-023;
las extensiones indicadas como pendientes no quedan incluidas por esa razón.
Los errores no deben revelar datos personales.

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
- **Y** el reloj de prueba está fijo en `2026-10-09T08:00:00-05:00`; el
  email de destino y una contraseña inicial sintética se envían con los datos.
  El campo de contacto se envía como `telefono`.
- **Cuando** envía `POST /conductores`.
- **Entonces** la API responde `201`, crea el conductor y lo vincula una sola
  vez a `conductor.rosa@example.test`, no al usuario
  `admin.frank@example.test`, aplica las normalizaciones del contrato si se
  aprueban y devuelve `conductor_id`, `usuario_id`, `nombre`, disponibilidad y
  `habilitado_asignacion: true`.
- **Y** el cuerpo no incluye DNI, licencia ni contacto.

Los IDs de respuesta son generados. El alta con contraseña inicial está
documentada en ST-022 y contrastada con las pruebas de alta/login; no se
prescribe una credencial real ni se requiere un flujo nuevo de invitación.

### D2 — DNI duplicado

- **Dado** que ya existe el conductor de prueba con DNI `45678912`.
- **Y** un Operador autorizado intenta registrar
  `Rosa Quispe Soto`, asociando una cuenta CONDUCTOR distinta y enviando el mismo
  DNI `45678912`.
- **Cuando** envía `POST /conductores`.
- **Entonces** la API responde `409` con el error genérico `Identificador ya registrado`, no
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

El guardado está implementado y probado. La contradicción entre el texto de
RF-003 y US-003 sigue pendiente de decisión en ECL-81; RF-003 conserva su texto
vigente hasta un control de cambios aprobado.

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
El listado paginado está implementado y consumido por ST-023. No incluye
desactivación. Las pruebas de API acreditan autorización y proyecciones.

### D7 — Conductor intenta consultar un conductor ajeno

- **Dado** un Conductor autenticado cuyo `usuario_id` está vinculado al
  conductor `C-100`, mientras `C-200` está vinculado a otra cuenta.
- **Cuando** solicita `GET /conductores/C-200` desde la interfaz o directamente
  al backend.
- **Entonces** la API responde `403` con `{"detail":"Acceso denegado"}`, sin
  incluir ID, DNI, contacto ni otro campo de `C-200`.
- **Y** la pantalla de mantenimiento deniega el acceso al rol Conductor sin
  renderizar datos protegidos; el control de propiedad se prueba directamente
  en backend, sin presuponer una pantalla de consulta de terceros.

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

La API implementa page desde 1, page_size 1–100, default 20 y orden por
conductor_id ascendente. C-100/C-200/C-300 son alias de fixtures que deben
resolverse a UUID válidos; no son identificadores literales admitidos por HTTP.

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
| Provisión de credenciales | Contrato observado: email y contraseña inicial de solo escritura; no invitación. | ST-022, schemas, servicio y prueba HTTP de alta/login. | Decisión de implementación documentada, presentada para ratificación; D1. | Frank revisó; Julio pendiente. |
| Campos obligatorios, formatos y límites | Usar `telefono`, límites de schema y máximo técnico de experiencia; el patrón ASCII de licencia sigue pendiente en ECL-81. | Schema y ST-022 frente a propuestas iniciales. | D1/D5a/D5b; no se modifica la línea base. | Frank revisó; Julio pendiente. |
| Disponibilidad | Propuesta: intervalo completo al alta y para asignar; omitir ambos extremos en PATCH conserva; ambos `null` limpia el intervalo y mantiene el perfil no asignable; un solo extremo es inválido. | El modelo lógico sugiere `disponible_desde/hasta`; no define nulabilidad o actualización. | Constraints, validación de alta/PATCH y elegibilidad; D1/D4/D5b. | Frank propone; Antony/Julio revisan. |
| Licencia vencida al guardar | Se permite perfil vencido con elegibilidad básica falsa. La contradicción con RF-003 se mantiene explícita en ECL-81. | ST-022/ST-024 y US-003 frente a RF-003. | D3a acredita guardado; D3 requiere motor (ECL-79). | Julio/Frank deben resolver por control de cambios. |
| Permisos | Acuerdo de Frank para revisión: Administrador/Operador POST/GET listado/GET por ID/PATCH; Conductor solo GET propio; otros roles sin listado ni detalle individual. | Referencia a la matriz RBAC global, acotada a las operaciones candidatas de ECL-48. | Autorización, proyecciones, pruebas; D6/D7. | Frank acuerda; Antony/Julio revisan. |
| Listado y dependencia ST-023 | GET paginado implementado para Administrador/Operador; resúmenes sin DNI, licencia ni teléfono. | ST-022/ST-023 y pruebas de API/UI. | D6/D9; default 20, page_size 1–100, orden por UUID. | Frank revisó; Julio pendiente. |
| Proyección de Auditor | Extensión condicional, no implementada ni comprometida por el CRUD; definición/validación pendiente en ECL-80. | D8 y RNF-004; las pruebas actuales solo acreditan 403. | Mantener Sin prueba, no ampliar permisos desde ECL-71. | Julio/Frank deciden alcance. |
| RN-005 | Conducción y descansos por ruta, no duración de disponibilidad. | RN-005 y falta de motor. | F1/F2 y D3 sin prueba completa: ECL-79, relacionado con ECL-12. | Antony por motor; Julio/Frank por interpretación. |

## Verificación contra lo implementado

Revisión estática de Frank al 25/10/2026 sobre `main` `dc148e7`. **Cubierto**
significa que se inspeccionaron código y pruebas que afirman los observables,
con validaciones históricas enlazadas; no significa que se ejecutaran hoy.
**Diferencia** identifica una precisión corregida o una decisión pendiente.
**Sin prueba** identifica comportamiento no acreditado por una prueba completa.
No se reejecutaron suites backend/frontend ni se modificaron sus evidencias.

Referencias: [API](../../../backend/tests/unit/test_conductor_api.py),
[schemas](../../../backend/tests/unit/test_conductor_schemas.py),
[servicio](../../../backend/tests/unit/test_conductor_service.py),
[HTTP real](../../../backend/tests/integration/test_conductor_http_e2e.py),
[integración ST-024](../../../backend/tests/integration/test_conductor_st024.py),
[bordes ST-024](../../../backend/tests/unit/test_conductor_st024_unit.py),
[UI](../../../frontend/src/pages/DriversPage.test.tsx),
[dominio UI](../../../frontend/src/domain/driverForm.test.ts),
[ST-022](<../../03 Implementación/Sprint 02/validaciones/VALIDACION_ST022.md>),
[ST-023](<../../03 Implementación/Sprint 02/validaciones/VALIDACION_ST023.md>) y
[ST-024](<../../03 Implementación/Sprint 02/validaciones/VALIDACION_ST024.md>).

| Escenario | Prueba o evidencia que lo cubre | Resultado |
|---|---|---|
| D1 — alta válida | HTTP real `test_real_http_authentication_atomicity_and_driver_privacy`; servicio `test_registration_uses_hash_adapter_and_distinct_new_account`; schemas `test_normalization_and_secret_representation`; ST-022/ST-023. | Cubierto. Se concreta contraseña inicial, `telefono` y reloj fijo; no acredita patrón de licencia pendiente de ECL-81. |
| D2 — DNI duplicado | HTTP real; integración ST-024 `test_negative_requests_preserve_committed_data` verifica rollback de cuenta/perfil; API `test_sanitized_service_errors`. | Cubierto. Se corrige el texto esperado a conflicto genérico de identificador, sin exigir que revele cuál está duplicado. |
| D3 — licencia para ruta futura, incluido borde | Servicio `test_nonassignable_profiles` y `test_license_is_valid_through_its_final_local_day` solo prueban elegibilidad al consultar. No hay asignación de rutas. | Sin prueba completa. [ECL-79](https://continental-team-il84x39k.atlassian.net/browse/ECL-79), relacionado con ECL-12; no sustituir por prueba del CRUD. |
| D3a — guardar licencia vencida | HTTP real y schemas `test_clear_availability_and_expired_license_are_valid_profile_data`; ST-022/ST-024. | Diferencia normativa: guardado cubierto, pero contradicción RF-003/US-003 pendiente en [ECL-81](https://continental-team-il84x39k.atlassian.net/browse/ECL-81). |
| D4 — cambiar, omitir, retirar e invalidar disponibilidad | Integración ST-024 `test_availability_and_profile_survive_application_restart`, `test_negative_requests_preserve_committed_data`; servicio `test_read_page_and_update_validate_resulting_profile`; schemas `test_invalid_patch`; UI «edita sólo datos modificados, preserva fechas y retira disponibilidad»; dominio UI. | Cubierto para CRUD y representación Lima/UTC. El uso en una planificación futura sigue en ECL-79. |
| D5a — alta inválida | Schemas `test_invalid_registration`, API `test_validation_never_echoes_password_or_personal_data`, integración ST-024 `test_negative_requests_preserve_committed_data`. | Cubierto: 422 y ausencia de cuenta/perfil parcial. |
| D5b — PATCH inválido | Servicio `test_read_page_and_update_validate_resulting_profile`; integración ST-024 `test_negative_requests_preserve_committed_data`. | Cubierto: 422 y valores previos conservados. |
| D6 — permisos y controles visuales | API `test_authorized_contracts`, `test_forbidden_roles_do_not_reach_persistence`; HTTP real; integración ST-024 `test_real_forbidden_writes_preserve_data_and_audit_denial`; UI y ST-023. | Cubierto en las operaciones del CRUD; navegación no sustituye autorización. |
| D7 — Conductor consulta ajeno | API `test_driver_own_projection_and_foreign_denial_are_audited`, HTTP real y ST-022; ST-023 acredita denegación de la pantalla de mantenimiento a Conductor. | Cubierto en backend (403 sin datos). No presupone una pantalla de consulta de terceros para Conductor. |
| D8 — resumen anonimizado de Auditor, condicional | API `test_detail_denies_unsupported_projections` solo verifica denegación; no existe resumen agregado de conductores para Auditor. | Sin prueba de la extensión. [ECL-80](https://continental-team-il84x39k.atlassian.net/browse/ECL-80) debe definirla o registrar su descarte; no es defecto del CRUD mínimo. |
| D9 — listado paginado | HTTP real; servicio `test_repository_orders_paginates_and_locks`; API `test_invalid_pagination`; UI «pagina y actualiza desde el backend»; ST-022/ST-023. | Cubierto para orden, paginación, proyección y 403; los tres IDs del ejemplo son alias, no un dataset ejecutado hoy. |
| F1 — conducción total 8 h / 8 h 1 min | Bordes ST-024 `test_future_nine_hour_availability_is_not_driving_time` confirma que disponibilidad no es conducción; no prueba un motor. | Sin prueba. ECL-79: implementar y verificar límite por ruta, sin modificar RN-005. |
| F2 — 4 h continuas y descanso de 1 h | No se encontró motor ni pruebas de conducción continua/descansos en la base contrastada. | Sin prueba. ECL-79: verificar los límites y el descanso exacto. |

### Diferencias de contrato para ratificar

`contacto` se precisa como `telefono`, se documentan credenciales de solo
escritura, máximo técnico de experiencia y error de conflicto genérico según
ST-022. No son nuevas funciones. El patrón ASCII de licencia se mantiene como
decisión pendiente en ECL-81: no se elimina una propuesta por el mero hecho
de que falte en el código. Tampoco se cambia el criterio de asignación de D3
para hacerlo pasar con `habilitado_asignacion`.

Las tareas ECL-79 (5 SP), ECL-80 (2 SP) y ECL-81 (1 SP) se crearon en Jira con
estimaciones autorizadas expresamente por Frank; no se les impuso un sprint
ni una fecha. La ratificación acepta o rechaza la especificación y sus
pendientes; no acredita implementación de las extensiones.

## Condición para convertir el borrador en criterios ejecutables

Las entradas, respuestas y formatos de los escenarios son ejemplos concretos de
una propuesta para revisión, no un acuerdo. Tras la decisión de Julio, Antony y
Frank, conservar, ajustar o retirar cada regla candidata y alinear los BDD con
el contrato aprobado. Cualquier cambio a RF-003/RN-005 debe tramitarse mediante
control de cambios; este documento no declara pruebas ejecutadas.

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 0.2.0 | 25/10/2026 | Revisión ECL-71: verificación de todos los escenarios, precisiones del contrato observado y diferencias registradas en ECL-79/ECL-80/ECL-81. Ratificación de Julio pendiente. |

Tras la aprobación real de Julio se registrarán estado APROBADO, versión 1.0.0,
fecha efectiva y enlace a su revisión en este mismo documento. El nuevo commit
debe revalidarse y revisarse antes de integrar; no se retrofecha la acción A4.

[↑ Índice del Sprint 3](<../../03 Implementación/Sprint 03/README.md>)

[← Volver al README principal](../../../README.md)
