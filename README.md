# EcoLogística Lima

**Optimizador de Rutas Sostenibles para DistriRápido S.A.C.**

[![CI](https://github.com/JulioNaupariC/EcoLog-stica-Lima/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/JulioNaupariC/EcoLog-stica-Lima/actions/workflows/ci.yml)
[![CodeQL](https://github.com/JulioNaupariC/EcoLog-stica-Lima/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/JulioNaupariC/EcoLog-stica-Lima/actions/workflows/codeql.yml)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=JulioNaupariC_EcoLog-stica-Lima&metric=alert_status)](https://sonarcloud.io/project/overview?id=JulioNaupariC_EcoLog-stica-Lima)
[![Cobertura](https://sonarcloud.io/api/project_badges/measure?project=JulioNaupariC_EcoLog-stica-Lima&metric=coverage)](https://sonarcloud.io/component_measures?id=JulioNaupariC_EcoLog-stica-Lima&metric=coverage)

Repositorio de documentación y desarrollo del proyecto académico EcoLogística Lima. La solución propone una plataforma web para gestión operativa, optimización VRPTW/Green VRP, seguimiento geográfico, analítica y reportes de sostenibilidad.

## Estructura del repositorio

El proyecto está organizado en cuatro carpetas principales. La infraestructura
local (`compose.yaml`) está en la raíz y la integración continua en `.github/`.

| Carpeta | Contenido | Tecnologías |
|---|---|---|
| `backend/` | API REST, lógica de negocio, migraciones y pruebas | ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white) ![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white) ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white) ![Alembic](https://img.shields.io/badge/Alembic-6BA81E?style=for-the-badge) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white) ![PostGIS](https://img.shields.io/badge/PostGIS-2A6F97?style=for-the-badge) ![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white) |
| `frontend/` | Aplicación web de Operación y del conductor | ![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB) ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white) ![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white) ![Vitest](https://img.shields.io/badge/Vitest-6E9F18?style=for-the-badge&logo=vitest&logoColor=white) ![ESLint](https://img.shields.io/badge/ESLint-4B32C3?style=for-the-badge&logo=eslint&logoColor=white) |
| `docs/` | Documentación por fase, planificación y evidencias | ![Markdown](https://img.shields.io/badge/Markdown-000000?style=for-the-badge&logo=markdown&logoColor=white) ![Jira](https://img.shields.io/badge/Jira-0052CC?style=for-the-badge&logo=jira&logoColor=white) |
| `scripts/` | Verificación de la documentación y automatización | ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) |
| Raíz y `.github/` | Contenedores, CI, análisis de seguridad y calidad | ![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white) ![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white) ![CodeQL](https://img.shields.io/badge/CodeQL-181717?style=for-the-badge&logo=github&logoColor=white) ![SonarQube Cloud](https://img.shields.io/badge/SonarQube%20Cloud-126ED3?style=for-the-badge&logo=sonarqubecloud&logoColor=white) |

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
[VALIDACION_ST034.md](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST034.md>). El healthcheck de base usa `pg_isready`; por sí solo no acredita PostGIS ni el
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

## Problemas frecuentes del entorno local — ECL-90

Ejecutar desde la raíz del clon, antes de levantar una segunda instancia:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File scripts/verificar_entorno.ps1
```

El verificador devuelve **0** si encuentra Docker/Compose, un motor Linux accesible,
`.env` y los puertos disponibles; devuelve **1** si alguna comprobación falla.
Solo comprueba la existencia de `.env`, sin leerlo. No configura credenciales,
no arranca servicios ni acredita login o integración. Si la app ya está levantada,
es normal que marque los puertos como ocupados: revisar su propietario antes de
intentar otro arranque.

| Síntoma | Causa o diagnóstico | Resolución / comando |
|---|---|---|
| `docker` no se reconoce | Docker no está instalado o su CLI no está en PATH | Comprobar `Get-Command docker`; instalar Docker Desktop según su guía oficial y abrir otra consola. No basta con instalar solo el cliente. |
| `failed to connect ... dockerDesktopLinuxEngine` | Docker Desktop está cerrado, el motor aún no inició o el contexto es incorrecto | Iniciar Docker Desktop desde Inicio; comprobar `docker context ls` y `docker info --format '{{.OSType}}'`. Continuar cuando el último devuelva `linux`; cambiar a contenedores Linux desde Docker Desktop si corresponde. |
| Compose no existe o es v1 | Falta el complemento Compose v2 | Comprobar `docker compose version --short` y actualizar Docker Desktop. Usar `docker compose`, conforme al arranque del proyecto. |
| Fallo del backend WSL | WSL sin preparar, desactualizado o virtualización deshabilitada | Diagnosticar con `wsl --status`, `wsl --version` y `wsl --list --verbose`. Si corresponde, `wsl --update`; en un equipo nuevo, preparar WSL 2 según Microsoft y reiniciar cuando lo solicite. No reiniciar WSL mientras haya cargas activas. |
| Puerto 8000 o 5173 ocupado | Otra app o un clon anterior ya publica ese puerto | Comprobar `Get-NetTCPConnection -State Listen -LocalPort 8000,5173` y `docker ps --format '{{.Names}} {{.Ports}}'`. Reutilizar la instancia correcta o detener solo los servicios propios identificados. No ejecutar `taskkill` indiscriminadamente. |
| Otro clon usa el nombre Compose del README | Compose agrupa recursos por nombre de proyecto, no solo por carpeta | Revisar `docker compose ls --all`. Para una instancia nueva aislada añadir `-p ecologistica-lima-ecl90` a **todos** sus comandos Compose; también necesita puertos libres. No reutilizar ni borrar volúmenes de otro clon. |
| `.env` ausente | La configuración privada no viaja por Git | Ejecutar el bloque condicional de copia de `.env.example` del arranque anterior y completar los valores en un editor local. Validar con `docker compose --env-file .env config --quiet`, sin imprimir configuración expandida. |
| Configuración válida pero BD rechaza la conexión | URL/credenciales no coinciden, uso de `localhost` dentro de Docker o credenciales cambiadas sobre un volumen existente | Revisar privadamente `DATABASE_URL`: en Compose el host es `db:5432`; codificar caracteres reservados. Ejecutar `docker compose --env-file .env run --rm --no-deps backend python -m app.db.check`. Usar las credenciales originales del volumen o una base nueva aislada, sin borrar datos. |
| `python` abre Microsoft Store o no existe | Alias de Windows o Python ausente | Comprobar `py -0p`; si Python 3.12 está instalado, usar `py -3.12` y el ejecutable de `.venv`. La ruta Docker de la guía ECL-90 permite ejecutar integración sin Python en el host. |
| «La ejecución de scripts está deshabilitada» | Política de ejecución de PowerShell | Comprobar `Get-ExecutionPolicy -List`; para estos scripts locales revisados, usar la invocación con `-ExecutionPolicy RemoteSigned` mostrada arriba, limitada al proceso. Si hay una directiva organizativa, solicitar la alternativa autorizada; no cambiarla globalmente. |
| Falta `pytest` en el contenedor de la API | La imagen de ejecución instala `requirements.lock`, no las dependencias de pruebas | Usar la imagen temporal con `requirements-dev.lock` de la guía ECL-90, o instalar esas dependencias en el `.venv` del backend. La imagen API tampoco copia `tests/`. |
| `TEST_DATABASE_URL is required` / esquema no vacío | Falta una base exclusiva de pruebas o se está apuntando a desarrollo/demo | Seguir la integración aislada de ECL-90: base vacía con sufijo `_test`, distinta de desarrollo. No sustituirla por la demo ni aplicar sus downgrades a datos de trabajo. |
| Build/procesos terminan por falta de memoria | RAM insuficiente o límites de Docker/WSL | Comprobar `docker stats --no-stream` y los recursos de Docker Desktop; cerrar cargas prescindibles propias y revisar los requisitos del proveedor. No se midió un fallo de memoria en los equipos del grupo. |

[Guía, evidencia local y tabla A11 para Frank](<docs/03 Implementación/Sprint 04/guias/GUIA_ENTORNO_LOCAL_ECL90.md>).
Los casos observados y los diagnósticos preventivos se distinguen en esa guía.
Las indicaciones de Docker, WSL y PowerShell se contrastaron con las guías de
[Docker Desktop para Windows](https://docs.docker.com/desktop/setup/install/windows-install/),
[comandos WSL de Microsoft](https://learn.microsoft.com/en-us/windows/wsl/basic-commands)
y [políticas de ejecución de PowerShell](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies).

## Fase 01: Inicio y línea base

- [Selección del enfoque del proyecto V_1_0_0](<docs/01 Inicio/01. Selección del enfoque del proyecto V_1_0_0.md>)  
- [Acta de constitución V_1_1_0](<docs/01 Inicio/02. Acta de constitución V_1_1_0.md>)
- [Declaración de la visión V_1_0_0](<docs/01 Inicio/03. Declaración de la visión V_1_0_0.md>)
- [Registro de supuestos y restricciones V_1_0_0](<docs/01 Inicio/04. Registro de supuestos y restricciones V_1_0_0.md>)
- [Registro de interesados V_1_0_0](<docs/01 Inicio/05. Registro de interesados V_1_0_0.md>)
- [Requisitos funcionales V_1_1_0](<docs/01 Inicio/06. Requisitos funcionales V_1_1_0.md>)
- [Requisitos no funcionales V_1_2_0](<docs/01 Inicio/07. Requisitos no funcionales V_1_2_0.md>)
- [Usuarios V_1_0_0](<docs/01 Inicio/08. Usuarios V_1_0_0.md>)
- [Reglas de negocio V_1_1_0](<docs/01 Inicio/09. Reglas de negocio V_1_1_0.md>)
- [Stack tecnológico V_1_0_0](<docs/01 Inicio/10. Stack tecnológico V_1_0_0.md>)
- [Base de datos V_1_1_0](<docs/01 Inicio/11. Base de datos V_1_1_0.md>)
- [Modelo C4 V_1_0_0](<docs/01 Inicio/12. Modelo C4 V_1_0_0.md>)
- [Restricciones V_1_0_0](<docs/01 Inicio/13. Restricciones V_1_0_0.md>)

## Fase 02: Planificación del Proyecto

- [01 Transformando a ágil V_1_0_0](<docs/02 Planificación/01 Transformando a ágil V_1_0_0.md>)
- [02 Artefactos Jira V_1_0_0](<docs/02 Planificación/02 Artefactos Jira V_1_0_0.md>)
- [03 Registro de riesgos V_1_0_0](<docs/02 Planificación/03 Registro de riesgos V_1_0_0.md>)
- [02 Artefactos Jira V_1_0_1 — adenda operativa del Sprint 1](<docs/02 Planificación/02 Artefactos Jira V_1_0_1.md>)
- [04 Presupuesto del proyecto V_1_0_0](<docs/02 Planificación/04 Presupuesto del proyecto V_1_0_0.md>)

### Especificaciones BDD del Sprint 2

- [ECL-47 / ST-021 — Reglas y BDD de conductores](<docs/02 Planificación/BDD/ECL-47-ST-021-conductores.md>)
- [ECL-51 / ST-025 — Reglas y BDD de preferencias de entrega](<docs/02 Planificación/BDD/ECL-51-ST-025-preferencias-entrega.md>)
- ECL-71 — Verificación para ratificación: [conductores](<docs/02 Planificación/BDD/ECL-47-ST-021-conductores.md>) y [preferencias de entrega](<docs/02 Planificación/BDD/ECL-51-ST-025-preferencias-entrega.md>) (aprobadas por Julio, PR #64).

### Especificaciones BDD del Sprint 3

- [ECL-72 / ST-039 — Reglas y BDD de incidencias (aprobada por Julio, PR #63)](<docs/02 Planificación/BDD/ECL-72-ST-039-incidencias.md>)

### Especificaciones BDD del Sprint 4

- ECL-97 — BDD US-006, US-008 y US-009 ratificadas (v1.0.0); US-007 permanece como borrador de extensión: [ECL-12 / US-006 — Rutas optimizadas](<docs/02 Planificación/BDD/ECL-12-US-006-rutas-optimizadas.md>), [ECL-14 / US-008 — Mapa operativo](<docs/02 Planificación/BDD/ECL-14-US-008-mapa.md>), [ECL-15 / US-009 — Dashboard](<docs/02 Planificación/BDD/ECL-15-US-009-dashboard.md>) y [ECL-13 / US-007 — Reoptimización (extensión)](<docs/02 Planificación/BDD/ECL-13-US-007-reoptimizacion.md>).

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

## Fase 03: Implementación

Cada sprint tiene su propia sección con la misma estructura: **entregables** de su
rúbrica, **documentación técnica** y **estado de cierre**. Los documentos de un sprint
cerrado están en su carpeta `docs/03 Implementación/Sprint 0N/` y, además, en su rama
de cierre `sprint-N`.

| Sprint | Periodo (Jira) | Objetivo | Entregables | Rama de cierre |
|---|---|---|---|---|
| [Sprint 1 — Base Operativa](#sprint-1--base-operativa) | 11/09/2026–02/10/2026 | Base ejecutable y segura: autenticación, flota, pedidos y CI/CD | 01–04, en `docs/03 Implementación/Sprint 01/` | `sprint-1` |
| [Sprint 2 — Gestión operativa y experiencia del conductor](#sprint-2--gestión-operativa-y-experiencia-del-conductor) | 08/10/2026–23/10/2026 | Conductores y preferencias, experiencia móvil accesible y tolerante a desconexiones, capacidad y observabilidad | 01–04, en `docs/03 Implementación/Sprint 02/` | `sprint-2` |
| [Sprint 3 — Calidad y Seguridad](#sprint-3--calidad-y-seguridad) | 26/10/2026–30/10/2026 | Incidencias del conductor (US-012) y calidad, seguridad y accesibilidad acreditadas | 01–05 e Ítems 6–8, en `docs/03 Implementación/Sprint 03/` | `sprint-3` |

### Sprint 1 — Base Operativa

#### Entregables del Sprint 1

En [`docs/03 Implementación/Sprint 01/`](<docs/03 Implementación/Sprint 01/README.md>), en la versión entregada el 02/10/2026 (commit `58c3d9c`, rama `sprint-1`):

1. **Informe de estado:** [01 Informe de estado del proyecto V_1_0_0](<docs/03 Implementación/Sprint 01/01 Informe de estado del proyecto V_1_0_0.md>)
2. **Impedimentos:** [02 Registro de Impedimentos V_1_0_0](<docs/03 Implementación/Sprint 01/02 Registro de Impedimentos V_1_0_0.md>)
3. **Revisión del Sprint:** [03 Revisión del Sprint V_1_0_0](<docs/03 Implementación/Sprint 01/03 Revisión del Sprint V_1_0_0.md>)
4. **Retrospectiva:** [04 Retrospectiva del Sprint V_1_0_0](<docs/03 Implementación/Sprint 01/04 Retrospectiva del Sprint V_1_0_0.md>)

#### Documentación técnica del Sprint 1

[Índice del Sprint 1](<docs/03 Implementación/Sprint 01/README.md>)

El Sprint 1 no tiene documentación técnica propia. La instalación y las pruebas de esa
versión están en sus README, en la rama `sprint-1`:

- [Backend: instalación, pruebas y API](https://github.com/JulioNaupariC/EcoLog-stica-Lima/blob/sprint-1/backend/README.md)
- [Frontend: instalación, pruebas y verificaciones](https://github.com/JulioNaupariC/EcoLog-stica-Lima/blob/sprint-1/frontend/README.md)

#### Estado de cierre del Sprint 1

| Indicador | Resultado |
|---|---|
| Periodo | 11/09/2026–02/10/2026 (el cierre original del 25/09/2026 se reprogramó en Jira) |
| Story Points | 28 de 28 finalizados |
| Elementos de Jira | 6 elementos padre y 19 subtareas en «Finalizada» |
| Pull requests | #1–#22 (ECL-29 se integró en los PR #20 y #21) |
| Review | Programada el 02/10/2026 (inspección G5117), según su [Revisión del Sprint](<docs/03 Implementación/Sprint 01/03 Revisión del Sprint V_1_0_0.md>) |
| Observaciones | Las precisiones de Jira del sprint están en la [adenda de Artefactos Jira V_1_0_1](<docs/02 Planificación/02 Artefactos Jira V_1_0_1.md>) |

### Sprint 2 — Gestión operativa y experiencia del conductor

#### Entregables del Sprint 2

En [`docs/03 Implementación/Sprint 02/`](<docs/03 Implementación/Sprint 02/README.md>), en la versión de contenido 1.3.1 (la retrospectiva, en la 1.3.0):

1. **Informe de estado:** [01 Informe de estado del proyecto V_1_0_0](<docs/03 Implementación/Sprint 02/01 Informe de estado del proyecto V_1_0_0.md>)
2. **Impedimentos:** [02 Registro de Impedimentos V_1_0_0](<docs/03 Implementación/Sprint 02/02 Registro de Impedimentos V_1_0_0.md>)
3. **Revisión del Sprint:** [03 Revisión del Sprint V_1_0_0](<docs/03 Implementación/Sprint 02/03 Revisión del Sprint V_1_0_0.md>)
4. **Retrospectiva:** [04 Retrospectiva del Sprint V_1_0_0](<docs/03 Implementación/Sprint 02/04 Retrospectiva del Sprint V_1_0_0.md>)

#### Documentación técnica del Sprint 2

[Índice del Sprint 2 y mapa de reubicación](<docs/03 Implementación/Sprint 02/README.md>)

**Validaciones de subtareas**

- [ST-022 / ECL-48 — API de conductores](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST022.md>)
- [ST-023 / ECL-49 — Formulario y listado de conductores](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST023.md>)
- [ST-024 / ECL-50 — Pruebas de conductores](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST024.md>)
- [ST-026 / ECL-52 — API de preferencias de entrega](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST026.md>)
- [ST-027 / ECL-53 — Interfaz de preferencias](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST027.md>)
- [ST-028 / ECL-54 — Matriz de preferencias y clientes](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST028.md>)
- [ST-030 / ECL-56 — Interfaz móvil del conductor](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST030.md>)
- [ST-031 / ECL-57 — Responsive y accesibilidad](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST031.md>)
- [ST-032 / ECL-58 — Offline y sincronización](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST032.md>)
- [ST-034 / ECL-60 — Métricas de API y base de datos](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST034.md>)
- [ST-035 / ECL-61 — Carga y disponibilidad](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST035.md>)
- [ST-038 / ECL-64 — Optimización de consultas](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST038.md>)

**Informes**

- [ST-033 / ECL-59 — Plan de pruebas de capacidad y disponibilidad](<docs/03 Implementación/Sprint 02/informes/plan-pruebas-capacidad.md>)
- [ST-036 / ECL-62 — Resultados, SLA y operación](<docs/03 Implementación/Sprint 02/informes/INFORME_ST036.md>)
- [ST-037 / ECL-63 — Medición inicial de payload y consultas críticas](<docs/03 Implementación/Sprint 02/informes/INFORME_ST037.md>)

**Diseño**

- [ST-029 / ECL-55 — Diseño móvil del conductor (Giancarlo)](<docs/03 Implementación/Sprint 02/diseno/ST-029/README.md>) · [Guía visual](<docs/03 Implementación/Sprint 02/diseno/ST-029/guia-visual.md>) · [Evidencias visuales](<docs/03 Implementación/Sprint 02/diseno/ST-029/evidencias/README.md>)

**Guías**

- [ST-024 — Guía de integración](<docs/03 Implementación/Sprint 02/guias/GUIA_JOSE_ST024.md>)
- [ST-027 — Guía de integración](<docs/03 Implementación/Sprint 02/guias/GUIA_JOSE_ST027.md>)
- [ST-031 y ST-032 — Guía de integración](<docs/03 Implementación/Sprint 02/guias/GUIA_JOSE_ST031_ST032.md>)
- [ST-035 — Guía de integración](<docs/03 Implementación/Sprint 02/guias/GUIA_JOSE_ST035.md>)

#### Estado de cierre del Sprint 2

| Indicador | Resultado |
|---|---|
| Periodo | 08/10/2026–23/10/2026 |
| Story Points | 27 de 27 finalizados |
| Elementos de Jira | 5 elementos padre y 19 subtareas en «Finalizada» |
| Pull requests | #23–#57 y el cierre (#58) |
| Review | 09/10/2026, evaluada con 14/20 sin demostración; el parche posterior (PR #47–#57) y la demostración complementaria están en la [Revisión del Sprint](<docs/03 Implementación/Sprint 02/03 Revisión del Sprint V_1_0_0.md>) |
| Observaciones | Contrastados con sus criterios de aceptación, ECL-11 y ECL-25 cumplen; ECL-9, ECL-22 y ECL-23 cumplen parcialmente. La retrospectiva se realizó en clase el 23/10/2026 con el equipo completo, y la guía visual de ST-029 (ECL-55) se integró en el cierre |

### Sprint 3 — Calidad y Seguridad

#### Entregables del Sprint 3

En el orden de la rúbrica, todos en [`docs/03 Implementación/Sprint 03/`](<docs/03 Implementación/Sprint 03/README.md>):

1. **Revisión del Sprint:** [01 Revisión del Sprint V_1_0_0](<docs/03 Implementación/Sprint 03/01 Revisión del Sprint V_1_0_0.md>) (ECL-69)
2. **Retrospectiva:** [02 Retrospectiva del Sprint V_1_0_0](<docs/03 Implementación/Sprint 03/02 Retrospectiva del Sprint V_1_0_0.md>) (ECL-70)
3. **Calidad de código:** [03 Calidad de código V_1_0_0](<docs/03 Implementación/Sprint 03/03 Calidad de código V_1_0_0.md>) (ECL-65, SonarCloud) · [Evidencias](<docs/03 Implementación/Sprint 03/evidencias/ECL-65/README.md>)
4. **Seguridad OWASP:** [04 OWASP V_1_0_0](<docs/03 Implementación/Sprint 03/04 OWASP V_1_0_0.md>) (ECL-66, OWASP Top 10 2025) · [Evidencias](<docs/03 Implementación/Sprint 03/evidencias/ECL-66/README.md>)
5. **Accesibilidad WCAG:** [05 WCAG V_1_0_0](<docs/03 Implementación/Sprint 03/05 WCAG V_1_0_0.md>) (ECL-67, WCAG 2.1 AA) · [Evidencias finales](<docs/03 Implementación/Sprint 03/evidencias/ECL-67/comprobacion-final-20261027/README.md>) · [Registro inicial](<docs/03 Implementación/Sprint 03/evidencias/ECL-67/README.md>)
6. **Organización y `.gitignore`:** [Estructura del repositorio](#estructura-del-repositorio) y [`.gitignore`](.gitignore) (PR #66)
7. **Versionamiento documental:** [07 Coherencia y versionamiento documental V_1_0_0](<docs/03 Implementación/Sprint 03/07 Coherencia y versionamiento documental V_1_0_0.md>) (PR #68)
8. **Ubicación y enlaces bidireccionales:** [Índice del Sprint 3](<docs/03 Implementación/Sprint 03/README.md>); cada documento enlaza de vuelta a este README

#### Documentación técnica del Sprint 3

[Índice del Sprint 3](<docs/03 Implementación/Sprint 03/README.md>)

**Historias de usuario**

- [US-012 / ECL-18 — Matriz de validación I01–I16 (ECL-76)](<docs/03 Implementación/Sprint 03/validaciones/VALIDACION_US012.md>) · [Campaña real y evidencias de cierre](<docs/03 Implementación/Sprint 03/validaciones/evidencias/ECL-76/cierre-20261027/README.md>) · [Registro inicial](<docs/03 Implementación/Sprint 03/validaciones/evidencias/ECL-76/README.md>) · [Cuerpo del PR](<docs/03 Implementación/Sprint 03/validaciones/ECL-76-PR.md>)
- [US-013 / ECL-77 — Restablecer contraseña de un usuario](<docs/03 Implementación/Sprint 03/validaciones/VALIDACION_US013.md>) · [Evidencias visuales](<docs/03 Implementación/Sprint 03/validaciones/evidencias/ECL-77/README.md>)

**Validaciones de subtareas**

- [ST-041 / ECL-74 — Formulario móvil de incidencias](<docs/03 Implementación/Sprint 03/validaciones/VALIDACION_ST041.md>) · [Evidencias de Chrome y Firefox](<docs/03 Implementación/Sprint 03/validaciones/evidencias/ECL-74/README.md>) · [Cuerpo del PR](<docs/03 Implementación/Sprint 03/validaciones/ECL-74-PR.md>)
- [ST-042 / ECL-75 — Vista de incidencias pendientes para Operación](<docs/03 Implementación/Sprint 03/validaciones/VALIDACION_ST042.md>) · [Evidencias](<docs/03 Implementación/Sprint 03/validaciones/evidencias/ECL-75/README.md>)

**Guías**

- [EN-012 / ECL-68 — Guía de demostración en laboratorio](<docs/03 Implementación/Sprint 03/guias/GUIA_DEMO_LABORATORIO.md>) · [Diagnóstico técnico de la demostración](<docs/03 Implementación/Sprint 03/guias/DIAGNOSTICO_ECL68.md>)

#### Estado de cierre del Sprint 3

| Indicador | Resultado |
|---|---|
| Periodo | 26/10/2026–30/10/2026 |
| Story Points | 23 de 26 finalizados (30/10/2026) |
| Elementos de Jira | 14 de 15 en «Finalizada» (10 elementos padre y 5 subtareas); ECL-68 sigue en «In Review / QA» |
| Pull requests | #59–#85 (#84 registra la Review y #85 ordena `docs/03 Implementación` por sprint) |
| Review | 30/10/2026, demostración en vivo con los tres flujos; nota 19/20. Asistentes, evaluación y retroalimentación en la [Revisión del Sprint](<docs/03 Implementación/Sprint 03/01 Revisión del Sprint V_1_0_0.md>) |
| Observaciones | US-012 y US-013 están en `main`. Quality Gate de SonarCloud aprobado (cobertura 94,5 %, duplicación 0,0 %); la vulnerabilidad Media `S8703`, ya mitigada, se cierra en ECL-84 y los 4 code smells en ECL-87. La demo en una PC de laboratorio sin administrador (ECL-68) pasa al Sprint 4 |

### Ramas de cierre por sprint

Cada sprint conserva una rama con el estado final de su código y documentación,
como evidencia de lo entregado. Las ramas de trabajo se eliminan al cerrar cada
sprint; las tres ramas de cierre están protegidas contra cambios y borrado.

| Rama | Contenido | Commit de corte |
|---|---|---|
| `sprint-1` | Sprint 1 — Base Operativa (PR #1–#22) | `58c3d9c` (02/10/2026) |
| `sprint-2` | Sprint 2 — Gestión operativa y experiencia del conductor, con el parche posterior a la Review (PR #23–#57) y el cierre (PR #58) | `1d7666a` (25/10/2026) |
| `sprint-3` | Sprint 3 — Calidad y Seguridad (PR #59–#85), con el registro de la Review y la carpeta de cada sprint | `cf4bb2c` (03/11/2026) |
| `main` | Rama de integración | — |

### Sprint 4 — Green IT y documentación

#### Entregables del Sprint 4

[Índice del Sprint 4](<docs/03 Implementación/Sprint 04/README.md>)

Los siguientes comentarios reservan enlaces para entregas futuras.

<!-- ECL-100 Revisión -->

<!-- ECL-101 Retrospectiva -->

<!-- ECL-102 Calidad y OWASP -->

<!-- ECL-103 WCAG -->

<!-- ECL-104 Matriz final -->

<!-- ECL-26 Casos de referencia -->

<!-- ECL-105 Guía de demo -->

#### Documentación técnica del Sprint 4

- [Convenciones y glosario ECL-99](<docs/03 Implementación/Sprint 04/CONVENCIONES_Y_GLOSARIO_ECL99.md>)
- [Plantilla de Revisión y demostración ECL-99](<docs/03 Implementación/Sprint 04/PLANTILLA_REVISION_SPRINT4_ECL99.md>)
- [ECL-98 — Resolución de incidencias: contrato, concurrencia y validaciones](<docs/03 Implementación/Sprint 04/ECL-98 resolucion incidencias.md>)
- [ECL-14 — Mapa operativo, lista accesible y límites de tráfico](<docs/03 Implementación/Sprint 04/ECL-14 mapa rutas.md>)
- [ECL-87 — Code smells del frontend y validación de accesibilidad](<docs/03 Implementación/Sprint 04/ECL-87 code smells frontend.md>)

#### Estado de cierre del Sprint 4

| Indicador | Estado |
|---|---|
| Velocidad y SP finalizados | Pendientes de verificar en Jira |
| Revisión y demostración | Pendientes de registrar |
| Retrospectiva | Pendiente |
| Calidad y seguridad | Pendiente de consolidación |
| Rama de cierre | Pendiente |

#### Green IT


[Índice de entregables del Sprint 4](<docs/03 Implementación/Sprint 04/README.md>)

- [ECL-118 — Informe 02: estándares de ingeniería de software y guía de desarrollo verde (borrador)](<docs/03 Implementación/reduccion del impacto ambiental/02 Estandares Ingeniería de software V_1_0_0.md>)
- [ECL-108 — Línea base ANTES: resultados y medianas](<docs/03 Implementación/reduccion del impacto ambiental/evidencias/antes/run-2026-11-06T23-50-12-524Z/README.md>) · [Protocolo y preparación inicial](<docs/03 Implementación/reduccion del impacto ambiental/evidencias/antes/README.md>)
- [ECL-111 — React.lazy, listados de 12 y verificación offline](<docs/03 Implementación/reduccion del impacto ambiental/ECL-111 React lazy y paginacion V_1_0_0.md>)
- [ECL-113 - Build de produccion con Gzip y cache](<docs/03 Implementación/Sprint 04/ECL-113 build produccion.md>)
- [ECL-114 — Lighthouse CI y corrección de pruebas diferidas](<docs/03 Implementación/reduccion del impacto ambiental/ECL-114 auditoria Green IT en CI.md>)

## Fase 04: Contribución

- [01. Política de pull requests V_1_0_0](<docs/04 Contribución/01. Politica de pull requests V_1_0_0.md>)
- [Plantilla de pull request](.github/pull_request_template.md)
- [AGENTS.md — reglas para agentes de IA](AGENTS.md)

## Código y operación

- [Backend: instalación, pruebas y API](backend/README.md)
- [Backend: pruebas de carga ST-035](backend/loadtest/README.md)
- [Frontend: instalación, pruebas y verificaciones](frontend/README.md)

## Evidencias

Las evidencias ejecutables permanecen junto al código que las genera.

Backend:

- [ECL-50](backend/evidencias/ECL-50/README.md)
- [ECL-54](backend/evidencias/ECL-54/README.md)
- [ECL-60](backend/evidencias/ECL-60/README.md)
- [ECL-61](backend/evidencias/ECL-61/README.md)
- [ECL-61 — incidencias y límites](backend/evidencias/ECL-61/INCIDENCIAS.md)
- [ECL-63](backend/evidencias/ECL-63/README.md)
- [ECL-64](backend/evidencias/ECL-64/README.md)
- [ECL-93 — spike del optimizador VRPTW](backend/evidencias/ECL-93/README.md)
- [ECL-25 — Inicio con indicadores agregados](backend/evidencias/ECL-25-inicio/README.md)

Frontend:

- [ECL-49](frontend/evidencias/ECL-49/README.md)
- [ECL-53](frontend/evidencias/ECL-53/README.md)
- [ECL-54](frontend/evidencias/ECL-54/README.md)
- [ECL-54 — reprueba de D-01 (13/10/2026)](frontend/evidencias/ECL-54/retest-D01-20261013/README.md)
- [ECL-56](frontend/evidencias/ECL-56/README.md)
- [ECL-57](frontend/evidencias/ECL-57/README.md)
- [ECL-58](frontend/evidencias/ECL-58/README.md)
- [ECL-58 — reprueba offline con el rediseño (13/10/2026)](frontend/evidencias/ECL-58/retest-20261013/README.md)
- [ECL-22 — rediseño UI/UX, capturas antes/después y accesibilidad](frontend/evidencias/ECL-22-rediseno/README.md)
