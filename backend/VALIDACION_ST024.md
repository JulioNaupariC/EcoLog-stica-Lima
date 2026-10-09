# Validación de ST-024 — ECL-50

Fecha: 09/10/2026, America/Lima.
Ticket: [ECL-50 · Implementar pruebas de gestión de conductores](https://continental-team-il84x39k.atlassian.net/browse/ECL-50).
Rama: `feat/ECL-50-st024-pruebas-conductores`.
Trazabilidad: US-003 / RF-003, RN-002, RNF-004 y RNF-010.

## Alcance

Se amplían las pruebas existentes de ST-020, ST-022 y ST-023 con 14 casos
unitarios y 6 casos de integración. Se ejecuta la regresión backend/frontend y
se configura el registro automático de resultados en CI. No cambia el contrato
HTTP ni las reglas de negocio.

Se conserva el contrato documentado en [ST-022](VALIDACION_ST022.md): una
licencia vencida puede persistirse como perfil, pero no habilita asignación.
La disponibilidad puede superar ocho horas; RN-005 restringe la conducción y
los descansos de una ruta. `habilitado_asignacion` representa elegibilidad
básica y no certifica factibilidad del optimizador.

## Matriz de pruebas

Los archivos unitarios se encuentran en `tests/unit/` y los de integración en
`tests/integration/`. Los casos de frontend están en `frontend/src/`.
Las nuevas pruebas son `tests/unit/test_conductor_st024_unit.py` y
`tests/integration/test_conductor_st024.py`.

| Grupo | Casos comprobados | Pruebas |
|---|---|---|
| Alta válida | Normalización, DNI con cero inicial, cuenta CONDUCTOR independiente, hash real, franja completa | `test_conductor_schemas.py`, `test_conductor_service.py`, `test_conductor_http_e2e.py` |
| Datos inválidos | DNI/formato, campos vacíos, experiencia negativa/booleana/fraccionaria, teléfono, fechas sin zona, campos extra, PATCH vacío | `test_conductor_schemas.py`, `test_conductor_api.py`, `test_conductor_st024.py` |
| Conflictos | DNI y email duplicados; reversión de cuenta creada; PATCH con DNI duplicado revierte también nombre | `test_conductor_http_e2e.py`, integración `test_conductor_st024.py` |
| Permisos positivos | Administrador y Operador crean, consultan y actualizan; Conductor consulta su resumen | `test_conductor_api.py`, `test_conductor_http_e2e.py` |
| Permisos negativos | Conductor/Auditor/Analista no escriben; Conductor no consulta terceros; rechazo sin sesión y al reutilizar cookie revocada | `test_conductor_api.py`, `test_conductor_http_e2e.py`, `test_conductor_st024_unit.py`, `test_conductor_st024.py` |
| Conservación y auditoría | Escrituras 403 conservan cuentas/perfiles y generan eventos AUTORIZACION_DENEGADA reales | integración `test_conductor_st024.py` |
| Privacidad | Listado/resumen sin DNI/contacto; errores sin contraseña ni input original; errores de almacenamiento sanitizados | `test_conductor_api.py`, `test_conductor_http_e2e.py`, `test_conductor_st024_unit.py` |
| Disponibilidad | Cambio y retiro persistidos; licencia vencida no habilita; cuenta/perfil inactivos no habilitan; final exclusivo con reloj fijo; fecha final de licencia en Lima | `test_conductor_service.py`, `test_conductor_st024_unit.py`, `test_conductor_st024.py` |
| Persistencia | Nueva sesión SQL, nueva instancia FastAPI y nueva autenticación conservan perfil y franja; se comparan instantes con zona, no cadenas de fecha | integración `test_conductor_st024.py` |
| Integridad BD | Unicidad, FK, restricciones CHECK, migración reversible, franja completa y ordenada | `test_conductor_st020.py` |
| Errores HTTP | 401, 403, 404, 409, 422, 503; UUID y paginación inválidos; 503 sanitizado para cada operación | `test_conductor_api.py`, `test_conductor_st024_unit.py` |
| Interfaz | Validación, alta, edición, retiro de disponibilidad, errores, doble envío, permisos, limpieza de contraseña y respuestas tardías | `domain/driverForm.test.ts`, `services/drivers.test.ts`, `pages/DriversPage.test.tsx`, `app/App.drivers.test.tsx` |

## Resultados locales

Entorno final: Windows, Python 3.12.6, dependencias exactas de
`requirements-dev.lock`, Node 22.18.0, npm 10.9.3 y `npm ci`.
PostgreSQL 16.15 / PostGIS 3.6 en servidor temporal exclusivo, escuchando solo
en `127.0.0.1:55450`. Base de pruebas vacía `st024_test`, separada de la base de
comprobación PostGIS del mismo servidor. No se reutilizó la base del proyecto.
CI utiliza Python 3.12.10 y PostGIS 16-3.5, por lo que su ejecución remota sigue
siendo una verificación independiente.

| Verificación | Resultado |
|---|---|
| Unitarias backend completas | 520 aprobadas |
| Cobertura unitaria backend | 93.22 % |
| Unitarias de conductores | 99 aprobadas |
| Cobertura API/esquemas/repositorio/servicio de conductores | 98.13 %; mínimo 80 % |
| Integración backend completa | 116 aprobadas, sin omisiones |
| Integración de conductores, incluida en las 116 | 10 aprobadas |
| Frontend completo | 369 aprobadas en 21 archivos |
| Frontend: statements / branches / functions / lines | 92.59 % / 92.51 % / 93.45 % / 94.84 % |
| Ruff check y format --check | Aprobados |
| pip check | Aprobado |
| Frontend typecheck, lint y build | Aprobados |

Los casos negativos aprobados significan que se obtuvo el rechazo esperado y
se comprobaron sus efectos; no representan fallos de la suite.

Los reportes XML de la ejecución final están en
[evidencias/ECL-50](evidencias/ECL-50/README.md). Se eliminaron únicamente el
hostname y las rutas absolutas del equipo al preparar las copias para Git.

Durante la verificación inicial se corrigieron dos comparaciones de la prueba
nueva que asumían UTC al leer desde una BD configurada en UTC-5. También se
habilitó PostGIS en la base de smoke y se ubicaron los temporales de pytest
dentro del repositorio para evitar restricciones de acceso de Windows. La
ejecución final utiliza Python 3.12 y no mantiene fallos u omisiones.
Persisten dos avisos de deprecación de Starlette/httpx/AnyIO ya presentes en
las dependencias fijadas; no impiden la ejecución.

## Registro en CI y aceptación

`.github/workflows/ci.yml` ejecuta pruebas en PR hacia `main`, al subir esta
rama y mediante `workflow_dispatch` cuando el workflow esté disponible en la
rama predeterminada. Mantiene los controles globales y añade un gate de
cobertura específico de conductores (80 %).

Cada job sube evidencia con `if: always()`, conservada durante 30 días:

- `backend-unit-results-<run_id>`: JUnit global y de conductores, cobertura XML
  global y de conductores, cobertura HTML de conductores.
- `backend-integration-results-<run_id>`: JUnit de integración real PostgreSQL.
- `frontend-test-results-<run_id>`: JUnit y cobertura HTML frontend.

El pipeline sigue fallando si falla una prueba o un gate. No se utiliza
`continue-on-error`. Si un paso previo impide iniciar las pruebas, los logs
registran el problema y la subida advierte que no hay archivos disponibles.

**Estado:** implementación y validación local completadas. Ejecución remota de
GitHub Actions y peer review pendientes del push y PR del usuario. Para cerrar
el ticket, adjuntar el enlace a una ejecución verde de esta rama/commit y sus
artefactos, además de este reporte. Las evidencias locales no se presentan como
una ejecución de GitHub Actions ni como una certificación SAST.
