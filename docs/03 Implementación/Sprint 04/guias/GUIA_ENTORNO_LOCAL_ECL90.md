# ECL-90 / A11 — Entorno local y seguimiento para la retrospectiva

Responsable: José Delgadillo, con apoyo de Julio. Revisor previsto: @JulioNaupariC.
Base de trabajo: `main` en `7733be8ed0fbe23bdfabfd3e9bd7cf017c6ea9be`.
Fecha de comprobación: **06/11/2026, America/Lima**. No se declara cumplido el 5/5.

## Resultado actual y tabla para Frank

Esta tabla está preparada para incorporarse a la retrospectiva del Sprint 4.
Es un seguimiento de A11, no el acta de una reunión ni una confirmación de otros
integrantes. No se contactó a los compañeros ni se accedió a sus computadoras.
**Sin verificar** significa ausencia de evidencia actual; no significa fallo.

| Integrante | App levantada e inicio de sesión | Integración local corrida | Fecha de validación Sprint 4 | Motivo / evidencia |
|---|---|---|---|---|
| José Samuel Delgadillo Pantoja | Sí | Sí: 250 aprobadas, 0 fallos/errores/omitidas | 06/11/2026 | Demo Compose real, login Operador y pruebas contra una base PostGIS nueva y desechable; artefactos enlazados abajo |
| Julio Armando Naupari Camarena | Sin verificar en Sprint 4 | Sin verificar en Sprint 4 | Sin validación actual | Hay evidencia histórica de arranque/login del 29/10; falta repetir y registrar el recorrido actual |
| Giancarlo Marcio Soto Escobar | Sin verificar en Sprint 4 | Sin verificar en Sprint 4 | Sin validación actual | Hay demostración en su laptop del 30/10 y una declaración previa de integración; falta confirmar el estado actual |
| Antony Munive Ríos | Sin verificar en Sprint 4 | Sin verificar en Sprint 4 | Sin validación actual | Hay declaraciones históricas de pruebas locales en sus PR; no acreditan arranque y login actuales en su PC |
| Frank Roy Yupanqui Acevedo | Sin verificar | Sin verificar | Sin validación actual | PR #91 informa que no dispone de Python local; PR #62 había registrado alias Microsoft Store y Docker detenido. Falta comprobar Docker o la alternativa de demo en su equipo |

**Métrica acreditada en Sprint 4: 1/5 con app y login; 1/5 con integración local.**
El [ticket Jira ECL-90](https://continental-team-il84x39k.atlassian.net/browse/ECL-90)
pide app/login de 5/5 y al menos 3 integrantes con integración local; el encargo
recibido propone que los cinco ejecuten ambas cosas. Se conserva esa cobertura
objetivo de 5/5, sin rebajarla ni inferir resultados a partir del CI.
En la consulta del ticket no había comentarios de confirmación (0).

Frank puede usar la tabla anterior tal cual, conservando los estados pendientes.
Para completar cada fila se necesita: integrante, fecha Lima, commit, método
de arranque, login real, comando de integración y resultado con aprobadas,
fallos y omitidas; o el error concreto y la alternativa utilizada. Cada integrante
debe registrar su confirmación en ECL-90, como pide el ticket. No atribuir al
grupo las pruebas ejecutadas por José ni las de un runner GitHub.

## Qué se buscó y qué acredita cada fuente

Se revisaron README, documentos de Review/retrospectiva, evidencias y PR del
repositorio, ECL-90 y una búsqueda Jira de entorno/Docker. La búsqueda semántica
Rovo devolvió 403; la búsqueda directa de Confluence también devolvió 403
(`Current user not permitted to use Confluence`). La lectura del ticket y la
búsqueda JQL sí funcionaron. No se infiere contenido de fuentes inaccesibles.

| Fuente | Hallazgo | Límite |
|---|---|---|
| [PR #74, Julio](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/74) | Reporta arranque, login administrador y reinicio en laptop de desarrollo Windows 11 el 29/10/2026, commit `85dd92b` | No acredita integración ni un recorrido Sprint 4; tampoco una PC restringida de laboratorio |
| [Review Sprint 3](<../../Sprint 03/01 Revisión del Sprint V_1_0_0.md>) | Registro de demostración del 30/10/2026 desde la laptop de Giancarlo, con flujos reales | Es evidencia histórica, no una nueva prueba del commit actual |
| [PR #35, Giancarlo](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/35) | Declara 110 pruebas de integración locales y PostgreSQL/PostGIS | PR creado el 09/10/2026; no confirma entorno y ejecución actuales |
| [PR #57, Antony](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/57) | Declara pipeline local con 154 pruebas de integración | Antecedente; no equivale a comprobar su PC en Sprint 4 |
| [PR #62, Frank](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/62) y [PR #91](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/91) | El primero describe Python apuntando a Microsoft Store y Docker detenido; el segundo informa falta de Python local | No demuestra que Docker no pueda usarse hoy; se registra el bloqueo reportado, sin inventar un intento |
| [PR #73, José](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/73) | Campaña local del 27/10 con 250 pruebas de integración | Se encontró como antecedente y se volvió a ejecutar la suite actual para ECL-90 |

## Recorrido Inicio / README con cada integrante

Usar el [arranque del README](../../../../README.md#arranque-local-con-docker-compose--ecl-29)
como entrada: la Ruta del Sprint 4 no se encontró en los archivos consultados y
Confluence no fue accesible. No se simula haber recorrido esa ruta con otros.

1. Actualizar el clon según las reglas del proyecto, registrar el commit y
   comprobar Docker Desktop, motor Linux y Compose.
2. Ejecutar `scripts/verificar_entorno.ps1`. Corregir los errores usando los
   [problemas frecuentes](../../../../README.md#problemas-frecuentes-del-entorno-local--ecl-90).
   Si la aplicación ya está activa, sus puertos ocupados no significan fallo de
   esa instancia. Identificarla antes de arrancar otra.
3. Preparar `.env` privadamente y validar con `config --quiet`. Revisar proyectos
   y volúmenes de otros clones. No publicar el archivo ni configuración expandida.
4. Seguir el arranque existente: build, base, comprobación PostGIS, migración,
   revisión `current`/`heads`, API y frontend. Usar `127.0.0.1` para ambos servicios.
5. Preparar cuentas y datos ficticios con el
   [seed existente](../../../../backend/README.md#datos-de-demostración--sprint-2)
   en una base autorizada `_demo`; sus contraseñas se suministran en privado.
   No recrear una base con datos ajenos ni usar cuentas personales reales.
6. Iniciar sesión y mostrar la app real. El estado saludable de un contenedor
   por sí solo no acredita este paso. Ejecutar después la integración contra
   una base distinta `_test`, según la ruta siguiente.
7. Guardar solo evidencia revisada, completar la fila y registrar el resultado
   en ECL-90. Si no puede ejecutarse, anotar error, fecha y alternativa.

La alternativa sin Docker es la
[guía de demo ECL-68](<../../Sprint 03/guias/GUIA_DEMO_LABORATORIO.md>).
Requiere preparar previamente las herramientas portables descritas allí.
Su validación en una PC de laboratorio sin administrador sigue siendo una
limitación conocida; este documento no la declara resuelta.

## Integración aislada con Docker: procedimiento reproducible

La imagen API no incluye pytest ni copia `tests/`. Para ejecutar la suite sin
Python local se utilizó una imagen temporal con `requirements-dev.lock` y un
montaje de pruebas de solo lectura, en el proyecto separado
`ecologistica-lima-ecl90`. La demo existente siguió activa en `ecologistica-lima-ecl108`.
No se cambió el Dockerfile ni Compose de la aplicación.

Desde la raíz, crear una carpeta temporal ignorada y el Dockerfile de pruebas:

```powershell
New-Item -ItemType Directory -Force .tmp-ecl90/resultados | Out-Null
@'
FROM python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-dev.lock ./
RUN python -m pip install --no-cache-dir -r requirements-dev.lock && python -m pip check
COPY . .
RUN groupadd --system app && useradd --system --gid app --home-dir /app --no-create-home app
USER app
'@ | Set-Content .tmp-ecl90/Dockerfile.integration -Encoding ASCII
@'
services:
  integracion:
    build:
      context: ./backend
      dockerfile: ../.tmp-ecl90/Dockerfile.integration
    environment:
      DATABASE_URL: ${DATABASE_URL:?Required}
      TEST_DATABASE_URL: ${TEST_DATABASE_URL:?Required}
    volumes:
      - ./backend/tests:/app/tests:ro
      - ./.tmp-ecl90/resultados:/results
    command: [python, -m, pytest, tests/integration, -q, --junitxml=/results/integration.xml, -p, no:cacheprovider]
'@ | Set-Content .tmp-ecl90/compose.integracion.yaml -Encoding ASCII
if (-not (Test-Path -LiteralPath .env.ecl90-tests)) {
    Copy-Item -LiteralPath .env -Destination .env.ecl90-tests
}
```

En un editor local, completar `TEST_DATABASE_URL` en `.env.ecl90-tests` con
`postgresql+psycopg`, host `db:5432`, las credenciales privadas de esa
configuración y base `ecologistica_ecl90_test`. Conservar `DATABASE_URL` dirigida
a una base distinta. Ese archivo y `.tmp-ecl90/` están ignorados; no mostrarlos
ni añadirlos al repositorio. `POSTGRES_*` deben corresponder a `DATABASE_URL`.

Antes de usar el nombre de proyecto, comprobar `docker compose ls --all` y
`docker volume ls --filter name=ecologistica-lima-ecl90_postgis_data`. En una
primera ejecución deben ser recursos nuevos; si ya existen, verificar propiedad
y estado antes de reutilizarlos. No borrar ni vaciar automáticamente una base.
La suite exige un esquema public vacío y una base `_test` diferente de desarrollo.

Ejecutar cada paso y detenerse si falla; no imprimir `config` sin `--quiet`:

```powershell
$opcionesEcl90 = @('-p', 'ecologistica-lima-ecl90', '--env-file', '.env.ecl90-tests', '-f', 'compose.yaml', '-f', '.tmp-ecl90/compose.integracion.yaml')
docker compose @opcionesEcl90 config --quiet
docker compose @opcionesEcl90 build integracion
docker compose @opcionesEcl90 up -d --wait db
# Solo en la primera preparacion: elegir el usuario privado de POSTGRES_USER.
$usuarioPruebasEcl90 = Read-Host 'POSTGRES_USER de la configuracion local'
docker compose @opcionesEcl90 exec -T db createdb --username=$usuarioPruebasEcl90 --owner=$usuarioPruebasEcl90 --template=template_postgis ecologistica_ecl90_test
docker compose @opcionesEcl90 run --rm --no-deps integracion
```

`createdb` debe fallar si la base ya existe, en lugar de reemplazarla. Para una
repetición, inspeccionar primero que la base exclusiva de pruebas conserve el
estado vacío admitido por los fixtures. No aplicar `alembic upgrade head` a esta
base antes de la suite: las pruebas de migración necesitan un esquema no versionado.
No correr dos suites simultáneamente contra ella.
La instalación directa equivalente se documenta en
[backend: pruebas de migración y persistencia](../../../../backend/README.md#pruebas-de-migración-y-persistencia).

Al terminar, se puede apagar exclusivamente el proyecto de pruebas conservando
sus datos con `docker compose @opcionesEcl90 down`. No usar `down -v` ni limpiar
volúmenes globales. Este procedimiento no publica PostgreSQL al host y no necesita
liberar los puertos de la demo para ejecutar integración.

## Evidencia local de José y problemas observados

| Comprobación | Resultado | Evidencia |
|---|---|---|
| App real y login Operador | Readiness 200, Vite 200, login y encabezado Inicio; Chrome 156.0.8078.80 | [Registro](../evidencias/ECL-90/run-2026-11-07T00-25-45-115Z/app.json) · [Captura](../evidencias/ECL-90/run-2026-11-07T00-25-45-115Z/login-operador.png) |
| Integración PostGIS | 250 aprobadas, 0 fallos, 0 errores y 0 omitidas; 118,71 s según salida de pytest | [JUnit original](../evidencias/ECL-90/run-2026-11-07T00-25-45-115Z/integration.xml) |
| Verificador | Docker, motor Linux, Compose y `.env`: OK; puertos 8000/5173 ocupados por la demo; salida 1 esperada | [Diagnóstico y pruebas](../evidencias/ECL-90/run-2026-11-07T00-25-45-115Z/verificacion.txt) |
| Pruebas del verificador | Faltantes, motor detenido/Windows, Compose v1, privacidad y puertos; también puerto efímero real ocupado/liberado; salida 0 | [Script de pruebas](../../../../scripts/tests/test-verificar-entorno.ps1) |
| Contexto y trazabilidad | Windows 11, CPU/RAM, Python 3.12.10 en Docker, commit base, separación de proyectos/bases y hashes de artefactos | [Entorno](../evidencias/ECL-90/run-2026-11-07T00-25-45-115Z/entorno.json) |

Los JSON y JUnit conservan UTC: el prefijo `2026-11-07T00...Z` corresponde al
**06/11/2026 por la tarde en Lima**. No se cambia la fecha interna de la evidencia.
La integración terminó con dos avisos de deprecación de Starlette/httpx/AnyIO,
sin fallos; no se modifican dependencias dentro de este ticket.

En esta PC se observó una política de PowerShell que impedía ejecutar scripts;
la invocación `RemoteSigned` por proceso permitió ejecutar los archivos locales
revisados, sin cambiar la política persistente. Los dos puertos ocupados y un
proyecto Compose de otro clon ya estaban presentes: se identificaron y se aisló
la integración en otro proyecto, conservando la demo. La falta inicial de motor
y `.env` en esta misma PC se resolvió durante ECL-108, antes de esta comprobación.
Los demás casos de la FAQ son diagnósticos preventivos o antecedentes citados;
no se inventan fallos de WSL o memoria del equipo.

Para repetir las pruebas del verificador:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File scripts/tests/test-verificar-entorno.ps1
python scripts/check_docs.py
```

La aceptación de A11 sigue pendiente de las otras cuatro PC, sus registros y
la revisión humana. El PR debe permanecer en borrador hasta la auditoría técnica
independiente y la revisión de @JulioNaupariC. La tabla queda disponible para Frank
mediante el PR y este documento; no se afirma que él ya la haya recibido o validado.

[← Índice del Sprint 4](../README.md)

[← Volver al README principal](../../../../README.md)
