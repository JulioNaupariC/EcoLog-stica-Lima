# EcoLogística Lima

**Optimizador de Rutas Sostenibles para DistriRápido S.A.C.**

Repositorio de documentación y desarrollo del proyecto académico EcoLogística Lima. La solución propone una plataforma web para gestión operativa, optimización VRPTW/Green VRP, seguimiento geográfico, analítica y reportes de sostenibilidad.

## Equipo

| Integrante | Rol |
|---|---|
| Julio Armando Naupari Camarena | Líder del proyecto |
| Frank Roy Yupanqui Acevedo | Analista de requisitos |
| Giancarlo Marcio Soto Escobar | Diseñador UX/UI |
| Antony Munive Ríos | Desarrollador backend y optimización |
| José Samuel Delgadillo Pantoja | Desarrollador frontend y aseguramiento de calidad |

## Arranque local con Docker Compose — ECL-29

Este entorno local levanta PostgreSQL 16/PostGIS 3.5, la API FastAPI y el
frontend Vite. No incluye Redis, worker de optimización, datos de ejemplo ni
servicios de producción. Requiere Docker con el daemon activo y Docker Compose
v2. Los puertos 8000 y 5173 del host deben estar libres. Los servicios web se
publican únicamente en `127.0.0.1`; PostgreSQL no publica un puerto al host.
Las imágenes base fijadas son `postgis/postgis:16-3.5`,
`python:3.12.10-slim-bookworm` y `node:22.18.0-bookworm-slim`. El backend usa
`requirements.lock` y el frontend `package-lock.json` mediante `npm ci`.
Sus digests de manifiesto están fijados en `compose.yaml` y los dos Dockerfile;
al actualizarlos se debe comprobar de nuevo la compatibilidad y el build.

Desde la raíz del repositorio, verificar antes de iniciar que no existe otro
proyecto Compose con nombre `ecologistica-lima-ecl29` y que el volumen
`ecologistica-lima-ecl29_postgis_data`, si existe, pertenece a este proyecto.
No reutilizar un volumen de origen desconocido ni detener otros contenedores:

```powershell
docker info --format '{{.ServerVersion}}'
docker compose ls --all
docker volume ls --filter name=ecologistica-lima-ecl29_postgis_data
netstat -ano -p tcp | Select-String -Pattern ':8000\s',':5173\s'
```

Crear `.env` **solo si todavía no existe** y completar sus valores privados.
`.env` de la raíz está ignorado por Git; es distinto de `backend/.env` y no se
copia a ninguna imagen. Nunca publicar el archivo ni la salida de una
configuración Compose expandida.

```powershell
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

`POSTGRES_DB`, `POSTGRES_USER` y `POSTGRES_PASSWORD` inicializan la base solo
cuando el volumen está vacío. `DATABASE_URL` debe usar esos mismos valores y el
host **interno** `db:5432`, por ejemplo con el formato
`postgresql+psycopg://USUARIO:CONTRASENA_CODIFICADA@db:5432/BASE`.
Codificar en porcentaje los caracteres reservados del usuario o contraseña
(por ejemplo, `@` como `%40`, `:` como `%3A`, `/` como `%2F` y `%` como `%25`).
Si un valor del archivo `.env` contiene `$`, usar comillas simples para evitar
la interpolación de Compose. No ejecutar `docker compose config` sin `--quiet`
al trabajar con credenciales privadas.
Un cambio de credenciales en `.env` no modifica una base ya inicializada.

La siguiente secuencia valida la configuración sin imprimirla, construye las
imágenes, inicia primero la base, comprueba PostgreSQL/PostGIS y ejecuta las
migraciones **explícitamente**. Comparar `alembic current` y `alembic heads`:
ambos deben indicar la misma revisión para confirmar que no quedan revisiones
Alembic por aplicar.

```powershell
docker compose --env-file .env config --quiet
docker compose --env-file .env build
docker compose --env-file .env up -d --wait db
docker compose --env-file .env run --rm --no-deps backend python -m app.db.check
docker compose --env-file .env run --rm --no-deps backend python -m alembic upgrade head
docker compose --env-file .env run --rm --no-deps backend python -m alembic current
docker compose --env-file .env run --rm --no-deps backend python -m alembic heads
docker compose --env-file .env up -d --wait backend frontend
docker compose --env-file .env ps
```

En la imagen PostGIS 16-3.5, `alembic check` detectó propuestas de eliminación
de tablas e índices instalados con las extensiones espaciales (36 tablas y 28
índices en la validación de ECL-29), pese a que `current` y `heads` coinciden.
No aplicar esas eliminaciones. La comprobación de deriva de modelos mediante
autogeneración queda pendiente de excluir correctamente esos objetos en un
trabajo de migraciones separado; no forma parte del arranque de ECL-29.

Abrir `http://127.0.0.1:5173/` para la aplicación,
`http://127.0.0.1:8000/health` para salud del proceso y
`http://127.0.0.1:8000/docs` para OpenAPI. Vite sirve desde el contenedor,
pero el navegador llama al API mediante `http://127.0.0.1:8000`; el nombre
`backend` solo se resuelve dentro de la red Compose. El CORS existente permite
el origen exacto `http://127.0.0.1:5173`. Mantener `127.0.0.1` en ambos lados
para la cookie de sesión `SameSite=Strict`.

El healthcheck del frontend verifica su proceso. El de API utiliza
`/health/ready` y exige una lectura `SELECT 1` en PostgreSQL (ECL-60).
`/health` sigue disponible como liveness independiente de BD. Las métricas
protegidas y los sondeos se describen en
[VALIDACION_ST034.md](backend/VALIDACION_ST034.md). El healthcheck de base usa `pg_isready`; por sí solo no acredita PostGIS ni el
esquema. Para ello sirven `app.db.check`, la comparación `alembic current` /
`alembic heads` y una inspección de las tablas de aplicación.
Si falla un paso, consultar `docker compose --env-file .env ps` y los logs del
servicio afectado, revisándolos antes de compartirlos. No seguir con el siguiente
paso hasta corregir el error. No se crean usuarios automáticamente; el login
requiere una cuenta de prueba autorizada ya existente.

Para verificar que el **esquema** persiste, apagar, volver a iniciar solo la
base, comparar las revisiones y comprobar las tablas. Esa comprobación no
acredita persistencia de datos de negocio:

```powershell
docker compose --env-file .env down
docker compose --env-file .env up -d --wait db
docker compose --env-file .env run --rm --no-deps backend python -m app.db.check
docker compose --env-file .env run --rm --no-deps backend python -m alembic current
docker compose --env-file .env run --rm --no-deps backend python -m alembic heads
docker compose --env-file .env run --rm --no-deps backend python -c "from sqlalchemy import inspect; from app.core.config import Settings; from app.db.session import build_engine; engine=build_engine(Settings()); names=set(inspect(engine).get_table_names()); expected={'usuario','auditoria','sesion','vehiculo','cliente','pedido','alembic_version'}; print('application_schema_present=',expected <= names); engine.dispose()"
```

Apagar conservando los datos con:

```powershell
docker compose --env-file .env down
```

No usar `down -v` ni borrar volúmenes. No hay bind mounts de código: después de
cambiar código hay que repetir `docker compose --env-file .env build` y levantar
de nuevo los servicios. Las instrucciones de arranque sin Docker siguen en
[`backend/README.md`](backend/README.md) y [`frontend/README.md`](frontend/README.md).

## Fase 01: Inicio y línea base

- [Selección del enfoque del proyecto V_1_0_0](<docs/01 Inicio/01. Selección del enfoque del proyecto V_1_0_0.md>)  
- [Acta de constitución V_1_1_0](<docs/01 Inicio/02. Acta de constitución V_1_1_0.md>)
- [Declaración de la visión V_1_0_0](<docs/01 Inicio/03. Declaración de la visión V_1_0_0.md>)
- [Registro de supuestos y restricciones V_1_0_0](<docs/01 Inicio/04. Registro de supuestos y restricciones V_1_0_0.md>)
- [Registro de interesados V_1_0_0](<docs/01 Inicio/05. Registro de interesados V_1_0_0.md>)
- [Requisitos funcionales V_1_0_0](<docs/01 Inicio/06. Requisitos funcionales V_1_0_0.md>)
- [Requisitos no funcionales V_1_1_0](<docs/01 Inicio/07. Requisitos no funcionales V_1_1_0.md>)
- [Usuarios V_1_0_0](<docs/01 Inicio/08. Usuarios V_1_0_0.md>)
- [Reglas de negocio V_1_0_0](<docs/01 Inicio/09. Reglas de negocio V_1_0_0.md>)
- [Stack tecnológico V_1_0_0](<docs/01 Inicio/10. Stack tecnológico V_1_0_0.md>)
- [Base de datos V_1_0_0](<docs/01 Inicio/11. Base de datos V_1_0_0.md>)
- [Modelo C4 V_1_0_0](<docs/01 Inicio/12. Modelo C4 V_1_0_0.md>)
- [Restricciones V_1_0_0](<docs/01 Inicio/13. Restricciones V_1_0_0.md>)

## Fase 02: Planificación del Proyecto

- [01 Transformando a ágil V_1_0_0](<docs/02 Planificación/01 Transformando a ágil V_1_0_0.md>)
- [02 Artefactos Jira V_1_0_0](<docs/02 Planificación/02 Artefactos Jira V_1_0_0.md>)
- [03 Registro de riesgos V_1_0_0](<docs/02 Planificación/03 Registro de riesgos V_1_0_0.md>)
- [04 Presupuesto del proyecto V_1_0_0](<docs/02 Planificación/04 Presupuesto del proyecto V_1_0_0.md>)

### Estado de Jira — fotografía de planificación inicial

- Proyecto: `ECL` — Company-managed Scrum.
- Board: `ECL board`.
- Release: `v1.0.0-MVP`.
- Product Backlog ejecutable: 20 elementos / 115 Story Points.
- Sprint 1: `Sprint 1 - Base Operativa`, 28 Story Points, 18 subtareas técnicas.
- Periodo planificado original: 11/09/2026 – 25/09/2026.

> Las evidencias visuales de Jira se encuentran disponibles en
> `docs/02 Planificación/evidencias-jira/` y están integradas en
> [`02 Artefactos Jira V_1_0_0.md`](<docs/02 Planificación/02 Artefactos Jira V_1_0_0.md>).

## Fase 03: Implementación — entregables del Sprint 1

- [01 Informe de estado del proyecto V_1_0_0](<docs/03 Implementación/01 Informe de estado del proyecto V_1_0_0.md>)
- [02 Registro de Impedimentos V_1_0_0](<docs/03 Implementación/02 Registro de Impedimentos V_1_0_0.md>)
- [03 Revisión del Sprint V_1_0_0](<docs/03 Implementación/03 Revisión del Sprint V_1_0_0.md>)
- [04 Retrospectiva del Sprint V_1_0_0](<docs/03 Implementación/04 Retrospectiva del Sprint V_1_0_0.md>)

### Actualización operativa — 02/10/2026

Sprint 1 sigue activo, con fin reprogramado en Jira al **02/10/2026 16:00 America/Lima**. La consulta actual registra **28/28 SP** de padres y **19/19 subtareas** finalizadas, como medidas separadas. ECL-29 y los entregables preparatorios están integrados mediante PR #20 y #21. Esto no acredita demo, retrospectiva ni aceptación. Véase la [adenda de Artefactos Jira V_1_0_1](<docs/02 Planificación/02 Artefactos Jira V_1_0_1.md>) para fuentes, límites y pendientes.
