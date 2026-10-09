# EcoLogística Lima — ST-035 / ECL-61 — Guía para José

Ticket: https://continental-team-il84x39k.atlassian.net/browse/ECL-61

Entrega: generador Locust reproducible, preparación aislada de datos, ejecución
HTTP real, conciliación SQL, medición P95/5xx/concurrencia/disponibilidad,
capturas, resultados y reporte de incidencias. Ver
[VALIDACION_ST035.md](backend/VALIDACION_ST035.md) para el resultado medido.

## 1. Revisar la rama

Desde la raíz del repositorio:

```powershell
git status
git branch --show-current
```

La rama de esta tarea es `feat/ECL-61-st035-carga-disponibilidad`, creada desde
`origin/main`. No cambiar a main ni descartar cambios para subir esta entrega.

## 2. Verificar calidad

Con Python 3.12 y el entorno virtual activado, desde `backend`:

```powershell
python -m pip install -r requirements-load.lock
python -m pip check
python -m ruff check .
python -m ruff format --check .
python -m pytest tests/unit -q --cov=app --cov=loadtest.analysis --cov=loadtest.audit --cov=loadtest.report --cov=loadtest.consolidate --cov-fail-under=80
```

El workflow existente agrega un gate específico para el analizador de carga,
incluidos casos negativos y cobertura ≥80%. Los resultados de GitHub Actions
se consultan después de abrir el PR; no atribuirles una ejecución local.

## 3. Revisar y reproducir la campaña

La ejecución y capturas de esta entrega están en
`backend/evidencias/ECL-61/campaign-20261009/`.
Abrir `reporte.html` en Chrome; los JSONL comprimidos son evidencia primaria.
La corrida interrumpida se conserva y su recuperación está en
`backend/evidencias/ECL-61/recovery-20261009/`. No separar esas carpetas.
Resultados: P95 de estrés 1.751/1.220/1.098 s y 0% 5xx; agregado diagnóstico
1.497 s sobre 203,798 pedidos. No se acreditó concurrencia sostenida de 100
solicitudes, ni el SLA mensual. Ver las incidencias antes de presentar la tarea.

Para repetir, instalar PostgreSQL 16 y PostGIS. Desde `backend`:

```powershell
python -m loadtest.campaign --pg-bin "C:/Program Files/PostgreSQL/16/bin" --output "evidencias/ECL-61/mi-nueva-campana"
python -m loadtest.report "evidencias/ECL-61/mi-nueva-campana"
python -m loadtest.audit "evidencias/ECL-61/mi-nueva-campana"
```

La carpeta de salida debe ser nueva. Duración aproximada: 43 minutos.
Usa puertos locales 55455/8055 y crea su propio clúster; no utiliza una base
compartida. Mantiene el código de la API y los pools actuales. Conserva el
clúster detenido dentro de `.tmp-st035-pg/`, ignorado por Git.
No publicar esa carpeta: contiene hashes y sesiones sintéticas.

La jornada de 1,000 pedidos está comprimida a 180 s. Las tres repeticiones de
estrés usan 60 s de subida +120 s de calentamiento +600 s de medición.
`--users 120` permite investigar un ajuste del generador si no se sostienen
100 solicitudes reales; conservar tanto la corrida anterior como la nueva.
No declarar un resultado favorable solo por configurar 100 clientes.

Para regenerar capturas, se requiere Chrome y Playwright 1.64.0 en una carpeta
aislada. Desde `backend`, sin modificar el package.json del frontend:

```powershell
npm install --prefix ../frontend/node_modules/.st035-browser-check --no-package-lock --no-save playwright@1.64.0
node loadtest/capture.mjs evidencias/ECL-61/mi-nueva-campana ../frontend/node_modules/.st035-browser-check/node_modules/playwright/index.mjs
```

Ver [loadtest/README.md](backend/loadtest/README.md) para preparación, timeout,
fórmulas, población y límites. La disponibilidad medida es solo del ambiente y
las ventanas publicadas; no se ha medido ni certificado un SLA mensual.

## 4. Subir al GitHub

Desde la raíz, revisar los archivos antes del commit:

```powershell
git status
git diff --check
git add .gitignore .github/workflows/ci.yml GUIA_JOSE_ST035.md backend/README.md backend/VALIDACION_ST035.md backend/requirements-load.lock backend/loadtest backend/tests/unit/test_loadtest_analysis.py backend/tests/unit/test_loadtest_evidence.py backend/evidencias/ECL-61
git diff --cached --stat
git commit -m "test(ECL-61): ejecutar pruebas de carga y disponibilidad ST-035"
git push -u origin feat/ECL-61-st035-carga-disponibilidad
```

## 5. Pull Request

Base: `main`. Compare: `feat/ECL-61-st035-carga-disponibilidad`.

Título:

```text
test(ECL-61): ejecutar pruebas de carga y disponibilidad ST-035
```

Descripción:

```markdown
Implementa y ejecuta una campaña reproducible con HTTP real y PostgreSQL/PostGIS
aislados: jornada sintética de 1,000 pedidos, 50 vehículos y tres repeticiones
de estrés con 100 clientes. Conserva intentos, conciliación de persistencia,
P95 exacto, errores 5xx, concurrencia del servidor y sondeos API/BD.

Incluye scripts Locust y aprovisionamiento, dependencias fijadas, capturas,
reporte HTML, incidencias y casos negativos del analizador integrados en CI.

La jornada está comprimida a 180 segundos. Los resultados y umbrales medidos
se detallan en backend/VALIDACION_ST035.md y en
backend/evidencias/ECL-61/campaign-20261009/reporte.html.
Los tres P95 medidos fueron 1.751, 1.220 y 1.098 s, con 0% 5xx. El agregado
diagnóstico es 1.497 s sobre 203,798 pedidos válidos persistidos. No se acreditó
concurrencia sostenida de 100 solicitudes: solo 19%, 19.5% y 21% de segundos
con muestras ≥100. Se conservó una corrida interrumpida por un salto del host
y se repitió en otra base, sin reemplazar sus archivos originales.
La consulta de tablero depende de ECL-15; el SLA mensual no ha sido medido.

Validación local: 556 pruebas unitarias aprobadas, cobertura global 93.00%;
36 casos del gate de utilidades con cobertura 90.99%; Ruff y pip check aprobados.
CI remoto y revisión por un compañero pendientes al abrir este PR.

Jira: https://continental-team-il84x39k.atlassian.net/browse/ECL-61
```

Adjuntar `01-resultados-disponibilidad.png` y `02-concurrencia.png` al PR,
solicitar revisión y esperar CI. No mezclar a main sin revisión del equipo.
