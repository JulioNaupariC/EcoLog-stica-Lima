# Backend EcoLogística Lima

## ST-032: contrato del itinerario offline

Aplicar `python -m alembic upgrade head` con `DATABASE_URL` del ambiente correcto
antes de desplegar esta revisión; head `0009_driver_stop_order`.
Agrega `driver_stop_assignment.pedido_id` nullable, FK a pedido y restricción única.
Las asignaciones anteriores permanecen sin vínculo hasta que el productor
confiable las migre; no se rellenan con datos ficticios.

`POST /login` agrega `expires_at` únicamente para CONDUCTOR, sin token en el cuerpo.
Es un vencimiento para la interfaz, no una autorización del cliente.
`GET /conductor/itinerario` devuelve `owner_id` autenticado y `stops`; cada parada
vinculada puede incluir `delivery: {address, reference, window_start, window_end}`.
Se excluyen datos de contacto/cliente y se responde `Cache-Control: no-store`.
Swagger/OpenAPI publica los esquemas actualizados.

El productor interno llama
`DriverReportService.provision_assignment(..., pedido_id=uuid_real)`;
se comprueba la existencia del pedido y se impide cambiar un vínculo existente.
No se agrega un endpoint público de aprovisionamiento ni un optimizador completo.
La autorización e idempotencia de `POST /conductor/reportes` siguen en el servidor:
mismo `operation_id` confirma la misma persistencia sin duplicarla.

Pruebas aisladas: `python -m scripts.verify_driver_offline --help`.
Procedimiento y evidencia: [VALIDACION_ST032.md](<../docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST032.md>).

Bootstrap FastAPI con SQLAlchemy síncrono y Psycopg 3. Incluye el modelo de
credenciales Usuario, hashing Argon2id, login HTTP con sesión por cookie HttpOnly,
autorización RBAC con auditoría persistente y registro de pedidos. El arranque
local con Docker Compose está documentado en el [README principal](../README.md#arranque-local-con-docker-compose--ecl-29). No incluye Redis ni worker.

## Instalación (PowerShell)

Esta instalación directa sigue disponible como alternativa a Docker Compose.
Dentro de la imagen Docker, `/app` es el directorio de trabajo y contiene el
paquete `app` y Alembic. Se instalan `requirements.lock` y no hace falta
instalar el proyecto como paquete editable para importar esos módulos.

Desde esta carpeta, comprobar primero `python --version`. El paquete declara
Python >=3.10; las versiones fijadas se validan con Python 3.12.10 en Windows.
La compatibilidad de otras versiones debe verificarse instalando las dependencias.

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.lock
.venv/Scripts/python -m pip install --no-deps --no-build-isolation -e .
.venv/Scripts/python -m pip check
.venv/Scripts/python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Para ejecución sin herramientas de desarrollo, instalar `requirements.lock`.
El entorno de construcción necesita setuptools; pip-tools lo incluye en desarrollo.

`GET /health` devuelve `{"status":"ok"}`. Swagger está en `/docs` y el esquema en
`/openapi.json`. La salud del proceso no certifica conectividad con la base.

## Configuración

Variables del proceso tienen precedencia sobre `.env`, leído desde el directorio
actual (ejecutar desde `backend/`). `.env.example` solo contiene valores seguros;
se puede copiar a `.env` e introducir allí la configuración privada.

| Variable | Uso |
|---|---|
| `DATABASE_URL` | Opcional para HTTP; obligatoria para DB/Alembic. Formato `postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE`. |
| `APP_ENV` | `development` (predeterminado), `test` o `production`. |
| `DB_CONNECT_TIMEOUT` | Tiempo de conexión en segundos, entre 1 y 30; predeterminado 5. |
| `CORS_ALLOWED_ORIGINS` | Array JSON de orígenes frontend permitidos, por ejemplo `["http://127.0.0.1:5173"]`. Predeterminado `[]`; en producción solo se aceptan orígenes HTTPS. |

Codificar caracteres especiales de usuario/contraseña en la URL. No registrar
credenciales ni incluirlas en comandos compartidos. Usar un usuario de aplicación
con privilegios mínimos; las operaciones administrativas usan otro usuario.

## Integración navegador/API — ECL-45

El backend de desarrollo se inicia en `http://127.0.0.1:8000` con el comando de
instalación anterior. Desde `frontend/`, iniciar Vite en el origen configurado:

```bash
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

El ejemplo de `CORS_ALLOWED_ORIGINS` permite ese origen y habilita credenciales
para `POST` JSON a `/login`, `/logout` y `/pedidos`. El frontend debe usar
`credentials: "include"` al iniciar sesión y al consumir la API para recibir y
enviar la cookie HttpOnly. Con `SameSite=Strict`, usar `127.0.0.1` en ambos
procesos; mezclarlo con `localhost` impide compartir la cookie como mismo sitio.
Los puertos diferentes siguen requiriendo CORS.

Sin orígenes configurados, el backend sigue disponible para clientes HTTP pero
no autoriza acceso CORS desde el navegador. En producción, establecer mediante
entorno una lista explícita de orígenes HTTPS del frontend; no usar comodines.
El despliegue debe conservar una relación de mismo sitio compatible con la
cookie `SameSite=Strict`. CORS no reemplaza la autenticación ni RBAC.

## PostgreSQL 16 y PostGIS

Se requiere una instancia existente y una base de pruebas. Un administrador debe
instalar PostGIS en el servidor y habilitarlo en la base elegida con
`CREATE EXTENSION IF NOT EXISTS postgis;`. La API no crea bases, extensiones ni tablas.

Con `DATABASE_URL` configurada privadamente:

```powershell
.venv/Scripts/python -m app.db.check
.venv/Scripts/python -m pytest tests/integration -q
.venv/Scripts/python -m alembic current
```

El comprobador ejecuta SELECT 1, verifica PostgreSQL 16, consulta PostGIS_Version()
y comprueba SRID 4326. Son consultas de lectura. Devuelve código 1 ante ausencia de
configuración, error de acceso, versión incompatible o PostGIS no habilitado;
el mensaje no imprime la URL ni el error del driver.

Sin URL, integración se omite expresamente. Con URL configurada, un error falla
la prueba: nunca se interpreta como validación exitosa.

## Estructura y transacciones

`app/api` contiene HTTP; `app/core`, configuración; `app/db`, infraestructura.
La factoría FastAPI crea el motor sin abrir conexión y lo libera al cerrar.
`session_factory` y `get_session` preparan sesiones síncronas; el llamador realiza
commit explícito. Los errores provocan rollback y el cierre libera la sesión.
Futuros handlers que usen estas sesiones deben ser síncronos (`def`).

Alembic obtiene la URL del entorno y usa `Base.metadata`. La primera revisión
es `0001_create_usuario`, sin revisión padre. Crea únicamente `usuario` con UUID,
email único, password_hash, rol, estado y creado_en según el esquema aprobado.
Las migraciones se ejecutan explícitamente, nunca al arrancar HTTP.
La comparación de metadata excluye `spatial_ref_sys`, administrada por PostGIS.

```powershell
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m alembic current
.venv/Scripts/python -m alembic check
```

Con `postgis/postgis:16-3.5` en Docker Compose, `alembic check` puede proponer
eliminar tablas e índices instalados por las extensiones espaciales. Para
confirmar revisiones aplicadas en ese entorno, comparar `alembic current` con
`alembic heads`; no ejecutar las eliminaciones sugeridas. La verificación de
deriva mediante autogeneración requiere un ajuste posterior fuera de ECL-29.

PostgreSQL 16 dispone de `gen_random_uuid()`; comprobar su disponibilidad antes
del upgrade. La migración no instala extensiones ni crea usuarios iniciales.

## Credenciales — ECL-30

`app/core/passwords.py` ofrece `hash_password`, `verify_password` y `needs_rehash`
usando argon2-cffi. Perfil explícito Argon2id: 64 MiB, 3 iteraciones y paralelismo
4; salt aleatorio generado por la biblioteca. El hash codificado incluye salt y
parámetros, y se almacena exclusivamente en `password_hash VARCHAR(255)`.

Se rechazan null, valores no string y cadena vacía. Se preservan Unicode y
espacios, sin normalización, truncamiento ni límite de 1024 bytes. No se define
una política de fortaleza o caducidad no documentada.

`CredentialService(UsuarioRepository(session))` expone:

- `create(email, password, rol)`: devuelve `UserIdentity`, sin hash.
- `verify(usuario_id, password)`: verifica únicamente la contraseña.
- `verify_and_rehash(usuario_id, password)`: verifica y actualiza parámetros si
  corresponde. Usa una actualización condicional para no sobrescribir un cambio
  de contraseña concurrente. Ante conflicto devuelve falso.

La creación siempre calcula un hash nuevo; una cadena con aspecto de hash se
trata como contraseña literal, nunca como hash importado. El repositorio mantiene
el hash dentro de su implementación y no lo devuelve al servicio. No se deben
serializar entidades ORM ni inspeccionar sus atributos como respuesta pública.

El llamador es dueño de la transacción: debe realizar commit explícito o rollback.
Los fallos de almacenamiento se convierten en `CredentialStorageError` sin
detalles del driver. No registrar entidades, contraseñas, hashes ni excepciones
originales. Un hash malformado o contraseña incorrecta no verifica; los fallos
operativos del backend generan errores saneados.

Verificar una contraseña no autoriza acceso ni comprueba estado activo. ECL-31
añade RBAC/auditoría por separado; ECL-36 coordinará estado de cuenta, bloqueo
RN-001, login y sesión. El servicio de credenciales conserva su alcance original.

## Autorización y auditoría — ECL-31

La matriz estática de `app/core/rbac.py` se traza contra
`docs/01 Inicio/08. Usuarios V_1_0_0.md`, RF-001 a RF-012, RN-002, RN-015
y RNF-003/RNF-004. No se modifican los documentos base. Rol identifica un perfil;
recurso identifica una capacidad; acción identifica la operación; permiso es
el par explícito `recurso.accion`. No hay tablas de permisos ni gestión dinámica.
Los enums de Python no cambian el VARCHAR ni los constraints de Usuario.
Cambiar el catálogo de roles requiere una nueva migración Alembic.
Nunca editar 0001 después de aplicada.

En esta tabla C/R/U/D equivalen a crear/consultar/actualizar/desactivar.
Cada letra corresponde a un permiso distinto; D siempre es lógico.

| Recurso | Administrador | Operador | Conductor | Analista | Auditor |
|---|---|---|---|---|---|
| usuarios | CRUD | R | — | — | R anonimizado |
| parametros | CRUD | R | — | R | R |
| vehiculos | CRUD | CRU | R asignado/jornada | R agregado | R |
| conductores | CRUD | CRU | R propio | R agregado | R anonimizado |
| pedidos | CRUD | CRU | R asignado/jornada | R agregado | R anonimizado |
| clientes | CRUD | CRU | R asignado/jornada | R agregado | R anonimizado |
| optimizaciones.consultar | Sí | Sí | — | Sí | Sí |
| optimizaciones.ejecutar / rutas.reoptimizar | — | Sí | — | — | — |
| rutas.consultar | Sí | Sí | Asignada/jornada | Agregado | Anonimizado |
| rutas.actualizar_estado | — | Sí | Asignada/jornada | — | — |
| incidencias | R | CRU | CR propias | R agregado | R anonimizado |
| indicadores.consultar | Sí | Sí | Propio | Sí | Sí |
| reportes.consultar / reportes.descargar | Sí | Sí | Propio | Sí | Anonimizado |
| compensacion.consultar | — | — | — | Sí | — |
| auditoria.consultar | Sí | Propio | Propio | — | Sí |

Los permisos son contratos para futuros módulos, no implementaciones de esos
módulos. `compensacion.consultar` se traza a RF-011/US-011. La descarga de un
reporte no concede escritura operativa. No se concede creación manual de rutas:
RF-006 define generación mediante optimización. No existe comodín de Administrador.

Interpretación restrictiva de la contradicción documental: aunque algunas celdas
conceden D al Operador, la regla complementaria exige Administrador. Se deniega D
al Operador y no se añade desactivación de incidencias a ningún rol porque la
matriz solo concede R al Administrador. El Auditor no recibe DNI/contacto ni una
excepción de acceso a datos personales; RNF-004 exige su protección.

### Contrato de uso independiente de HTTP

`evaluar(identidad, permiso, contexto)` es una policy pura sin I/O. Deniega
identidad/rol/permiso inválidos, estado diferente de ACTIVO, concesión ausente
y contexto insuficiente. `None` significa que no se proporcionó contexto y solo
puede bastar para alcance GENERAL; cualquier valor no nulo que no sea `Contexto`
se deniega, incluso para alcance GENERAL. La matriz y sus mapas son inmutables.

`Identidad` contiene UUID, rol y estado. El llamador debe obtenerlos de una fuente
confiable y vigente; no aceptar esos datos desde el cliente ni interpretar una
instancia de esta clase como prueba de autenticación. El usuario debe estar
persistido antes de auditar con su UUID. No se arrastran email ni hash.

`Contexto` representa hechos obtenidos por el servidor. PROPIO compara propietario
con actor; ASIGNADO_JORNADA exige actor asignado y UUID de jornada coincidente.
AGREGADO/ANONIMIZADO requieren una proyección explícita. No enviar booleanos del
cliente como evidencia ni pasar a estas verificaciones IDs sin validar.
Las colecciones deben filtrarse por el servidor antes de dar acceso.

La policy no agrega ni anonimiza datos: el futuro repositorio/esquema de respuesta
debe aplicar la proyección seleccionada y minimizar campos también en GENERAL.
Los UUID de jornada son un contrato interno para la futura integración, no una
tabla nueva. La restricción de sede/zona se implementará cuando exista ese modelo;
este incremento no habilita operación multisede.

`AutorizacionService(auditoria).autorizar(...)` evalúa y registra antes de retornar
la Decision permitida; si deniega, lanza `AuthorizationDenied("Access denied")`.
El consumidor ejecuta la operación solo después de ese retorno y respeta el
alcance. `evaluar` por sí solo no audita. `AuditoriaService(audit_factory)` es el
adaptador persistente; el servicio de autorización acepta un contrato AuditSink.
La factory de auditoría se crea desde `build_audit_engine(Settings())`, usando la
misma configuración externa pero un Engine y pool distintos de los de negocio.
Ambos engines tienen ciclos de vida separados y deben liberarse por separado.

No existe dependencia FastAPI, proveedor HTTP simulado ni endpoint adicional.
ECL-36 resolverá identidad, conectará autorización con HTTP y traducirá errores.
GET /health permanece público. Las rutas automáticas de documentación tampoco
cambian. La frase de Jira «aplicadas a endpoints protegidos» tiene integración
pendiente hasta que existan esos endpoints y su proveedor real de identidad.

### Auditoría de decisiones

Solo se escriben AUTORIZACION_PERMITIDA y AUTORIZACION_DENEGADA. La primera
no acredita ejecución ni éxito de una operación de negocio. No se auditan login,
sesiones, bloqueo RN-001 ni operaciones de módulos inexistentes.

El modelo lógico aprobado define los siete campos. ECL-31 concreta los tipos:

| Campo | Tipo / regla |
|---|---|
| auditoria_id | UUID PK generado por PostgreSQL |
| usuario_id | UUID nullable, FK a usuario con ON DELETE RESTRICT |
| entidad | VARCHAR(50), derivado del permiso; autorizacion si es inválido |
| entidad_id | UUID nullable, referencia lógica a objeto existente cuando aplique |
| accion | VARCHAR(64), CHECK limitado a las dos decisiones |
| creado_en | TIMESTAMPTZ, CURRENT_TIMESTAMP |
| detalle | JSONB objeto, únicamente permiso enumerado/null y motivo enumerado |

La nulabilidad permite denegaciones sin identidad u objeto establecido; no se
inventan usuarios. Tipos, longitudes e índices son decisiones físicas de ECL-31,
no un DDL de auditoría preexistente. Hay índices por fecha y usuario/fecha.

Registro/Detalle son modelos tipados, inmutables y validados con campos adicionales
prohibidos. El repositorio construye el contenido; no admite payload libre para
volcarlo a JSONB. Un permiso o rol inválido nunca se copia como texto en detalle.
No registrar contraseñas, hashes, tokens, cookies, sesiones secretas, DNI/contacto,
emails, cuerpos HTTP, headers ni mensajes originales de excepciones. No registrar
objetos de validación completos ni sus entradas al integrar consumidores.

El repositorio solo inserta y hace flush. AuditoriaService recibe exclusivamente
la factory del engine dedicado, posee una transacción corta y confirma cada
decisión; un rollback de negocio posterior no la elimina. Si falla conexión,
flush o commit se lanza AuditStorageError con
mensaje saneado y no se concede autorización. No hay reintento recursivo.
La auditoría es append-only mediante esta API, no una garantía contra un usuario
SQL privilegiado; no hay funciones de edición/borrado ni retención automática.

### Migración incremental y verificación

`0002_create_auditoria` depende de `0001_create_usuario`, que permanece intacta.
Upgrade crea únicamente auditoria e índices; downgrade a 0001 elimina auditoria
y conserva usuarios y PostGIS. La aplicación no ejecuta migraciones al arrancar.

Las pruebas de ECL-31 cubren policy, alcances, errores saneados, persistencia,
rollback y ciclo 0001 → 0002 → 0001 → 0002. El test de migración ejecuta también
`alembic.command.check` en ambos upgrades contra TEST_DATABASE_URL. ECL-32 mantiene
la suite transversal de seguridad/HTTP y las 20 pruebas de exposición de RNF-004.
La cobertura local no acredita el DoD completo ni sustituye peer review/SAST.

## Login y sesión — ECL-36

`POST /login` recibe únicamente email y password. Un acceso válido devuelve UUID
y rol actuales, y establece `ecologistica_session`; el token nunca aparece en el
JSON. Usuario inexistente, password incorrecta, estados INACTIVO/BLOQUEADO y un
bloqueo temporal activo reciben el mismo 401 `Credenciales inválidas`. Los fallos
de almacenamiento o auditoría producen un 503 saneado.

La sesión es opaca y revocable. Se genera con aleatoriedad criptográfica y la BD
almacena únicamente SHA-256(token). La cookie usa HttpOnly, SameSite=Strict,
path `/` y Secure en producción. `SESSION_TTL_MINUTES` es configuración técnica,
vale 60 por defecto y admite de 1 a 1440 minutos; no es requisito funcional. No
hay JWT ni refresh token.

`POST /logout` exige la sesión actual, la revoca, limpia la cookie y devuelve 204.
No revoca otras sesiones. Cada request protegido vuelve a resolver el hash de la
cookie, la sesión y el Usuario en PostgreSQL. Rol, estado y UUID nunca se confían
desde el cliente. Una sesión revocada/vencida, un cambio a INACTIVO/BLOQUEADO o un
bloqueo temporal vigente invalidan el acceso. `require_permission()` entrega esa
Identidad de BD a ECL-31; no se añadieron endpoints de negocio y `/health` sigue
público.

### RN-001

`intentos_fallidos` y `bloqueado_hasta` son independientes de `estado`. La fila de
Usuario se bloquea con `SELECT FOR UPDATE`: cada password incorrecta incrementa el
contador; la tercera conserva estado ACTIVO y fija 15 minutos. Al vencer, se limpia
el bloqueo antes del siguiente intento. Un éxito reinicia ambos campos. Los estados
BLOQUEADO e INACTIVO nunca se reactivan automáticamente. Un email inexistente pasa
por una verificación Argon2 ficticia, sin contador ni persistencia del email.

### Auditoría y transacciones

ECL-36 añade LOGIN_EXITOSO, LOGIN_FALLIDO, CUENTA_BLOQUEADA y SESION_CERRADA con
un detalle de acceso tipado separado del detalle RBAC. LOGIN_FALLIDO siempre tiene
`usuario_id=NULL`; una cuenta conocida solo puede aparecer como `entidad_id`. Nunca
se registran email, password, hashes, token, cookie, IP, user-agent ni errores del
driver.

Negocio y auditoría usan engines/pools creados una vez durante el lifecycle y se
cierran al apagar. La cookie se entrega solo después de persistir sesión y auditar
LOGIN_EXITOSO. Si la auditoría falla, la sesión creada se revoca compensatoriamente
y se devuelve 503.

### Migración 0003 y límites

`0003_create_login_sessions` depende de `0002_create_auditoria`: añade los campos
de RN-001, crea `sesion` y amplía el CHECK de auditoría. No modifica revisiones
anteriores. El downgrade a 0002 solo continúa si no existen eventos ECL-36. Si
existen, falla explícitamente sin borrar auditorías ni alterar esos registros, que
requieren tratamiento manual antes de volver a 0002.

ECL-38 conserva las pruebas BDD completas de autenticación. ECL-32 conserva la
campaña ofensiva, CSRF, enumeración temporal, fijación/robo de sesión y exposición
transversal de datos. ECL-36 aporta únicamente las pruebas técnicas necesarias.

## Modelo de vehículos — ECL-39

`0004_create_vehiculo` depende de `0003_create_login_sessions` y crea la tabla
`vehiculo`. Incluye `vehiculo_id` UUID, `placa VARCHAR(10) UNIQUE`,
`tipo VARCHAR(20)`, `capacidad_kg NUMERIC(10,2)`,
`capacidad_m3 NUMERIC(10,2)`, `rendimiento_km_l NUMERIC(10,3)`,
`factor_co2_kg_km NUMERIC(10,5)`, `anio_fabricacion SMALLINT` y
`estado VARCHAR(15) DEFAULT 'ACTIVO'`, con índice por estado.

El catálogo de tipo admite únicamente CAMIONETA, FURGON y MOTO. Ambas capacidades
y el rendimiento deben ser positivos; el factor de CO₂ admite cero, pero no valores
negativos, y el año debe estar entre 1980 y 2100. La placa debe proporcionarse en
mayúsculas, sin whitespace exterior y no vacía; no se transforma automáticamente.
Se admite whitespace interno. No se impone una regex de placa peruana ni existe
todavía un CHECK de catálogo para estado.

El downgrade `0004 → 0003` elimina la tabla `vehiculo` y todos sus datos. Es una
operación destructiva reservada a la base desechable de pruebas; nunca debe
ejecutarse contra desarrollo.

## Pruebas de migración y persistencia

Configurar privadamente `TEST_DATABASE_URL` en el entorno o `.env`, apuntando a
una base desechable cuyo nombre termine en `_test` y sea distinto del nombre de
la base de desarrollo. No se usa `DATABASE_URL` como sustituto.

El esquema public debe estar vacío: solo se admiten `spatial_ref_sys` de PostGIS
y una tabla `alembic_version` vacía. Las pruebas crean/eliminan `usuario`, `auditoria`,
`sesion`, `vehiculo`, `cliente` y `pedido`; pueden dejar la tabla de control de Alembic vacía.
Requieren `TEST_DATABASE_URL`, sin fallback a `DATABASE_URL`, y aplican las
validaciones de nombre `_test` y separación respecto de desarrollo. No ejecutarlas
contra datos que se desee conservar ni ejecutar downgrades destructivos contra
desarrollo. No se realizan downgrades automáticos al iniciar HTTP.

## API de vehículos — ECL-40

La API autenticada expone `POST /vehiculos`, `GET /vehiculos`,
`GET /vehiculos/{vehiculo_id}`, `PATCH /vehiculos/{vehiculo_id}` y
`DELETE /vehiculos/{vehiculo_id}`. El DELETE nunca elimina la fila: aplica la
transición lógica `ACTIVO → INACTIVO`; repetirla es idempotente. Un vehículo
inactivo puede consultarse, pero no modificarse ni reactivarse desde este CRUD.

La placa recibida por HTTP se normaliza con `strip().upper()`, conservando guiones
y whitespace interno. Los campos numéricos usan `Decimal` y rechazan valores no
finitos, signo, precisión o escala incompatibles antes de llegar a PostgreSQL.

Administrador dispone de CRUD, Operador de CRU y Auditor de lectura. Los alcances
asignado del Conductor y agregado del Analista no forman parte del listado CRUD
general. La identidad siempre procede de la sesión persistida.

`0005_extend_vehicle_audit_events` añade únicamente
`VEHICULO_PARAMETROS_ACTUALIZADOS` y `VEHICULO_DESACTIVADO`. Estas auditorías se
insertan en la misma transacción que el cambio del vehículo. El downgrade falla
sin borrar evidencia si existen eventos incompatibles con `0004`.

```powershell
.venv/Scripts/python -m pytest tests/integration -q
```

`TEST_DATABASE_URL` es obligatoria para las pruebas destructivas. Si falta o es
inválida, la suite correspondiente falla explícitamente; nunca usa `DATABASE_URL`
como fallback. La prueba de conectividad PostGIS existente usa `DATABASE_URL` y
es de solo lectura.

## Registro de pedidos — ECL-43

`POST /pedidos` requiere sesión con `pedidos.crear` (Administrador u Operador) y
devuelve `201` con el Pedido en estado `PENDIENTE`. Recibe `cliente_id`, dirección,
peso y volumen positivos, ventana con timestamps que incluyan zona u offset,
prioridad (`EXPRESS`, `ESTANDAR`, `ECONOMICO`) y tipo de producto libre hasta 20
caracteres. La ubicación admite latitud y longitud WGS84 juntas, o una referencia
textual no vacía de hasta 255 caracteres; también se pueden enviar ambas. El
request no acepta `pedido_id` ni `estado`.

La revisión `0006_create_cliente_pedido` crea la tabla documental `cliente` para
la FK y `pedido.ubicacion GEOGRAPHY(POINT,4326)` en PostGIS. La API no crea la
extensión PostGIS ni expone operaciones de Cliente. El CRUD y las preferencias
de Cliente pertenecen a ECL-11. Las pruebas de migración y persistencia de Pedido
usan exclusivamente la `TEST_DATABASE_URL` validada por el fixture existente.

## Itinerario del conductor y reportes offline — ECL-58

La revisión `0008_driver_reports` agrega asignaciones mínimas
conductor-parada e informes persistidos. `GET /conductor/itinerario` y
`POST /conductor/reportes` requieren sesión activa y rol `CONDUCTOR`; ambos
permisos se auditan con alcance propio. El propietario siempre se obtiene de la
sesión, y un informe sólo se acepta para una parada asignada a ese conductor.

El POST recibe `operation_id` (UUID idempotente), `stop_id` y estado final
`ENTREGADO` o `NO_ENTREGADO`. Repetir la misma operación devuelve el mismo ACK;
reutilizar el UUID con otro propietario o contenido produce `409`. La transacción
persiste el evento y el estado de parada conjuntamente. Una parada ya finalizada
no admite otro informe. Los fallos de almacenamiento devuelven mensajes
saneados.

El aprovisionamiento no se expone por HTTP. El futuro productor confiable del
planificador debe llamar `DriverReportService.provision_assignment(...)` usando
los UUID de parada y conductor producidos por ese flujo. La implementación actual
no contiene modelos ni un flujo de planificación/asignación de rutas, por lo que
el endpoint devuelve una lista vacía hasta que ese adaptador se conecte; esta
revisión no inventa asignaciones ni UUIDs. Tampoco sustituye el modelo de
Pedido/Parada ni almacena datos personales de clientes en el reporte.

En el cliente, la instantánea del itinerario y la outbox se separan por UUID de
sesión en IndexedDB. El cierre de sesión advierte sobre reportes sin ACK y no los
borra; tras autenticarse nuevamente con la misma cuenta pueden sincronizarse.
Sólo una confirmación HTTP con el mismo `operation_id` elimina un reporte local.

## Datos de demostración — Sprint 2

`scripts/seed_demo.py` crea un conjunto ficticio para la demostración del
Sprint 2. **Solo se ejecuta contra una base cuyo nombre termine en `_demo`**;
en cualquier otro caso, o con `APP_ENV=production`, termina sin modificar
nada. Las contraseñas se leen de variables de entorno (mínimo 12 caracteres)
y nunca se guardan en el repositorio ni se imprimen.

```powershell
# Base exclusiva y migrada, por ejemplo ecologistica_demo.
$env:DATABASE_URL = "postgresql+psycopg://USUARIO:CONTRASENA@127.0.0.1:5432/ecologistica_demo"
.venv/Scripts/python -m alembic upgrade head
# Definir privadamente SEED_DEMO_PASSWORD_ADMINISTRADOR, _OPERADOR, _CONDUCTOR,
# _ANALISTA y _AUDITOR (por ejemplo, con un gestor de contraseñas).
.venv/Scripts/python -m scripts.seed_demo
```

Crea, mediante los servicios de la aplicación:

| Dato | Cantidad | Detalle |
|---|---:|---|
| Usuarios | 1 por rol | `<rol>.demo@ecologistica.example`; la cuenta de conductor es `conductor.demo@ecologistica.example` |
| Clientes | 8 | Nombres ficticios; 7 con preferencias y 1 sin ellas (ruta de borde) |
| Vehículos | 5 | Placas `DEMO-001` a `DEMO-005` |
| Conductores | 4 | Dos habilitados, uno con licencia vencida y otro sin disponibilidad (rutas de borde) |
| Pedidos | 20 | Referencias `Pedido demo 01` a `Pedido demo 20`; los 5 primeros, hoy (Lima) de 09:00 a 14:00 en franjas de una hora; el resto, hoy y mañana |
| Paradas | 5 | Asignadas a `conductor.demo` con `DriverReportService.provision_assignment`, en orden de ventana (parada 1 a las 09:00, parada 5 a las 13:00) |

No existe un servicio de alta de clientes (su CRUD queda para el Sprint 3), así
que los clientes se insertan con el modelo ORM, no con SQL directo; sus
preferencias se guardan con `PreferenciasService`. El script es idempotente:
una segunda ejecución informa que todo «ya existía» y no duplica nada. Las fechas
se fijan en la primera ejecución: para demostrar otro día, recrear la base `*_demo`
(`dropdb`/`createdb`, extensión PostGIS y `alembic upgrade head`) y sembrar ese día.
Pruebas: `tests/unit/test_seed_demo.py` y `tests/integration/test_seed_demo.py`.

## Calidad

```powershell
.venv/Scripts/python -m pytest tests/unit --cov=app --cov-report=term-missing --cov-fail-under=80
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m ruff format --check .
```

Pruebas unitarias aíslan las variables y no acceden a una base real. Comprueban
importaciones, configuración, HTTP/OpenAPI, sesiones y manejo de fallos.
La prueba de integración se ejecuta separadamente contra PostgreSQL/PostGIS.
SAST, CI/CD y despliegue pertenecen a otros tickets; estas comprobaciones locales
no acreditan el DoD completo de ECL-19.

Para regenerar las versiones fijadas desde pyproject.toml:

```powershell
.venv/Scripts/python -m piptools compile --no-build-isolation --no-emit-index-url --no-emit-trusted-host --output-file=requirements.lock pyproject.toml
.venv/Scripts/python -m piptools compile --no-build-isolation --allow-unsafe --no-emit-index-url --no-emit-trusted-host --extra=dev --output-file=requirements-dev.lock pyproject.toml
```

## API de conductores - ECL-48 / ST-022

POST /conductores crea una cuenta CONDUCTOR y su perfil de forma atómica.
GET /conductores ofrece un listado paginado; GET y PATCH
/conductores/{conductor_id} consultan y actualizan el perfil/disponibilidad.
Administrador y Operador pueden registrar, consultar y actualizar.
Conductor sólo consulta su propio resumen; Analista/Auditor no acceden
a esta API individual. Se usa la sesión y RBAC existentes.

Una licencia vencida puede guardarse, pero el perfil se devuelve no asignable.
Las contraseñas son de sólo escritura y se hashean mediante Argon2id.
PATCH no permite cambiar cuenta, rol ni credenciales.

El contrato, permisos, validaciones, pruebas y límites se describen en
[VALIDACION_ST022.md](<../docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST022.md>). Los endpoints están disponibles
en /docs y /openapi.json.

### Auditoría de conductores — RN-015

Desde la migración `0010_extend_driver_audit_events`, el alta registra
`CONDUCTOR_REGISTRADO` y cada PATCH que cambie algún valor registra
`CONDUCTOR_ACTUALIZADO` con `campos_modificados` (solo nombres de campo, nunca
DNI, teléfono ni otros valores). Ambos eventos guardan el actor y el conductor,
y se escriben en la misma transacción: si la auditoría falla, la operación
devuelve 503 y no se persiste. Un PATCH con los mismos valores no genera
evento. El downgrade de 0010 se niega si ya existen eventos de conductor.
Pruebas: `tests/unit/test_conductor_audit.py` y
`tests/integration/test_conductor_audit.py`.

## Métricas y disponibilidad — ECL-60 / ST-034

GET /metrics expone contadores HTTP, errores 5xx, solicitudes en vuelo e histogramas
de latencia HTTP y SQL. Requiere sesión y permiso INDICADORES_CONSULTAR del RBAC existente.
Las etiquetas usan rutas agrupadas y operaciones SQL; no contienen datos personales,
cuerpos, SQL ni credenciales. El registro es por proceso y se reinicia con la API.

GET /health conserva liveness. GET /health/ready comprueba SELECT 1 con un pool de
lectura limitado y devuelve 200/503. El healthcheck Docker usa este segundo endpoint.
Para observaciones externas: `python -m app.monitoring.poll --interval 60`, desde backend;
produce JSONL y exige que API y BD respondan correctamente dentro de 5 s.

Ver [VALIDACION_ST034.md](<../docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST034.md>) y
[evidencias ECL-60](evidencias/ECL-60/README.md) para permisos, límites y reproducción.

## Preferencias de entrega — ECL-52 / ST-026

GET y PATCH /clientes/{cliente_id}/preferencias consultan e inicializan/actualizan
horario_preferido, referencia y restriccion_acceso de un Cliente existente.
Administrador y Operador utilizan la sesión y los permisos de Cliente existentes;
los demás roles no acceden a esta proyección individual.

PATCH conserva campos omitidos, permite null para limpiar y rechaza campos extra,
texto vacío, NUL y longitudes superiores a 120/255/255 caracteres. Los textos válidos
se preservan sin recorte. La actualización es transaccional y se limita al Cliente
identificado en la ruta, sin crear clientes ni alterar pedidos existentes.

El consumidor puede consultar preferencias al preparar un pedido y elegir usar
la referencia. El horario textual no se convierte automáticamente en una ventana.
El frontend de ese flujo corresponde a ST-027.

Contrato, resultados y reproducción en [VALIDACION_ST026.md](<../docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST026.md>).

## Búsqueda de clientes — ECL-53 / D-01

GET /clientes?buscar=&page=&page_size= devuelve una página de clientes con la
proyección mínima `cliente_id` y `nombre`, para los selectores de pedido y
preferencias. Requiere CLIENTES_CONSULTAR con alcance general (Administrador u
Operador); el resto de roles recibe 403. `page_size` admite de 1 a 50 (20 por
defecto). `buscar` se recorta, admite como máximo 160 caracteres, rechaza
caracteres de control, busca por fragmento del nombre sin distinguir
mayúsculas (los comodines `%` y `_` se tratan literalmente) y coincide además
con un `cliente_id` exacto. Los errores de validación no reflejan la entrada y
la respuesta lleva `Cache-Control: no-store`.

Pruebas: `tests/unit/test_clientes_api.py` y
`tests/integration/test_clientes_http_e2e.py`.

## Pruebas de gestión de conductores — ECL-50 / ST-024

La suite cubre datos válidos e inválidos, permisos, disponibilidad y persistencia
real en PostgreSQL. CI conserva JUnit y cobertura durante 30 días, incluso si
fallan las pruebas, y exige cobertura unitaria de conductores de al menos 80 %.
Consultar [VALIDACION_ST024.md](<../docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST024.md>) para la matriz de casos y
los resultados locales; [GUIA_JOSE_ST024.md](<../docs/03 Implementación/Sprint 02/guias/GUIA_JOSE_ST024.md>) explica cómo
repetir las pruebas, subir la rama y obtener la evidencia de GitHub Actions.

## Pruebas de carga y disponibilidad — ST-035 / ECL-61

La campaña aislada y sus parámetros se describen en
[loadtest/README.md](loadtest/README.md). Usa Locust con dependencias separadas
en `requirements-load.lock`, HTTP real y bases nuevas por perfil.
Los resultados, capturas e incidencias están en
[VALIDACION_ST035.md](<../docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST035.md>) y
[evidencias/ECL-61](evidencias/ECL-61/README.md).
El porcentaje de sondeos exitosos no acredita el SLA mensual.

## Resultados, SLA y operación — ECL-62 / ST-036

El [informe técnico ST-036](<../docs/03 Implementación/Sprint 02/informes/INFORME_ST036.md>) consolida resultados medidos de ST-035,
comparación con umbrales, fórmula mensual del SLA y procedimientos de diagnóstico.
P95 y 5xx observados son favorables; concurrencia sostenida y tablero no acreditados.
El SLA mensual permanece NO MEDIDO. La
[verificación derivada](evidencias/ECL-62/verificacion-fuentes.json) registra el
recálculo numérico y las discrepancias de integridad sin modificar evidencias previas.

## ECL-63 / ST-037: mediciones iniciales

Consultar [INFORME_ST037.md](<../docs/03 Implementación/Sprint 02/informes/INFORME_ST037.md>) y
[evidencias/ECL-63](evidencias/ECL-63/README.md). Incluye planes reales de
consultas de pedidos sobre datos sinteticos y oportunidades para ST-038.
Dashboard y rutas permanecen pendientes; no se acredita RNF-012.

## ECL-64 / ST-038: consulta minima de cliente

La comprobacion de cliente para registrar pedidos usa SELECT EXISTS, evitando
recuperar el perfil completo. Ver [VALIDACION_ST038.md](<../docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST038.md>) y
[evidencias/ECL-64](evidencias/ECL-64/README.md) para comparacion y pruebas.
El payload del dashboard sigue pendiente; este incremento no acredita RNF-012.

## ECL-54 / ST-028: validacion de preferencias

Ver [VALIDACION_ST028.md](<../docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST028.md>) para matriz BDD, resultados
y diferencias registradas. La API y gestion de preferencias estan contrastadas;
P8 presenta una brecha en la propuesta al crear pedidos. El BDD sigue en borrador.

## Restablecimiento de contraseña (ECL-77)

US-013, Sprint 3. Sin servicio de correo no hay autoservicio por email: el
Administrador genera una contraseña temporal que se muestra una sola vez, y la
persona debe cambiarla al entrar. Evidencia y comandos en
[VALIDACION_US013.md](<../docs/03 Implementación/Sprint 03/validaciones/VALIDACION_US013.md>).

### Flujo

1. El Administrador abre la lista de cuentas y restablece la de un usuario.
2. El servicio genera la temporal, guarda solo su hash Argon2id, marca
   `debe_cambiar_contrasena=true`, fija el vencimiento en 24 h, limpia
   `intentos_fallidos` y `bloqueado_hasta`, revoca **todas** las sesiones del
   usuario y audita `CONTRASENA_RESTABLECIDA`, todo en una transacción.
3. El usuario inicia sesión con la temporal: `LoginResponse` informa
   `debe_cambiar_contrasena=true` y cualquier otro endpoint autenticado responde
   403 `Cambio de contraseña requerido`.
4. `POST /cambiar-contrasena` guarda la nueva, limpia el indicador y el
   vencimiento, revoca las **otras** sesiones (conserva la actual) y audita
   `CONTRASENA_CAMBIADA`. La temporal deja de servir.

### Endpoints

| Método y ruta | Acceso | Respuesta |
|---|---|---|
| `GET /usuarios?page=&page_size=` | `USUARIOS_ACTUALIZAR` (Administrador) | Página con `usuario_id`, `email`, `rol`, `estado`, `debe_cambiar_contrasena`; nunca el hash |
| `POST /usuarios/{usuario_id}/restablecer-contrasena` | `USUARIOS_ACTUALIZAR` (Administrador) | `{contrasena_temporal, expira_en}` con `Cache-Control: no-store`; 404 si no existe; 409 si está inactivo o es la propia cuenta |
| `POST /cambiar-contrasena` | Cualquier sesión, también con cambio pendiente | 204; 422 si la nueva tiene menos de 12 caracteres o es igual a la actual; 400 si la actual no es válida |
| `POST /login` | Público | Agrega `debe_cambiar_contrasena: bool` |

`GET /usuarios` exige `USUARIOS_ACTUALIZAR` y no `USUARIOS_CONSULTAR` por mínimo
privilegio (OWASP A01): la lista expone el correo de todas las cuentas. La matriz
RBAC no cambia; el `USUARIOS_CONSULTAR` del Operador queda para revisión del equipo.

### Reglas de seguridad

- La temporal tiene 16 caracteres de `secrets` sobre un alfabeto sin ambiguos
  (sin 0/O/o ni 1/l/I). Solo se persiste su hash y solo se devuelve una vez.
- Una temporal vencida responde el mismo 401 genérico que unas credenciales
  inválidas y no suma intentos.
- Una contraseña actual incorrecta en el cambio cuenta como en el login: tres
  intentos bloquean 15 minutos y se audita `LOGIN_FALLIDO`/`CUENTA_BLOQUEADA`.
- La obligación de cambio se aplica en `get_authenticated_session`, una sola vez
  para todos los endpoints; `get_current_session` solo la usan `/logout` y
  `/cambiar-contrasena`. El texto del 403 está fijado por prueba porque el
  frontend depende de él.
- Los cuerpos usan `SecretStr` y `hide_input_in_errors=True`; `SanitizedRoute`
  (`app/api/validation.py`, compartida con conductores) evita que un 422 repita
  la entrada. Las pruebas comprueban que ninguna respuesta, log ni auditoría
  contiene una contraseña.
- La auditoría guarda solo `{"sesiones_revocadas": n}`.

### Migración 0012

`0012_password_reset` cuelga de `0011_pedido_prioridad_index`: agrega
`debe_cambiar_contrasena BOOLEAN NOT NULL DEFAULT false` y
`contrasena_temporal_expira_en TIMESTAMPTZ NULL`, y amplía `ck_auditoria_accion`.
El downgrade se niega si existen auditorías con las acciones nuevas. ECL-73 también
crea una 0012: la que se integre segunda debe encadenarse después y conservar las
acciones de la otra, para que quede una sola cabeza.

## Script de restablecimiento de contraseña (ECL-78)

EN-013. Sirve para recuperar una cuenta cuando se pierde su contraseña en un
entorno local o de demo, incluida la del Administrador, que no puede
restablecerse a sí mismo con el botón de US-013.

```powershell
python -m scripts.reset_password --email administrador.demo@ecologistica.example
```

La contraseña nueva se pide dos veces con `getpass` y debe tener al menos 12
caracteres. Nunca se recibe por argumento ni variable de entorno, ni se imprime o
registra. En una sola transacción, igual que el cambio de la aplicación:

- guarda el hash Argon2id con `CredentialService.replace`;
- deja `debe_cambiar_contrasena=false` y limpia el vencimiento temporal, los
  intentos y el bloqueo;
- revoca todas las sesiones activas de la cuenta;
- audita `CONTRASENA_CAMBIADA` con `{"sesiones_revocadas": n}`, sin la
  contraseña ni el hash. El actor registrado es la propia cuenta, porque el
  script corre fuera de una sesión de la aplicación.

Termina con código 2, **sin modificar nada** y sin mostrar datos de la cuenta, si:

- `APP_ENV=production`;
- `DATABASE_URL` falta o su base no termina en `_demo` o `_local`;
- no hay una terminal interactiva;
- las contraseñas no coinciden, tienen menos de 12 caracteres o se cancela;
- el correo no existe.

Las primeras tres comprobaciones ocurren antes de pedir la contraseña o conectar.
La protección de la base está en `scripts/_guard.py` y es la misma del seed, que
la usa solo con `_demo`.

### Uso con Docker Compose

La imagen del backend no copia `scripts/`: se monta en solo lectura, como el seed.
`getpass` necesita una terminal, así que se usa `run -it`. Desde la raíz del
repositorio, con el stack actualizado a `main` (imagen reconstruida y migraciones
en `head`, porque el script usa la migración `0012_password_reset`):

```powershell
docker compose --env-file .env build backend
docker compose --env-file .env run --rm --no-deps backend python -m alembic upgrade head
docker compose --env-file .env run --rm --no-deps -it -v "${PWD}/backend/scripts:/app/scripts:ro" backend python -m scripts.reset_password --email administrador.demo@ecologistica.example
```

Al terminar imprime un texto fijo («contraseña actualizada; se cerraron las
sesiones activas de la cuenta»), sin el correo ni ningún valor derivado de la
contraseña. El número de sesiones revocadas queda solo en la auditoría. Las pruebas están
en `tests/unit/test_reset_password.py` y
`tests/integration/test_reset_password_script.py`.

## Incidencias (ECL-73)

ST-040, subtarea de US-012 (ECL-18). El conductor registra incidencias de su
jornada y el Administrador o el Operador consultan las pendientes de validación.
Lo consumen ECL-74 (José) y ECL-75 (Giancarlo).

Implementa la [BDD de ECL-72](<../docs/02 Planificación/BDD/ECL-72-ST-039-incidencias.md>),
aprobada por Julio en el PR #63 (escenarios I01–I16; I12, offline 10/10, es de
la interfaz). Los tipos, las severidades y los límites están en un solo módulo,
`app/core/incidencias.py`, del que toman sus valores el modelo, la migración
`0013_incidencias`, los esquemas, el servicio y las pruebas. Las pruebas llevan
el ID del escenario en su nombre (`test_I11_...`) para mapearlas en ECL-76.

### Endpoints

| Método y ruta | Acceso | Respuesta |
|---|---|---|
| `POST /conductor/incidencias` | `incidencias.crear`, alcance propio, **solo rol Conductor** con perfil vinculado | 201 con `{incidencia_id, operation_id, estado, registrada_en}`; 200 con la misma respuesta ante un reenvío equivalente; 409 con contenido distinto; 422 con datos inválidos, sin repetir lo enviado; 403 genérico para otros roles, sin perfil vinculado o con una parada ajena; 401 sin sesión |
| `GET /incidencias?estado=PENDIENTE_VALIDACION&page=1&page_size=20` | `incidencias.consultar`, alcance general (Administrador y Operador) | Orden `ocurrida_en` descendente con desempate por `incidencia_id` ascendente. `page` ≥ 1 y `page_size` entre 1 y 100 (20 por defecto); otro estado o paginación inválida → 422. Una página posterior a la última devuelve 200 con `items: []` y el total real. El conductor aparece solo con `conductor_id` y `nombre`. Analista, Auditor y Conductor reciben 403 sin datos |

```json
{
  "operation_id": "uuid versión 4 del cliente (cola offline)",
  "tipo": "TRAFICO | AVERIA | ACCIDENTE | CLIMA | SEGURIDAD | OTRO",
  "severidad": "BAJA | MEDIA | ALTA",
  "ocurrida_en": "2026-10-27T09:15:00-05:00",
  "latitud": -12.0464,
  "longitud": -77.0428,
  "parada_id": "uuid opcional de una parada del propio itinerario",
  "observacion": "opcional, de 0 a 500 puntos de código Unicode"
}
```

Las fechas de las respuestas se devuelven en hora de Lima (`-05:00`).

### Reglas

- **Validación estricta (I04–I07):**
  - `operation_id` debe ser un UUID versión 4.
  - `tipo` y `severidad` admiten solo los valores exactos del catálogo.
  - Latitud en [-90, 90] y longitud en [-180, 180]: aceptan enteros y rechazan
    cadenas, booleanos, NaN e infinito.
  - `ocurrida_en` debe llevar zona horaria. Se admite hasta 5 min en el futuro
    según el reloj del servidor, inclusive, y no hay antigüedad máxima, para que
    la cola offline pueda entregar reportes viejos.
  - `observacion` no se recorta ni se trunca; omitida o `null` se guarda como
    `""`.
  - Los campos extra (`conductor_id`, `usuario_id`, `reportada_por`, `ruta_id`,
    `estado`) devuelven 422.
- **Orden de comprobación:**
  1. esquema y permisos;
  2. perfil vinculado;
  3. idempotencia;
  4. solo para una operación nueva, la hora futura y la parada. Una parada
     inexistente devuelve 422 genérico y una de otro conductor, 403 genérico.

  Así un reenvío nunca invalida un alta ya hecha.
- **Idempotencia por `(conductor, operation_id)` (I13, I16):**
  - Hay equivalencia si coinciden el mismo instante en UTC, las mismas
    coordenadas numéricas (`-12 == -12.0`), los opcionales normalizados y la
    observación exacta, incluidos espacios y mayúsculas.
  - El mismo UUID de otro conductor es una operación independiente y nunca
    devuelve el registro ajeno.
  - Si dos primeros envíos llegan a la vez, la restricción única decide: el
    perdedor relee el registro y responde 200 (o 409 si el contenido difiere),
    nunca 5xx.
- **Auditoría (RN-015):** `INCIDENCIA_REGISTRADA` va en la misma transacción que
  el alta, con actor = usuario conductor y entidad = incidencia. El detalle solo
  guarda `tipo`, `severidad`, `con_parada` y `con_observacion`.

### Formato del 422 (para el formulario, ECL-74)

Todos los 422 de estos endpoints tienen la misma forma: identifican el campo y
un código estable, **sin repetir el valor enviado**, sin `input` ni `ctx`.

```json
{
  "detail": [
    {
      "loc": ["body", "ocurrida_en"],
      "type": "fecha_futura_fuera_de_tolerancia",
      "msg": "Entrada inválida"
    }
  ]
}
```

- **`loc`:** indica el campo, por ejemplo `["body", "latitud"]` o
  `["query", "page_size"]`. El formulario lo usa para marcar el campo.
- **`type`:** es el código del error. Los de esquema son los de Pydantic: por
  ejemplo, `missing`, `timezone_aware` (fecha sin zona), `less_than_equal`,
  `float_type`, `uuid_version`, `enum` y `extra_forbidden`. Los de la API son:
  - `fecha_futura_fuera_de_tolerancia`: `ocurrida_en` pasa del reloj del
    servidor + 5 min (I05);
  - `parada_invalida`: `parada_id` no existe (I07).
- **`msg`:** siempre es `"Entrada inválida"`; el texto para el usuario lo pone el
  cliente según `loc` y `type`.
- Un estado distinto de `PENDIENTE_VALIDACION` en `GET /incidencias` responde
  `{"detail": "Estado no admitido en este listado"}`.

### Rol en el registro (I08)

La matriz RBAC global concede `incidencias.crear` también al Operador. El
endpoint `POST /conductor/incidencias` admite **solo el rol Conductor**, mediante
`require_permission(..., roles={Rol.CONDUCTOR})`, sin modificar la matriz.

- **Operador:** recibe 403 antes de llegar al servicio, aunque tenga un perfil
  de conductor vinculado.
- **Auditoría:** la denegación se registra como `AUTORIZACION_DENEGADA` con
  motivo `SIN_PERMISO`.

### Jornada de la parada (I03): pendiente

La BDD pide que la parada sea del itinerario **y de la jornada** del reporte. El
modelo actual no permite comprobar la jornada de forma confiable:

- no existe una entidad de jornada ni de ruta;
- el itinerario (`driver_stop_assignment`) no tiene fecha;
- `pedido_id` es opcional;
- la ventana de un pedido puede cruzar la medianoche de Lima.

Hoy solo se valida que la parada exista y sea del conductor. La comprobación de
jornada queda pendiente del modelo de rutas, sujeta a la ratificación del
aplazamiento y a su ticket de seguimiento. **I03 no está cubierto por
completo.**

### Migración 0013

`0013_incidencias` cuelga de `0012_password_reset` y amplía
`ck_auditoria_accion` con `INCIDENCIA_REGISTRADA`, conservando las acciones de
0012.

- **Tabla `incidencia`:**
  - restricción única `(conductor_id, operation_id)`;
  - `ubicacion` como `geography(Point,4326)`;
  - `observacion` NOT NULL con valor por defecto `''`;
  - índice `(estado, ocurrida_en DESC)`;
  - CHECK de tipo, severidad, estado y observación.
- **Vínculo con el conductor y la ruta:** la incidencia se vincula siempre al
  conductor. Sin parada no tiene ruta (ratificado por Julio). `ruta_id` llegará,
  nullable, con el modelo de rutas; ver
  [Base de datos V_1_1_0](<../docs/01 Inicio/11. Base de datos V_1_1_0.md>).
- **Downgrade protegido:** se niega mientras existan incidencias o su
  auditoría.

### Datos de demostración

`scripts/seed_demo.py` agrega 3 incidencias ficticias de `conductor.demo`,
pendientes de validación: avería, tráfico y clima en Lima, la primera asociada
a su parada 1. Su `operation_id` es determinista: se deriva con `uuid5` y se
marca como versión 4, así que volver a sembrar no las duplica.

[← Volver al README principal](../README.md)
