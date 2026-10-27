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

## Fase 03: Implementación — entregables del Sprint 2

- [01 Informe de estado del proyecto](<docs/03 Implementación/01 Informe de estado del proyecto V_1_0_0.md>)
- [02 Registro de Impedimentos](<docs/03 Implementación/02 Registro de Impedimentos V_1_0_0.md>)
- [03 Revisión del Sprint](<docs/03 Implementación/03 Revisión del Sprint V_1_0_0.md>)
- [04 Retrospectiva del Sprint](<docs/03 Implementación/04 Retrospectiva del Sprint V_1_0_0.md>)

### Documentación técnica del Sprint 2

- [Índice del Sprint 2 y mapa de reubicación](<docs/03 Implementación/Sprint 02/README.md>)

Validaciones:

- [ST-022 / ECL-48 — API de conductores](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST022.md>)
- [ST-023 / ECL-49 — formulario y listado de conductores](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST023.md>)
- [ST-024 / ECL-50 — pruebas de conductores](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST024.md>)
- [ST-026 / ECL-52 — API de preferencias de entrega](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST026.md>)
- [ST-027 / ECL-53 — interfaz de preferencias](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST027.md>)
- [ST-028 / ECL-54 — matriz de preferencias y clientes](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST028.md>)
- [ST-030 / ECL-56 — interfaz móvil del conductor](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST030.md>)
- [ST-031 / ECL-57 — responsive y accesibilidad](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST031.md>)
- [ST-032 / ECL-58 — offline y sincronización](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST032.md>)
- [ST-034 / ECL-60 — métricas de API y base de datos](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST034.md>)
- [ST-035 / ECL-61 — carga y disponibilidad](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST035.md>)
- [ST-038 / ECL-64 — optimización de consultas](<docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST038.md>)

Informes:

- [ST-033 / ECL-59 — Plan de pruebas de capacidad y disponibilidad](<docs/03 Implementación/Sprint 02/informes/plan-pruebas-capacidad.md>)
- [ST-036 / ECL-62 — Resultados, SLA y operación](<docs/03 Implementación/Sprint 02/informes/INFORME_ST036.md>)
- [ST-037 / ECL-63 — Medición inicial de payload y consultas críticas](<docs/03 Implementación/Sprint 02/informes/INFORME_ST037.md>)

Diseño:

- [ST-029 / ECL-55 — Diseño móvil del conductor (Giancarlo)](<docs/03 Implementación/Sprint 02/diseno/ST-029/README.md>)
- [ST-029 — Guía visual](<docs/03 Implementación/Sprint 02/diseno/ST-029/guia-visual.md>)
- [ST-029 — Evidencias visuales](<docs/03 Implementación/Sprint 02/diseno/ST-029/evidencias/README.md>)

Guías de integración:

- [Guía ST-024](<docs/03 Implementación/Sprint 02/guias/GUIA_JOSE_ST024.md>)
- [Guía ST-027](<docs/03 Implementación/Sprint 02/guias/GUIA_JOSE_ST027.md>)
- [Guía ST-031 y ST-032](<docs/03 Implementación/Sprint 02/guias/GUIA_JOSE_ST031_ST032.md>)
- [Guía ST-035](<docs/03 Implementación/Sprint 02/guias/GUIA_JOSE_ST035.md>)

### Documentación técnica del Sprint 3

- [Índice del Sprint 3](<docs/03 Implementación/Sprint 03/README.md>)
- [Ítem 7 — Coherencia y versionamiento documental](<docs/03 Implementación/Sprint 03/07 Coherencia y versionamiento documental V_1_0_0.md>)
- [US-013 / ECL-77 — Restablecer contraseña de un usuario](<docs/03 Implementación/Sprint 03/validaciones/VALIDACION_US013.md>)
- [US-013 / ECL-77 — Evidencias visuales](<docs/03 Implementación/Sprint 03/validaciones/evidencias/ECL-77/README.md>)
- [ECL-74 / ST-041 — Formulario móvil de incidencias y validación](<docs/03 Implementación/Sprint 03/validaciones/VALIDACION_ST041.md>)
- [ECL-74 — Evidencias de Chrome y Firefox](<docs/03 Implementación/Sprint 03/validaciones/evidencias/ECL-74/README.md>)
- [ECL-74 — Cuerpo preparado del pull request](<docs/03 Implementación/Sprint 03/validaciones/ECL-74-PR.md>)
- [ECL-75 / ST-042 — Vista de incidencias pendientes para Operación](<docs/03 Implementación/Sprint 03/validaciones/VALIDACION_ST042.md>) · [Evidencias](<docs/03 Implementación/Sprint 03/validaciones/evidencias/ECL-75/README.md>)
- [ECL-67 / EN-011 — Evaluación WCAG del Sprint 3](<docs/03 Implementación/Sprint 03/05 WCAG V_1_0_0.md>) · [Evidencias finales](<docs/03 Implementación/Sprint 03/evidencias/ECL-67/comprobacion-final-20261027/README.md>) · [Registro inicial](<docs/03 Implementación/Sprint 03/evidencias/ECL-67/README.md>)
- ECL-76 / ST-043 — [Matriz US-012](<docs/03 Implementación/Sprint 03/validaciones/VALIDACION_US012.md>) · [Evidencias](<docs/03 Implementación/Sprint 03/validaciones/evidencias/ECL-76/README.md>) · [Cuerpo del PR](<docs/03 Implementación/Sprint 03/validaciones/ECL-76-PR.md>)

### Estado del Sprint 2 — cierre

Periodo planificado: 08/10/2026–23/10/2026. El informe de estado, el registro de
impedimentos y la revisión están en la versión de contenido 1.3.1, y la
retrospectiva en la 1.3.0; el historial del Sprint 1 permanece en Git y en la
rama `sprint-1`.

En Jira, los cinco padres y las 19 subtareas figuran Finalizada (27/27 SP).
Contrastados con sus criterios de aceptación: ECL-11 y ECL-25 cumplen; ECL-9,
ECL-22 y ECL-23 cumplen parcialmente. La Review del 09/10/2026 se
evaluó con 14/20 sin demostración; el parche posterior (PR #47–#57) y la
demostración complementaria están en la [Revisión del Sprint](<docs/03 Implementación/03 Revisión del Sprint V_1_0_0.md>).
La retrospectiva se realizó en clase el 23/10/2026 con el equipo completo y la
guía visual de ST-029 (ECL-55) se integró en el cierre. El sprint se cierra en
Jira tras integrar el PR de cierre.

### Ramas de cierre por sprint

Cada sprint conserva una rama con el estado final de su código y documentación,
como evidencia de lo entregado. Las ramas de trabajo se eliminan al cerrar cada
sprint; las del Sprint 3 se conservan hasta su evaluación (30/10/2026).

| Rama | Contenido | Commit de corte |
|---|---|---|
| `sprint-1` | Sprint 1 — Base Operativa (PR #1–#22) | `58c3d9c` (02/10/2026) |
| `sprint-2` | Sprint 2 — Gestión operativa y experiencia del conductor, con el parche posterior a la Review (PR #23–#57) y el cierre | Merge del PR de cierre del Sprint 2 |
| `main` | Rama de integración; punto de partida del Sprint 3 | — |

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
