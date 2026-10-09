# Evidencia ST-035 / ECL-61

La evidencia principal está en [campaign-20261009](campaign-20261009/).
Abrir `reporte.html` después de generar el reporte desde los JSON.

| Archivo | Propósito |
|---|---|
| environment.json | Fecha, Git, versiones, CPU/RAM, procesos, red y parámetros |
| campaign.json | Resultados por perfil y P95 agregado calculado desde duraciones |
| campaign-consolidated.json | Derivado con recuperación; conserva la corrida interrumpida y declara los tres perfiles del agregado |
| reporte.html | Reporte local generado desde los resultados medidos |
| 01/02/03-*.png | Capturas del reporte real renderizado en Chrome |
| sha256.json | Integridad de los archivos exportados al cerrar la campaña |
| audit.json | Recálculo independiente de la exportación, sin acceder a BD/API |
| baseline.json por perfil | IDs/conteos previos, revisión Alembic y versiones BD |
| manifest.json por perfil | Semilla, horarios, clientes, URL local y duraciones |
| requests.jsonl.gz | Todos los intentos, fases, tiempos, estados y correlación |
| persisted.jsonl.gz | UUID/cliente/referencia leídos realmente de PostgreSQL |
| monitor.jsonl y metrics-*.prom | Concurrencia instrumentada, muestreo y recursos |
| availability.jsonl | Sondeos de proceso y lectura BD, con UTC y latencia |
| locust*.csv/html/log | Exportación nativa; percentiles aproximados por fase |
| api.log y postgres.log | Registros de ejecución de los procesos aislados |
| generator-source.py | Fuente del generador correspondiente al perfil, cuando incluida |

Los directorios `smoke`, `smoke2` y `smoke3` corresponden a comprobaciones
previas del entorno/generador; **no son las tres repeticiones completas**.
El primero falló por restricciones de ejecución de PostgreSQL en el sandbox;
el segundo detectó la necesidad de habilitar PostGIS antes de migrar.
Se corrigió la preparación; `smoke3` creó 1,000 pedidos y ejecutó solo 10 s
estables de estrés. Se conservan sus resultados sin presentarlos como campaña
de aceptación. Las capturas dentro de `smoke3` también son diagnóstico.

Resultados de calidad: `unit-tests.xml`, `unit-coverage.xml`,
`load-tools-unit.xml` y `load-tools-coverage.xml`. La ejecución en GitHub
Actions se registra separadamente cuando José abra el PR.

Los archivos contienen datos sintéticos; no contienen cookies, contraseñas,
hashes de credenciales, tokens, DNI ni datos de clientes reales.
El XML unitario conserva el nombre de un caso negativo con la cadena inválida
`$argon2id$broken`, definida en `tests/unit/test_passwords.py`; no es un hash
de credencial. `evidence-sha256.json` permite comprobar la integridad de los
archivos publicados.
La carpeta `.tmp-st035-pg` queda ignorada y no forma parte de la evidencia pública.

La recuperación se encuentra en [recovery-20261009](recovery-20261009/), con
su `campaign.json` nativo intacto y otra base de datos. El reporte principal
enlaza sus archivos mediante rutas relativas; conservar ambas carpetas juntas.
Las fuentes del orquestador/generador exportadas corresponden a cada ejecución.
La versión final añade anotaciones y comprobaciones del temporizador; las
diferencias de medición se documentan sin reescribir los datos anteriores.

Consultar [VALIDACION_ST035.md](../../VALIDACION_ST035.md) y
[INCIDENCIAS.md](INCIDENCIAS.md) antes de interpretar resultados como
cumplimiento de capacidad. **No se ha medido el SLA mensual.**
