# Backend EcoLogística Lima — ECL-27 / ECL-30

Bootstrap FastAPI con SQLAlchemy síncrono y Psycopg 3. Incluye el modelo de
credenciales Usuario y hashing Argon2id. No incluye login HTTP, sesiones,
autorización, auditoría, Docker, Redis ni pipelines.

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
implementará RBAC/auditoría; ECL-36 coordinará estado de cuenta, bloqueo RN-001,
login y sesión. No hay JWT, cookies, contadores ni permisos en este incremento.

## Pruebas de migración y persistencia

Configurar privadamente `TEST_DATABASE_URL` en el entorno o `.env`, apuntando a
una base desechable cuyo nombre termine en `_test` y sea distinto del nombre de
la base de desarrollo. No se usa `DATABASE_URL` como sustituto.

El esquema public debe estar vacío: solo se admiten `spatial_ref_sys` de PostGIS
y una tabla `alembic_version` vacía. Las pruebas crean y eliminan `usuario`, y
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
