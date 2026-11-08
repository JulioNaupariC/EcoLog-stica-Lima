# ECL-79 — Elegibilidad de conductores y RN-005 en ST-047

| Campo | Valor |
|---|---|
| Versión / fecha | 1.0.0 / 08/11/2026, America/Lima |
| Ticket | [ECL-79](https://continental-team-il84x39k.atlassian.net/browse/ECL-79), 5 Story Points |
| Rama | `feat/ECL-79-elegibilidad-conductores`, desde `main` `8a9f25d` |
| Fuente | [BDD ECL-47 / ST-021, D3/D4/F1/F2](<../../02 Planificación/BDD/ECL-47-ST-021-conductores.md>) y RN-005 |
| Responsable | José Delgadillo; identidad Git cotejada con `JoseDelgadillo277` |
| Revisores | @ANTONY-MUNIVE (backend), @JulioNaupariC (docs/BDD), @GiancarloSE (frontend) |

La asignación de ST-047 ahora comprueba licencia durante toda la conducción
prevista, disponibilidad durante la ruta y RN-005. La prueba no se sustituye
por `habilitado_asignacion` ni por el registro de una franja disponible. Las
rutas que no pueden recibir conductor conservan su solución y sus paradas.

El usuario autorizó expresamente ampliar los motivos públicos, añadir la
migración y ajustar el contrato para informar la causa de licencia vencida
exigida por D3. La interfaz presenta los nuevos motivos sin datos de licencia.
No se modifica el CRUD de conductores ni la lógica del ticket ECL-82 pendiente.
Terminología: [glosario ECL-99](CONVENCIONES_Y_GLOSARIO_ECL99.md).

## Contrato de cómputo

1. El repositorio selecciona candidatos con perfil y cuenta activos y rol
   CONDUCTOR. Incluye licencia y disponibilidad, aunque no sean suficientes,
   para poder diagnosticar el rechazo al conocer la ruta. El nombre histórico
   de su DTO interno `ConductorElegible` no acredita factibilidad; la consulta
   se denomina `conductores_candidatos` y el snapshot cuenta candidatos.
2. `plan_de_ruta` usa Haversine, factor de desvío y velocidad de ST-044, con
   minutos redondeados hacia arriba. Cada viaje se ubica lo antes posible
   entre salida/fin de servicio y ETA/regreso, interrumpiéndolo por los
   descansos explícitos del motor. Se incluye el retorno al depósito.
3. Servicio y espera ordinaria no suman conducción ni se transforman
   automáticamente en descanso. Un horario incompatible, una parada sin
   ubicación o un descanso fuera de ruta, superpuesto o durante servicio
   no autorizan asignación.
4. RN-005 admite **480 minutos** de conducción total y **240 minutos** desde
   el último descanso explícito de al menos **60 minutos**. Igualdad admitida;
   exceso rechazado. Una pausa de 59 minutos no reinicia el contador. Se
   evalúa cada ruta, no se confunde con duración de disponibilidad.
5. La disponibilidad cubre la ruta completa, incluyendo servicio, espera y
   descansos. Se admite `desde == salida` y `hasta == regreso`: no hay actividad
   posterior al extremo final del intervalo.
6. La licencia cubre todos los tramos de conducción en `America/Lima`.
   Su último día termina en la medianoche local siguiente. Los intervalos
   de conducción son `[inicio, fin)`: terminar exactamente en ese instante
   se admite; comenzar o seguir conduciendo desde él se rechaza.
   La fecha de creación de la corrida no sustituye al horario previsto.
7. Se conserva la selección determinista del primer candidato libre válido;
   cada conductor se usa como máximo una vez en la corrida. No se implementa
   reserva o coordinación entre optimizaciones distintas.

El cronograma reconstruido es una previsión con la matriz aproximada del
proyecto, no telemetría ni una medición de conducción real. El motor OR-Tools
conserva su restricción conservadora anterior, que cuenta servicio/espera para
limitar la búsqueda: ECL-79 valida asignación, sin relajar esa búsqueda ni
garantizar descubrir todas las soluciones posibles.

## Motivos públicos y migración

| Motivo | Causa verificada / prioridad |
|---|---|
| `JORNADA_INVIABLE` | El horario no admite un plan de conducción coherente o incumple RN-005; se evalúa primero |
| `SIN_CONDUCTOR_ELEGIBLE` | No quedan candidatos activos/libres tras las asignaciones previas |
| `DISPONIBILIDAD_INSUFICIENTE` | Quedan candidatos, pero ninguno cubre la ruta completa; incluye disponibilidad ausente |
| `LICENCIA_VENCIDA` | Entre los candidatos que cubren la franja, ninguna licencia cubre toda la conducción prevista |

Si se asigna conductor, el motivo es `null`. Ningún rechazo anula la corrida:
el estado sigue `COMPLETADA` y se conservan ruta, paradas, métricas y pedidos.
Los motivos pertenecen a **rutas sin conductor**, no al catálogo distinto de
pedidos no asignados. No se exponen DNI, número de licencia ni los perfiles de
los candidatos rechazados.

`0018_motivos_elegibilidad`, sobre `0017_parametros_versionados`, amplía el
CHECK `ck_ruta_motivo_sin_conductor`. No cambia columnas ni reescribe motivos
existentes. Su downgrade se niega si existen rutas con motivos nuevos; no los
convierte artificialmente al motivo antiguo. En una base sin esos datos se
probó downgrade/upgrade y comparación del esquema mediante Alembic.
`alembic heads` muestra una única cabeza: `0018_motivos_elegibilidad`.

El enum Pydantic actualiza OpenAPI/Swagger. El frontend valida los cuatro
motivos, conserva compatibilidad con fixtures anteriores sin motivo explícito
y muestra un mensaje legible por causa en el detalle de la ruta.
El cambio de contrato se comunica en el PR a los revisores de frontend/backend.

## BDD → prueba ejecutada

| Escenario | Prueba y resultado |
|---|---|
| D3, último día y medianoche de Lima | `test_D3_licencia_ultimo_dia_lima_y_cruce_medianoche`, `test_D3_se_evalua_conduccion_y_no_fecha_de_consulta_o_espera_final`; PostGIS `test_ECL79_D3_licencia_toda_conduccion_cruce_medianoche`. Incluye equivalencia UTC, fin exacto de vigencia y rechazo con `LICENCIA_VENCIDA`. |
| D4, disponibilidad de la ruta | `test_disponibilidad_cubre_toda_ruta_con_bordes_exactos`; PostGIS `test_ECL79_disponibilidad_se_comprueba_para_la_ruta_completa`. Bordes exactos admitidos, inicio un minuto tarde y fin un minuto antes rechazados. |
| F1, 8 h / 8 h 1 min | `test_F1_ocho_horas_admitidas_ocho_horas_un_minuto_rechazadas`, manteniendo los demás límites satisfechos. PostGIS verifica 8 h con pausa exacta y rechazo del exceso, sin perder la solución. |
| F2, continuidad y descanso | `test_F2_borde_cuatro_horas_sin_descanso`, `test_F2_descanso_exacto_reinicia_conduccion`: 239/240/241 minutos y pausas de 59/60/61 minutos. La integración F1/F2 verifica la persistencia y el motivo. |
| Servicio/espera y cronología | `test_plan_separa_conduccion_servicio_y_espera_con_tiempos_de_matriz`, `test_plan_interrumpe_conduccion_con_descanso_y_conserva_servicio`, casos de horario inválido y solapamiento. |
| Perfil, cuenta y rol reales | PostGIS `test_ECL79_candidatos_reales_excluyen_perfiles_no_autorizados`: perfil/cuenta inactivos, rol distinto, licencia vencida y disponibilidad ausente. |
| Motivo conocido y no pérdida de ruta | U `test_motivo_publico_refleja_causa_verificada`; PostGIS `test_ECL79_F1_F2_asignacion_persistida_y_solucion_conservada`: una ruta/parada guardadas, sin descartar la optimización. |
| Migración y rollback | `test_ECL79_migracion_0018_round_trip_y_una_cabeza`, `test_ECL79_downgrade_no_borra_motivos_operativos`; regresión de parámetros conserva la cabeza real al fallar su downgrade. |
| Consumo y presentación frontend | `operationRoutes.test.ts` admite los cuatro motivos y rechaza uno desconocido; `OperationRoutesPage.test.tsx` muestra las tres causas específicas sin datos personales. |

Archivos de referencia:

- [Dominio de elegibilidad](../../../backend/app/optimizacion/elegibilidad.py) y
  [pruebas de bordes](../../../backend/tests/unit/test_elegibilidad_conductores.py).
- [Servicio ST-047](../../../backend/app/services/optimizaciones.py),
  [pruebas U](../../../backend/tests/unit/test_optimizaciones_service.py) e
  [integración PostGIS](../../../backend/tests/integration/test_optimizaciones.py).
- [Migración 0018](../../../backend/alembic/versions/0018_motivos_elegibilidad.py).
- [Contrato frontend](../../../frontend/src/domain/operationRoutes.ts) y
  [detalle de ruta](../../../frontend/src/components/OperationRouteDetail.tsx).

Los bordes de integración utilizan datos y persistencia reales con un
resolver determinista para controlar minutos exactos; se distinguen de las
regresiones existentes que sí ejecutan OR-Tools, incluido el escenario de
150 pedidos/15 vehículos. No se presenta la prueba controlada como una
medición del rendimiento del solver.

## Resultados finales y evidencias

Python 3.12.10 con `requirements-dev.lock` en Docker, PostgreSQL 16/PostGIS 3.5
y Node 22.18.0. Base efímera exclusiva `ecologistica_ecl79_test`, desde
`template0` con solo PostGIS, sin publicar puertos ni tocar las bases demo.
La imagen de herramientas reutilizada se llama `ecologistica-ecl82-tests`:
contiene dependencias, no código de la rama ECL-82; el backend se monta desde
esta rama independiente de `main`.

| Verificación | Resultado |
|---|---|
| `ruff check .` / `ruff format --check .` | Correctos; 264 archivos con formato válido |
| Suite unitaria completa backend | **1212 aprobadas, 2 omitidas**; cobertura **95,37 %** (4557/4778 líneas) |
| Incremento afectado | Dominio, servicio y repositorio de optimización: **100 %** de líneas en cada módulo |
| Integración optimizaciones/modelo de rutas | **56 aprobadas**, incluye migración, protección de downgrade y cada motivo nuevo |
| Regresión de parámetros | **10 aprobadas**; integración total ejecutada: **66**, sin solapamiento entre archivos |
| Frontend `typecheck` / `lint` / `build` | Correctos |
| Suite completa frontend con cobertura | **900 aprobadas**; líneas **97,89 %**, statements **95,78 %**, branches **93,07 %**, functions **95,30 %**; todos los gates ≥80 % aprobados |
| Frontend afectado | Dominio y componente: 100 % de líneas; branches del componente 35/42 (83,33 %) |

Ejecución final sobre `8a9f25d` + cambios locales, `working_tree_dirty: true`;
no se atribuyen sus resultados al commit creado después de medir:

- [Resumen de la campaña final](evidencias/ECL-79/run-20261108T172711Z/summary.json).
- [JUnit backend](evidencias/ECL-79/run-20261108T172711Z/unit-tests.xml) y
  [cobertura XML](evidencias/ECL-79/run-20261108T172711Z/backend-coverage.xml).
- [JUnit de optimizaciones/modelo/migración](evidencias/ECL-79/run-20261108T172711Z/integration-tests.xml)
  y [JUnit de parámetros](evidencias/ECL-79/run-20261108T172711Z/parameter-tests.xml).
- [JUnit frontend](evidencias/ECL-79/run-20261108T172711Z/frontend-tests.xml),
  [LCOV](evidencias/ECL-79/run-20261108T172711Z/frontend-lcov.info) y
  [cobertura frontend extraída](evidencias/ECL-79/run-20261108T172711Z/frontend-coverage-summary.json).
- [Dockerfile de herramientas](evidencias/ECL-79/run-20261108T172711Z/Dockerfile.tests)
  y [Compose utilizado](evidencias/ECL-79/run-20261108T172711Z/compose.yaml).

El [registro previo a ampliar motivos](evidencias/ECL-79/run-20261108T171942Z/summary.json)
se conserva separado (1206 unitarias y 27 de integración); no se utiliza como
resultado final ni se suman pruebas repetidas. Los XML enumeran las dos
omisiones unitarias y los avisos de dependencias. Vitest emitió avisos `act`
en pruebas preexistentes; no hubo fallos de pruebas ni de sus umbrales.

## Reproducción

Con Python 3.12 y el lock instalados, desde `backend/`:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest tests/unit --cov=app --cov-fail-under=80
# TEST_DATABASE_URL privada: base *_test vacía, diferente de DATABASE_URL.
python -m pytest tests/integration/test_optimizaciones.py tests/integration/test_modelo_rutas.py tests/integration/test_parametros.py
python -m alembic heads
```

Desde la raíz:

```powershell
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run test:coverage
npm.cmd --prefix frontend run build
python scripts/check_docs.py
```

Para repetir en Docker, copiar los archivos de herramientas a `.tmp-ecl79/`
como `Dockerfile` y `compose.yaml`; crear `test.env` privado con usuario
`ecl79`, contraseña aleatoria, base de arranque `bootstrap` y
`TEST_DATABASE_URL` hacia `ecologistica_ecl79_test` en `db:5432`.
Construir la imagen indicada en Compose usando `backend/` como contexto;
crear la base de prueba desde `template0` y habilitar solo `postgis`.
Ejecutar `tests` con `--no-deps`; montar además `docs/` en `/docs` y `frontend/`
en `/frontend`, en solo lectura, para los fixtures de la suite unitaria.
Las pruebas arman sus protecciones solo sobre una base `_test` vacía autorizada.
No publicar el archivo de entorno ni usar una base de demostración para ellas.

## Alcance y revisión pendiente

No se modifica RN-005, el CRUD ni `habilitado_asignacion`. No se amplía el
catálogo de pedidos no asignados ni se relaja la búsqueda de OR-Tools.
Se mantienen los rechazos de licencia, disponibilidad y conducción como
decisiones distintas; un descanso no es un permiso para exceder ocho horas
totales. No hay coordinación de asignaciones entre corridas ni cambios
retroactivos de rutas existentes. Debe aplicarse la migración antes de servir
el código que persiste los nuevos motivos.

La evidencia nueva se enlaza en la BDD conservando sus escenarios e historial.
Auditoría técnica independiente, aprobación humana y revisión de alertas
CodeQL corresponden al PR. No se declara Done en Jira ni se integra en `main`
desde esta sesión implementadora.

[← Índice del Sprint 4](README.md)

[← Volver al README principal](../../../README.md)
