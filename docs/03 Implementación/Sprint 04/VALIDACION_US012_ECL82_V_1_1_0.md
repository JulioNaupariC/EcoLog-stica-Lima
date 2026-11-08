# US-012 — Validación de jornada de la parada, ECL-82

| Campo | Valor |
|---|---|
| Versión | 1.1.0, complemento de la validación US-012 del Sprint 3 |
| Fecha de ejecución | 08/11/2026, America/Lima; horas UTC en los JUnit |
| Ticket | [ECL-82](https://continental-team-il84x39k.atlassian.net/browse/ECL-82), 2 Story Points |
| Rama | `fix/ECL-82-jornada-incidencia` |
| Base de código | `8a9f25d` de `main`, más los cambios locales ECL-82; `working_tree_dirty: true` en el resumen |
| Responsable | José Delgadillo, frontend y QA |
| Revisores previstos | @ANTONY-MUNIVE (backend), @JulioNaupariC (documentación) |
| Fuente de aceptación | [BDD aprobada ECL-72 / ST-039](<../../02 Planificación/BDD/ECL-72-ST-039-incidencias.md>), I03, I10 e I13 |
| Historial previo | [VALIDACION_US012, Sprint 3](<../Sprint 03/validaciones/VALIDACION_US012.md>), I03 parcial antes de ST-046 |

**I03 queda cubierto para propiedad y jornada** por pruebas unitarias y de
integración con el modelo persistido ST-046. El documento histórico conserva
su resultado original. No se cambian los requisitos ni la BDD para adaptar
la aceptación al código; esta versión actualiza la evidencia de ejecución.
Terminología: [glosario ECL-99](CONVENCIONES_Y_GLOSARIO_ECL99.md).

## Cambio y contrato HTTP

Una incidencia nueva con `parada_id` requiere que la asignación pertenezca al
usuario autenticado y que su ruta vinculada pertenezca al perfil del mismo
conductor. La fecha de la ruta (`Ruta.fecha_operacion`) debe ser igual a
`ocurrida_en.astimezone(ZoneInfo("America/Lima")).date()`.
Se utiliza `RutaRepository.jornada_de_asignacion` en la misma sesión/transacción
del alta. La asociación con la ruta se conserva por la cadena
incidencia → asignación → parada planificada → ruta; no se agrega otro ID al payload.

| Caso | Respuesta | Persistencia |
|---|---|---|
| Parada propia y fecha local de ocurrencia igual a la fecha de su ruta | 201, pendiente de validación | Una incidencia y una auditoría de alta |
| Parada propia de otra jornada | 403, `{"detail":"Acceso denegado"}` | Sin incidencia ni auditoría de alta |
| Asignación propia con ruta de otro conductor o sin conductor | Mismo 403 genérico | Sin alta |
| Asignación antigua sin parada de ruta vinculada | Mismo 403 genérico | Sin alta; no se infiere una fecha |
| Parada inexistente | 422 genérico, contrato previo | Sin alta |
| Reporte válido sin parada | 201, contrato previo | Alta permitida |
| Reenvío equivalente de operación existente, aunque cambie la jornada | 200, acuse original | Sin duplicación ni nueva auditoría de alta |
| Misma operación con contenido distinto | 409, contrato previo | Original conservado |
| Fallo al consultar la ruta | 503, `Servicio no disponible` | Sin alta, error interno oculto |

La jornada se compara con la **ocurrencia**, no con el día de recepción ni
con la ventana del pedido. El día de UTC puede ser distinto al de Lima:
`2026-10-27T04:59:59Z` pertenece al 26/10 en Lima y
`2026-10-27T05:00:00Z` al 27/10. Se mantiene la tolerancia futura de cinco
minutos y la ausencia de antigüedad máxima. Un reporte offline tardío de una
jornada válida sigue siendo admisible.

La búsqueda idempotente por conductor/operación y la comparación de contenido
ocurren **antes** de consultar parada y jornada. También la relectura tras una
carrera concurrente conserva ese orden. No se reescribe ni se invalida un alta
confirmada por cambios posteriores en la ruta.

No hay migraciones ni dependencias nuevas. OpenAPI/Swagger incluye la jornada
entre las causas del 403 del POST. Registrar una incidencia no cambia el estado
de la ruta, de la parada ni de la optimización, ni dispara reoptimización.

## Escenario BDD → prueba

**U** = unitarias con repositorios simulados; **INT** = HTTP, sesiones,
PostgreSQL/PostGIS, claves foráneas y auditoría reales; **UI** = Vitest/jsdom,
sin navegador real. Los nombres se resuelven en los archivos enlazados abajo.

| Escenario BDD | Prueba | Resultado de esta versión |
|---|---|---|
| I03 — Parada de itinerario y jornada del reporte | U: `test_I03_alta_con_parada_propia`; INT: `test_I03_registrar_con_parada_propia` con asignación, parada planificada y ruta persistidas | **Cubierto**: 201, conductor correcto, una incidencia pendiente; ruta, parada y optimización conservan sus estados |
| I03 — Otra jornada y límite de medianoche Lima | U: `test_ECL82_jornada_no_autorizada_sin_persistir`, `test_ECL82_fecha_se_calcula_en_lima_sin_limitar_antiguedad`; INT: `test_ECL82_jornada_usa_fecha_lima_y_rechaza_otra_sin_persistir` | **Cubierto**: fechas locales correctas admitidas, jornada distinta rechazada con 403 sin persistencia |
| I03/I10 — Ruta no autorizada o no acreditable | U: variantes sin ruta, otro conductor y sin conductor; INT: `test_ECL82_asignacion_propia_sin_ruta_autorizada_403_generico` | **Cubierto**: idéntico cuerpo 403 para los tres casos |
| I13 — Replay con contexto de parada cambiado | U: `test_ECL82_reenvio_con_parada_no_consulta_jornada_ni_propietario`; INT: `test_ECL82_replay_no_revalida_jornada_y_nueva_operacion_si` | **Cubierto**: 201 inicial, 200 con acuse idéntico tras cambiar la fecha de ruta; otra operación 403; otro contenido 409; una incidencia y una auditoría |
| I13 — Carrera de dos primeros envíos | U: `test_ECL82_carrera_relee_sin_consultar_jornada_otra_vez`; INT previa: `test_I13_dos_primeros_envios_concurrentes_un_201_y_un_200` | **Cubierto**: relectura sin nueva consulta de jornada; regresión concurrente HTTP aprobada |
| I01/I05/I07/I10/I14 — Contratos previos | Suites completas de incidencias U/INT | Sin regresiones: alta sin parada, tiempo, parada inexistente/ajena y validaciones previas |
| I12/I13/I16 — Cola offline, respuesta perdida y aislamiento | `incidentSync.test.ts`, `useIncidentSynchronization.test.tsx` | **19 UI aprobadas**: payload/operación conservados, replay y manejo de errores; no se afirma una campaña nueva Chrome/Firefox |

Archivos:

- [Servicio y pruebas U](../../../backend/tests/unit/test_incidencias_service.py).
- [API y OpenAPI, pruebas U](../../../backend/tests/unit/test_incidencias_api.py).
- [Pruebas INT de incidencias](../../../backend/tests/integration/test_incidencias.py).
- [Pruebas INT de datos demo](../../../backend/tests/integration/test_seed_demo.py).
- [Cola offline](../../../frontend/src/services/incidentSync.test.ts).
- [Hook de sincronización](../../../frontend/src/hooks/useIncidentSynchronization.test.tsx).

## Compatibilidad de la demo

El usuario autorizó adaptar la siembra: sus asignaciones históricas no tienen
ruta planificada y no deben eludir la nueva validación. `seed_demo.py` crea las
tres incidencias nuevas sin parada. Al repetir la siembra, conserva el
`parada_id` de cada operación ya registrada, incluso una referencia antigua
sin ruta. La prueba
`test_ECL82_seed_reenvia_incidencia_legacy_con_parada_sin_ruta` comprueba ese
reenvío sin duplicar ni borrar la referencia histórica.

No se migran ni se inventan jornadas para asignaciones antiguas. Las incidencias
nuevas que requieran una parada necesitan la ruta real de ST-046; las demás
pueden enviarse sin parada. La cola conserva su política existente ante 403:
mantiene el reporte y pausa el reintento automático, sin descartar datos.

## Verificación y evidencia reproducible

Entorno: Docker sobre Windows, Python **3.12.10** con
`backend/requirements-dev.lock`, PostgreSQL 16/PostGIS 3.5; Node 22.18.0 para
Vitest. Base efímera exclusiva `ecologistica_ecl82_validation_test`, creada desde
`template0` con solo PostGIS, sin puertos publicados ni volumen persistente.
No se utilizaron las bases demo ni credenciales reales.

| Verificación | Resultado |
|---|---|
| `ruff check .` | Correcto |
| `ruff format --check .` | Correcto, 261 archivos formateados |
| `pytest tests/unit --cov=app --cov-fail-under=80` | 1177 aprobadas, 2 omitidas; **95,27 %** (4456/4677 líneas) |
| Cobertura del servicio afectado `app/services/incidencias.py` | **100 %** |
| Cobertura del router afectado `app/api/incidencias.py` | **98,15 %** |
| Revalidación U de incidencias tras completar las pruebas de concurrencia y OpenAPI | **171 aprobadas**; incluye la prueba agregada durante la suite global |
| `pytest tests/integration/test_incidencias.py tests/integration/test_seed_demo.py` | **91 aprobadas**, sin omisiones |
| Vitest, cola y hook de sincronización | **19 aprobadas** en dos archivos |

Los conteos de la revalidación se solapan con los de la suite global: no se
suman como pruebas únicas. El XML distingue las dos omisiones de la suite
global. La cobertura se obtiene de esa suite; la revalidación posterior solo
modifica/amplía pruebas, sin cambiar el código de aplicación medido.
Lint/formato se comprobaron también sobre los archivos finales de backend.

Evidencia original de la ejecución local, con árbol de trabajo modificado:

- [Resumen verificable](evidencias/ECL-82/run-20261108T165807Z/summary.json).
- [JUnit de la suite global](evidencias/ECL-82/run-20261108T165807Z/unit-tests.xml).
- [Cobertura XML](evidencias/ECL-82/run-20261108T165807Z/coverage.xml).
- [JUnit U de revalidación](evidencias/ECL-82/run-20261108T165807Z/focused-unit-tests.xml).
- [JUnit de integración](evidencias/ECL-82/run-20261108T165807Z/integration-tests.xml).
- [JUnit de la cola offline](evidencias/ECL-82/run-20261108T165807Z/frontend-offline.xml).
- [Imagen de herramientas](evidencias/ECL-82/run-20261108T165807Z/Dockerfile.tests) y
  [Compose aislado utilizado](evidencias/ECL-82/run-20261108T165807Z/compose.yaml).

En una instalación Python 3.12 preparada con el lock y una base `_test` vacía
autorizada, desde `backend/`:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest tests/unit --cov=app --cov-fail-under=80
# Definir TEST_DATABASE_URL privadamente, diferente de DATABASE_URL.
python -m pytest tests/integration/test_incidencias.py tests/integration/test_seed_demo.py
```

Desde la raíz:

```powershell
npm.cmd --prefix frontend run test -- src/services/incidentSync.test.ts src/hooks/useIncidentSynchronization.test.tsx
python scripts/check_docs.py
```

Para reproducir con Docker, copiar los dos archivos de herramientas a
`.tmp-ecl82/` como `Dockerfile` y `compose.yaml`; este último tiene rutas
relativas a esa ubicación. Preparar allí `test.env` privado con
`POSTGRES_USER=ecl82`, una contraseña aleatoria, `POSTGRES_DB` de arranque y
`TEST_DATABASE_URL` apuntando a la base de validación vacía terminada en `_test`.
Nunca versionar ese archivo. Construir la imagen con
`docker build -t ecologistica-ecl82-tests -f .tmp-ecl82/Dockerfile backend`.
Crear la base desde `template0` y habilitar solo `postgis` mediante `psql`.
Ejecutar el servicio `tests` con `--no-deps -e PYTHONPATH=/app` para evitar
recrear la base en `tmpfs`. Las pruebas unitarias con el contenedor requieren
montar también `docs/` en `/docs` y `frontend/` en `/frontend`, en solo lectura,
para sus fixtures preexistentes.

Durante la preparación hubo fallos de entorno, corregidos antes de la
ejecución válida: Docker estaba detenido; faltaban rutas de importación y
fixtures en los montajes; el esquema inicial del contenedor incluía objetos
adicionales y se creó una base desde `template0`. Cambiar el archivo de entorno
recreó el contenedor efímero, por lo que la base se preparó de nuevo y se usó
`--no-deps`. Esos intentos no se presentan como pruebas aprobadas.

No se ejecutó toda la suite de integración del proyecto ni una nueva campaña
E2E de navegador. No se modificó código frontend, requisitos, reglas de negocio
ni evidencias históricas. CI, revisión de alertas CodeQL, auditoría técnica
independiente y aprobación humana se registran en el PR; esta sesión no se
autoaprueba ni integra en `main`.

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0, validación histórica del Sprint 3 | 27/10/2026 | Propiedad de parada y cola offline; I03 parcial por jornada sin modelo de rutas |
| 1.1.0, ECL-82 | 08/11/2026 | Valida fecha local y conductor de la ruta en altas nuevas; I03 cubierto; replay, compatibilidad demo y regresiones verificadas |

[← Índice del Sprint 4](README.md)

[← Volver al README principal](../../../README.md)
