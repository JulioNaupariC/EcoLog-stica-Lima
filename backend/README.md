# Backend EcoLogística Lima — ECL-27

Bootstrap FastAPI con SQLAlchemy síncrono y Psycopg 3. No incluye entidades de
negocio, autenticación, Docker, Redis ni pipelines.

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

Alembic obtiene la URL del entorno y usa `Base.metadata`. No hay revisiones ni
tablas de negocio. `alembic heads` y `alembic history` deben estar vacíos.
Las futuras migraciones se ejecutarán explícitamente, nunca al arrancar HTTP.

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
