# Backend EcoLogística Lima — ECL-27 / ECL-30 / ECL-31

Bootstrap FastAPI con SQLAlchemy síncrono y Psycopg 3. Incluye el modelo de
credenciales Usuario, hashing Argon2id y autorización RBAC con auditoría persistente.
No incluye login HTTP, sesiones, integración HTTP de autorización, Docker,
Redis ni pipelines.

## Instalación (PowerShell)

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

Codificar caracteres especiales de usuario/contraseña en la URL. No registrar
credenciales ni incluirlas en comandos compartidos. Usar un usuario de aplicación
con privilegios mínimos; las operaciones administrativas usan otro usuario.

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

## Pruebas de migración y persistencia

Configurar privadamente `TEST_DATABASE_URL` en el entorno o `.env`, apuntando a
una base desechable cuyo nombre termine en `_test` y sea distinto del nombre de
la base de desarrollo. No se usa `DATABASE_URL` como sustituto.

El esquema public debe estar vacío: solo se admiten `spatial_ref_sys` de PostGIS
y una tabla `alembic_version` vacía. Las pruebas crean/eliminan `usuario` y `auditoria`, y
pueden dejar la tabla de control de Alembic vacía. No ejecutarlas contra datos
que se desee conservar. No se realizan downgrades automáticos al iniciar HTTP.

```powershell
.venv/Scripts/python -m pytest tests/integration -q
```

Sin TEST_DATABASE_URL se omiten las pruebas destructivas y se reporta downgrade
pendiente. La prueba de conectividad PostGIS existente usa DATABASE_URL y es
de solo lectura. No se considera una omisión como prueba aprobada.

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
