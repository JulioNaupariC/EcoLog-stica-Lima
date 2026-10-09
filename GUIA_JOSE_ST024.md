# EcoLogística Lima — ST-024 — Guía para José

Ticket Jira: [ECL-50](https://continental-team-il84x39k.atlassian.net/browse/ECL-50).
Entrega: pruebas de conductores, validación real PostgreSQL, reportes y
conservación de evidencia en CI. La rama ya está creada y los archivos ya
están en el repositorio; no hace falta copiar ningún paquete.

## 1. Revisar los cambios

Desde la raíz:

```powershell
git status
git branch --show-current
git diff --check
git diff
```

La rama debe ser `feat/ECL-50-st024-pruebas-conductores`.
El reporte está en [backend/VALIDACION_ST024.md](backend/VALIDACION_ST024.md).
Los XML conservados corresponden a pruebas locales ejecutadas.

## 2. Repetir backend

Se dejó `.venv` con Python 3.12 y las dependencias fijadas. En otro equipo,
crear ese entorno con Python 3.12 e instalar `backend/requirements-dev.lock`.
Desde la raíz, ejecutar cada comando y corregir cualquier fallo antes de seguir:

```powershell
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m ruff check backend
.venv/Scripts/python.exe -m ruff format --check backend
Set-Location backend
../.venv/Scripts/python.exe -m pytest tests/unit -q --cov=app --cov-report=term-missing --cov-report=xml:test-results/coverage.xml --junitxml=test-results/unit.xml --cov-fail-under=80
../.venv/Scripts/python.exe -m pytest tests/unit/test_conductor_schemas.py tests/unit/test_conductor_service.py tests/unit/test_conductor_api.py tests/unit/test_conductor_st024_unit.py -q --cov=app.api.conductores --cov=app.schemas.conductor --cov=app.services.conductores --cov=app.repositories.conductores --cov-report=term-missing --cov-report=xml:test-results/conductores-coverage.xml --cov-report=html:test-results/conductores-coverage --junitxml=test-results/conductores-unit.xml --cov-fail-under=80
Set-Location ..
```

Para integración, configurar en la sesión `TEST_DATABASE_URL` hacia una base
**desechable y vacía** PostgreSQL/PostGIS, cuyo nombre termine en `_test`, y
`DATABASE_URL` hacia otra base PostGIS para el smoke. No utilizar datos de
desarrollo: estas pruebas aplican y revierten migraciones. El servidor temporal
usado para esta entrega se detuvo al terminar. GitHub Actions crea sus propias
bases; no necesita tus credenciales locales.

Después de configurar las variables privadas, desde la raíz:

```powershell
Set-Location backend
../.venv/Scripts/python.exe -m pytest tests/integration -q --basetemp=test-results/integration-tmp --junitxml=test-results/integration.xml
Set-Location ..
```

El `--basetemp` anterior es exclusivo para archivos temporales de pytest y puede
ser limpiado por pytest al repetir el comando. No guardar otros archivos allí.

## 3. Repetir frontend

Con Node compatible con `frontend/package.json`, ejecutar desde la raíz:

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run test:coverage -- --reporter=default --reporter=junit --outputFile.junit=test-results/frontend.xml
npm.cmd run build
Set-Location ..
```

## 4. Subir a GitHub

Desde la raíz y en la rama de ST-024, revisar y agregar únicamente los archivos
de esta entrega. No incluir `.env`, `.venv`, temporales ni datos de PostgreSQL:

```powershell
git status
git add .gitignore .github/workflows/ci.yml backend/README.md backend/tests/unit/test_conductor_st024_unit.py backend/tests/integration/test_conductor_st024.py backend/VALIDACION_ST024.md backend/evidencias/ECL-50 GUIA_JOSE_ST024.md
git diff --cached --stat
git diff --cached --check
git commit -m "test(ECL-50): cubrir gestion de conductores y registrar evidencia CI"
git push -u origin feat/ECL-50-st024-pruebas-conductores
```

## 5. Obtener evidencia CI y abrir PR

1. Después del push, abrir [GitHub Actions](https://github.com/JulioNaupariC/EcoLog-stica-Lima/actions).
2. Abrir la ejecución **CI** de la rama de ST-024 y comprobar el commit.
3. Verificar los jobs Backend / Quality and unit, Backend / Integration y Frontend.
4. Descargar los tres artefactos indicados en el reporte. Conservarlos antes de
   que venza la retención de 30 días; revisar los XML, incluidas las negativas.
5. Abrir el [PR de esta rama hacia main](https://github.com/JulioNaupariC/EcoLog-stica-Lima/compare/main...feat/ECL-50-st024-pruebas-conductores?expand=1)
   y solicitar revisión de un compañero. Revisar también los controles SAST
   existentes del repositorio antes de integrar.
6. Adjuntar al ticket el PR, el enlace de la ejecución verde y los artefactos.
   No marcar como ejecutada la CI remota hasta observar su resultado real.

Título sugerido: `test(ECL-50): pruebas de gestión de conductores y evidencia CI`.

Descripción sugerida del PR:

> Amplía la cobertura de gestión de conductores con límites de disponibilidad,
> sesión obligatoria/revocada, errores sanitizados y persistencia/rollback real
> PostgreSQL. CI exige cobertura de conductores >=80 % y conserva resultados
> JUnit y cobertura durante 30 días, incluso ante fallos.
>
> Validación local: 520 unitarias backend, 116 de integración y 369 frontend
> aprobadas. Cobertura de conductores 98.13 %. Ruff, typecheck, lint y build
> aprobados. Reporte: backend/VALIDACION_ST024.md. Añadir aquí el enlace de
> GitHub Actions una vez finalice la ejecución remota.
