# ECL-76 / ST-043 — Validación de incidencias US-012

Fecha de ejecución: **27/10/2026**, zona `America/Lima`.
Rama: `test/ECL-76-pruebas-incidencias`. Historia: ECL-18 / US-012.
Fuente: [BDD aprobada ECL-72, I01–I16](<../../../02 Planificación/BDD/ECL-72-ST-039-incidencias.md>).

El incremento añade pruebas sobre los casos que faltaban en la interfaz y un
script de navegador contra el API real. **La aceptación completa sigue pendiente:**
este equipo no tiene Docker, base PostGIS local ni configuración privada demo.
El intento E2E terminó en configuración antes de abrir un navegador; no se
acredita ningún ciclo E2E ni persistencia real en esta ejecución.

## Entorno y evidencia

Windows / PowerShell, Node 22.18.0, Python 3.14.4. La suite backend se ejecutó
con las dependencias disponibles en el equipo; CI usa Python 3.12.10 y las
versiones lock. El frontend se instaló con `npm ci` y su lock vigente.
Base de partida: `main` actualizado mediante `git pull --ff-only`; el SHA
exacto está en [el intento registrado](<evidencias/ECL-76/local-20261027/offline-attempt/results.json>).
`workingTreeDirty: true` identifica que se probó el incremento aún sin commit;
no se atribuyen estas pruebas a un commit posterior.

- [Evidencias y resultados de comandos](<evidencias/ECL-76/README.md>).
- [JUnit backend: 139 pruebas de incidencias](<evidencias/ECL-76/local-20261027/backend-incidencias.xml>).
- [JUnit frontend completo](<evidencias/ECL-76/frontend-tests.xml>).

En las tablas, **U** significa prueba unitaria/API con dependencias simuladas,
**UI** significa Vitest/jsdom con IndexedDB simulado, **INT** requiere PostgreSQL
y **E2E** requiere navegador, API y base reales. U/UI aprobadas no sustituyen INT/E2E.
«N/A» en navegador corresponde a pytest o jsdom, no a Chrome/Firefox.

## Archivos de pruebas

Las referencias de nombre de la matriz se resuelven en estos archivos:

| Clave | Archivo |
|---|---|
| API | [test_incidencias_api.py](../../../../backend/tests/unit/test_incidencias_api.py) |
| Servicio | [test_incidencias_service.py](../../../../backend/tests/unit/test_incidencias_service.py) |
| INT | [test_incidencias.py](../../../../backend/tests/integration/test_incidencias.py) |
| Formulario | [IncidentCreatePage.test.tsx](../../../../frontend/src/pages/IncidentCreatePage.test.tsx) |
| Dominio | [incident.test.ts](../../../../frontend/src/domain/incident.test.ts) |
| Cola | [incidentSync.test.ts](../../../../frontend/src/services/incidentSync.test.ts) |
| Hook | [useIncidentSynchronization.test.tsx](../../../../frontend/src/hooks/useIncidentSynchronization.test.tsx) |
| Listado | [OperationIncidentsPage.test.tsx](../../../../frontend/src/pages/OperationIncidentsPage.test.tsx) |
| E2E | [verify-incidents-offline.mjs](../../../../frontend/scripts/verify-incidents-offline.mjs) |

## Matriz BDD por tipo de ruta

Cada fila incluye el nombre de una prueba existente o añadida. Los nombres con
parámetros se ejecutan para cada variante definida en su archivo. Evidencia
**B** = JUnit backend; **F** = JUnit frontend; **E** = intento E2E enlazado arriba.

| Escenario BDD | Tipo de ruta | Prueba: archivo y nombre | Navegador | Resultado real | Evidencia |
|---|---|---|---|---|---|
| I01 — Registrar una incidencia válida sin ruta | Dorada | API: `test_I01_conductor_registra_incidencia_201`; Servicio: `test_I01_alta_sin_parada_queda_pendiente_y_auditada_sin_datos_personales`; Formulario: `ruta dorada: envío válido muestra acuse e ID del servidor`; INT: `test_I01_registrar_incidencia_valida_sin_ruta` | N/A; Chrome/Firefox previstos | U/UI aprobadas; INT bloqueada. E2E incluye alta online, sin ejecución real | B/F/E |
| I02 — Operación consulta los pendientes | Feliz | API: `test_I02_administrador_y_operador_listan_sin_datos_personales` (ambos roles); Listado: `I02: presenta hora de Lima, catálogo, severidad textual con icono y solo el nombre del conductor`; INT: `test_I02_operacion_consulta_pendientes_ordenados_y_paginados` | N/A | U/UI aprobadas; orden, desempate, total y páginas con BD real pendientes de INT | B/F |
| I03 — Registrar con parada propia | Feliz | Servicio: `test_I03_alta_con_parada_propia`; Formulario: `ruta de borde: GPS rechazado permite seleccionar parada propia con coordenadas`; INT: `test_I03_registrar_con_parada_propia` | N/A | U/UI aprobadas para propiedad; INT bloqueada; escenario parcial por jornada y ruta de negocio aún no implementadas (ECL-82) | B/F; defecto conocido abajo |
| I04 — Datos incompletos conservan el borrador | Infeliz | Servicio: `test_I04_campo_obligatorio_ausente_o_null`; Formulario: `I04 ruta infeliz: falta %s, conserva borrador tras recargar sin encolar ni enviar` (tipo, severidad, ubicación, hora y varios); INT: `test_I04_campos_obligatorios_ausentes_422_sin_reserva` | N/A | U/UI aprobadas; borrador íntegro, sin POST ni cola; persistencia/ausencia de reserva real pendiente de INT | B/F |
| I05 — Hora futura o sin zona | Infeliz | Servicio: `test_I05_fecha_sin_zona_es_invalida`, `test_I05_I14_tolerancia_futura_inclusiva_y_sin_antiguedad`; Formulario: `I05 hora futura ruta infeliz: rechaza envío y conserva el valor íntegro tras recargar`; INT: `test_I05_hora_futura_o_sin_zona_422` | N/A | U/UI aprobadas. La UI genera hora automática con zona; API cubre fecha sin zona; INT bloqueada | B/F |
| I06 — Observación de más de 500 caracteres | Infeliz | Servicio: `test_I06_observacion_de_501_puntos_de_codigo_sin_truncar`; Formulario: `I06 observación Unicode de 501 caracteres ruta infeliz: rechaza envío y conserva el valor íntegro tras recargar`; INT: `test_I06_observacion_de_501_puntos_de_codigo_422_sin_truncar` | N/A | U/UI aprobadas, incluidos emoji; INT bloqueada | B/F |
| I07 — Catálogos, coordenadas, UUID y campos ajenos inválidos | Infeliz | Servicio: `test_I07_variaciones_invalidas_rechazadas`, `test_I07_coordenadas_no_finitas`, `test_I07_parada_inexistente_devuelve_422_generico`; API: `test_I05_I06_I07_entrada_invalida_422_sin_eco`; INT: `test_I07_variaciones_invalidas_422_sin_persistencia_ni_eco` | N/A | U aprobadas; catálogos inválidos, extremos excedidos, tipos inválidos, UUID y extras parametrizados; INT bloqueada | B |
| I08 — Crear con rol sin permiso | Infeliz | API: `test_I08_rol_sin_permiso_de_crear_recibe_403_y_se_audita` (Administrador, Operador, Analista, Auditor); INT: `test_I08_crear_con_rol_sin_permiso_403` | N/A | U aprobadas; INT bloqueada | B |
| I09 — Analista, Auditor o Conductor consultan pendientes | Infeliz | API: `test_I09_analista_auditor_y_conductor_reciben_403_sin_datos`; INT: `test_I09_analista_auditor_o_conductor_no_listan` | N/A | U aprobadas para los tres roles; INT bloqueada | B |
| I10 — Sin sesión o con parada ajena | Infeliz | API: `test_I10_sin_sesion_responde_401_en_ambos_endpoints`, `test_I10_403_generico_sin_perfil_o_con_parada_ajena`; INT: `test_I10_sin_sesion_401_en_ambos_endpoints`, `test_I10_parada_de_otro_conductor_403_generico` | N/A | U aprobadas; INT bloqueada | B |
| I11 — Mismo identificador con otro contenido | Infeliz | Servicio: `test_I11_mismo_operation_id_otro_contenido_devuelve_409`; Formulario: `I11 ruta infeliz: conflicto visible conserva operación sin corrección ni reintento automático`; INT: `test_I11_mismo_operation_id_otro_contenido_devuelve_409` | N/A | U/UI aprobadas; cambios por campo y conflicto visible sin nueva operación; INT bloqueada | B/F |
| I12 — Sin conexión, recarga y sincronización | Borde | Formulario: `ruta de borde: offline, recarga y reconexión confirman una sola operación`; E2E: fase `I12/I13 ruta de borde`, diez rondas por navegador con itinerario preservado | jsdom; Chrome/Firefox previstos | UI aprobada. **E2E bloqueado; 0/10 ejecutadas en cada navegador**, sin capturas reales | F/E |
| I13 — Respuesta perdida, replay y concurrencia | Borde | Cola: `ruta de borde: offline y respuesta perdida reutilizan exactamente operación y contenido`; Servicio: `test_I13_reenvio_equivalente_devuelve_200_sin_duplicar_ni_revalidar`, `test_I13_carrera_relee_y_responde_200_o_409_nunca_5xx`; INT: `test_I13_dos_primeros_envios_concurrentes_un_201_y_un_200`, `test_I13_replay_equivalente_devuelve_la_respuesta_original`; E2E: primera ronda pierde el acuse 201 y exige 200 de replay | N/A; Chrome/Firefox previstos | U/UI aprobadas; concurrencia atómica y traza única reales pendientes de INT, E2E bloqueado | B/F/E |
| I14 — Límites válidos y selección de catálogos | Borde | Servicio: `test_I14_limites_validos_y_observacion_normalizada`, `test_I14_matriz_de_seis_tipos_por_tres_severidades`; Dominio: `I14 ruta de borde: admite catálogo %s / %s`, `I05/I14 ruta de borde: reloj fijo y desfase %i ms`; INT: `test_I14_limites_validos_se_aceptan_y_conservan` | N/A | U/UI aprobadas: 18 combinaciones, Unicode, extremos, pasado, T0 y +5 min inclusivo; INT bloqueada | B/F |
| I15 — Paginación inválida y lista vacía | Borde | API: `test_I15_paginacion_o_estado_invalidos_422_sin_elementos`, `test_I15_page_size_maximo_es_valido`; Listado: `I15: pagina con teclado, actualiza la página actual y vuelve a la anterior`, `muestra vacío sin inventar datos y permite actualizar`; INT: `test_I15_lista_vacia_y_pagina_posterior_a_la_ultima` | N/A | U/UI aprobadas; INT bloqueada | B/F |
| I16 — Cambio de cuenta y fallos de sincronización | Borde | API: `test_I16_cookie_changed_in_another_tab_never_registers_foreign_outbox`; Cola: `ruta de borde: cuenta ajena, cambio de cookie y cancelación nunca envían el pendiente`, `ruta infeliz: %i conserva contenido y pausa reintentos automáticos`, `ruta de borde: 5xx y confirmación inválida no retiran el pendiente`; Hook: `ruta de borde: reautenticación del mismo propietario reanuda 401, no 403/409/422`; Formulario: `ruta infeliz: almacenamiento bloqueado no confirma encolado`; INT: `test_I16_mismo_uuid_de_otro_conductor_es_independiente` | N/A | U/UI aprobadas para aislamiento, errores y almacenamiento; INT bloqueada | B/F |

## Comandos ejecutados

Desde la raíz, salvo el bloque backend. Resultados detallados en el README de
evidencias. La primera instalación npm falló en el entorno restringido; una
segunda ejecución con acceso de red instaló las 257 dependencias correctamente.
El primer lint encontró una separación de línea en una prueba nueva; se corrigió
y la nueva ejecución pasó. Estos incidentes de preparación no son bugs del producto.

```powershell
git switch main
git pull --ff-only
git switch -c test/ECL-76-pruebas-incidencias
Push-Location frontend
npm.cmd ci --cache ../.npm-cache --no-audit --no-fund
Pop-Location
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run test:coverage -- --maxWorkers=1 --reporter=default --reporter=junit --outputFile.junit='../docs/03 Implementación/Sprint 03/validaciones/evidencias/ECL-76/frontend-tests.xml'
npm.cmd --prefix frontend run build
node --check frontend/scripts/verify-incidents-offline.mjs
Push-Location backend
python -m ruff check .
python -m ruff format --check .
python -m pytest tests/unit -q --cov=app --cov-fail-under=80
python -m pytest tests/unit/test_incidencias_api.py tests/unit/test_incidencias_service.py -q --junitxml='../docs/03 Implementación/Sprint 03/validaciones/evidencias/ECL-76/local-20261027/backend-incidencias.xml'
Pop-Location
$env:ECL76_OUTPUT = Join-Path $PWD 'docs/03 Implementación/Sprint 03/validaciones/evidencias/ECL-76/local-20261027/offline-attempt'
node frontend/scripts/verify-incidents-offline.mjs
Remove-Item Env:ECL76_OUTPUT
python scripts/check_docs.py
```

`docker compose ps` no pudo ejecutarse porque `docker` no existe en PATH ni en
la ubicación habitual de Docker Desktop. No se ejecutó integración sin una base
aislada `_test`, ni se sustituyó PostGIS por SQLite. El resultado del script Node
es `passed: false`, fase `configuration`; faltan las contraseñas demo privadas.

## Reproducir E2E con Docker local

Usar exclusivamente el entorno demo sintético. Seguir primero las comprobaciones,
la creación privada de `.env`, el build, PostGIS y las migraciones del
[README principal](../../../../README.md). El nombre de la base debe terminar
en `_demo` para que el seed permita la operación. No reutilizar bases o volúmenes
de origen desconocido. Preparar las cinco variables `SEED_DEMO_PASSWORD_*` de
forma privada (mínimo 12 caracteres) en `.env`; no publicar valores ni logs de login.

El contenedor backend no recibe las claves de seed del `.env` automáticamente.
Pasar el archivo al contenedor explícitamente:

```powershell
docker compose --env-file .env run --rm --no-deps --volume "${PWD}/.env:/run/ecl76-demo.env:ro" backend python -c "from dotenv import load_dotenv; load_dotenv('/run/ecl76-demo.env', override=False); from scripts.seed_demo import main; raise SystemExit(main())"
docker compose --env-file .env up -d --wait backend
docker compose --env-file .env stop frontend
```

La recarga sin conexión necesita el service worker del **build de producción**.
El frontend Compose normal usa Vite dev y no satisface ese requisito. En una
terminal dedicada, servir el build desde la imagen del mismo proyecto:

```powershell
docker compose --env-file .env run --rm --no-deps --service-ports frontend sh -c "npm run build && npm run preview -- --host 0.0.0.0 --port 5173 --strictPort"
```

En otra terminal, desde la raíz, con Google Chrome instalado:

```powershell
npm.cmd install --prefix .tmp-ecl76 --no-save --package-lock=false playwright@1.56.1
node .tmp-ecl76/node_modules/playwright/cli.js install firefox
npm.cmd --prefix frontend run test:incidents-offline
```

Playwright queda en la carpeta temporal ignorada, fuera de las dependencias de la
aplicación. También se admite `PLAYWRIGHT_MODULE` con la ruta absoluta a un módulo
Playwright ya instalado y sus navegadores compatibles. Chrome usa el motor
Chromium mediante `channel: 'chrome'`; Firefox usa el binario de Playwright.

El script inicia sesiones reales de Conductor y Operador en contextos separados,
registra con red, ejecuta diez ciclos offline/recarga/reconexión por navegador,
verifica itinerario, propietario y payload estable, pierde solo la primera
respuesta ya persistida y exige replay 200 con el acuse original. No cambia
fechas ni la autenticación del API. El script deja las incidencias sintéticas
creadas y cierra solo las sesiones que abrió.

El contrato `GET /incidencias` omite `operation_id`. Para comprobar unicidad sin
modificarlo, el script conserva el mapeo operación → observación sintética única
→ ID del acuse. Busca la observación en todas las páginas y exige un único
registro con el ID confirmado. Una repetición que creara otro ID con el mismo
payload haría fallar la prueba. La unicidad de auditoría y la concurrencia de dos
primeros envíos se verifican adicionalmente con INT, no mediante el listado.

Cada ejecución crea un directorio nuevo `run-<timestamp>` con `results.json` y
capturas offline/reconectado de ambos navegadores. Si se usa `ECL76_OUTPUT`, debe
ser un directorio que aún no exista. Un error conserva fase y tipo sin imprimir
mensajes privados de Playwright. No sobrescribir evidencia histórica.

## CI, defectos y cierre

El workflow existente ejecuta pytest unitario, pytest de integración contra
PostGIS aislado y Vitest con cobertura. Las pruebas añadidas entran en el job
Frontend automáticamente; se añade la comprobación de sintaxis del script E2E.
El E2E completo queda como campaña local porque necesita build/preview, dos
navegadores y cuentas demo provisionadas contra una base local. No se instala
Playwright en los jobs normales ni se añaden secretos para simular su ejecución.

Defecto conocido: [ECL-82](https://continental-team-il84x39k.atlassian.net/browse/ECL-82),
validación de jornada de I03, ya documentado en la línea base. Se registra como
parcial y no se cambia su alcance. No se encontraron nuevos fallos del producto
en las suites ejecutadas; no se creó ni se cambió ningún ticket Jira.

Antes de cerrar ECL-76: ejecutar INT y E2E real, registrar los 10/10 de cada
navegador y adjuntar capturas; si falla el producto, registrar el resultado y
abrir el bug correspondiente en Jira. Actualizar esta matriz con evidencia de
esa ejecución. Permanecen pendientes CI remoto, revisión de alertas CodeQL,
auditoría técnica independiente y aprobación humana. Preparar el PR como **Draft**.

[↑ Índice del Sprint 3](<../README.md>)

[← Volver al README principal](../../../../README.md)
