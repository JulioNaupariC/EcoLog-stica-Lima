# Evidencias de ECL-76 — US-012

Ejecución local del **27/10/2026**, `America/Lima`, rama
`test/ECL-76-pruebas-incidencias`, sobre `892c36459f0d124631bb2ad73758cc84154c718c`
más los cambios del ticket aún sin commit.

| Comprobación | Resultado real | Evidencia |
|---|---|---|
| Backend unitario completo | 868 aprobadas; cobertura 92,27 %, umbral 80 % satisfecho | [Extracto de consola](local-20261027/backend-summary.txt) |
| Backend unitario de incidencias | 139 aprobadas; 0 fallos | [JUnit](local-20261027/backend-incidencias.xml) |
| Frontend completo con cobertura | 732 aprobadas en 50 archivos; líneas 97,62 %, ramas 92,87 %, sentencias 95,41 %, funciones 94,82 % | [JUnit](frontend-tests.xml), [extracto de consola](local-20261027/frontend-summary.txt) |
| TypeScript, ESLint, build y sintaxis E2E | Aprobados | [Registro de comandos](local-20261027/checks.txt) |
| Ruff lint / formato | Aprobados; 212 archivos conformes | [Extracto de consola](local-20261027/backend-summary.txt) |
| Integración PostGIS | Bloqueada, sin Docker ni base aislada configurada | [Registro de entorno](local-20261027/checks.txt) |
| E2E Chrome / Firefox | Bloqueado en configuración, antes de iniciar navegadores; ninguna ronda ejecutada | [Resultado real del intento](local-20261027/offline-attempt/results.json) |

Los extractos son salidas parciales de los comandos ejecutados, no logs íntegros.
Los JUnit contienen los casos y sus resultados completos. Se sustituye el nombre
del equipo por `local-validation` y se eliminan rutas absolutas del usuario al
preparar las evidencias. Los resultados y marcas temporales no se alteran.
Vitest emitió avisos React `act(...)` en varios archivos, incluidos los tests de
formulario; no produjo fallos. Pytest emitió dos avisos de deprecación de
Starlette/TestClient; se conservan los resultados aprobados sin ocultar esa limitación.

No hay capturas de ECL-76: el API real no estaba levantado. Las capturas previas
de ECL-74 usan un API sintético y no se reutilizan como prueba de este E2E.
Una ejecución real crea otra carpeta `run-<timestamp>` con JSON y capturas nuevas;
nunca sobrescribir archivos ya versionados dentro de esta carpeta.

Instrucciones, matriz I01–I16 y pendientes en
[VALIDACION_US012](<../../VALIDACION_US012.md>). El PR preparado está en
[ECL-76-PR](<../../ECL-76-PR.md>). ECL-76 sigue pendiente de la campaña real,
del CI remoto y de las revisiones requeridas.

[↑ Índice del Sprint 3](<../../../README.md>)

[← Volver al README principal](../../../../../../README.md)
