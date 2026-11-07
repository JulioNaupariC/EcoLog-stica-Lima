# ECL-14 — US-008: rutas y alertas en mapa

Historia: 8 Story Points; RF-008 y RNF-009. Se implementa la página
`/operacion/rutas` para Administrador y Operador conforme a la
[BDD US-008 ratificada, M01–M06](<../../02 Planificación/BDD/ECL-14-US-008-mapa.md>).
Se mantienen los términos del [glosario ECL-99](CONVENCIONES_Y_GLOSARIO_ECL99.md).

## Entrega y contrato

La página ofrece fecha de operación en Lima, paginación de optimizaciones,
selector de ejecución y lista de rutas. Cada ruta muestra vehículo, conductor
o ausencia de asignación, estado, distancia, duración, emisiones, combustible y
costo. El detalle incluye trazado, paradas numeradas, ETA estimada, ventanas
completas, estados y pedidos no asignados con sus motivos publicados.

La fuente predeterminada llama con cookie y sin caché HTTP a:

```text
GET /optimizaciones?fecha=AAAA-MM-DD&page=N&page_size=12
GET /optimizaciones/{optimizacion_id}
```

El adaptador `services/operationRoutes.ts` consume el contrato **ST-045 publicado**
en `backend/app/schemas/rutas.py`, que prevalece sobre el ejemplo provisional
del mensaje: las métricas están en `ruta.metricas` y las ventanas son timestamps
completos, no cadenas HH:mm. Se valida la respuesta antes de representarla:
UUID, fechas, offset de Lima, coordenadas, métricas, estados, geometría y
secuencias consecutivas desde 1. Se rechazan IDs repetidos y pedidos asignados
y no asignados simultáneamente. No se reordena visualmente una secuencia inválida
para ocultar el defecto.

La API actual ya sirve fixtures ST-045 e indica `simulado: true`; se muestra
un aviso persistente. Los componentes no importan esos JSON. Al conectar
ST-047 al mismo contrato, el adaptador HTTP seguirá consultando los mismos
endpoints y mostrará los datos reales con `simulado: false`, sin reemplazar
los componentes. No hay botón que genere optimizaciones ni endpoint inventado.

## Tráfico y alertas: límite confirmado con José

La BDD está aprobada, pero ST-045 todavía no publica `trafico` ni `alertas`.
José autorizó continuar con **SIN_DATOS y casos sintéticos**. Por ello:

- El adaptador HTTP actual entrega `SIN_DATOS`, fuente/hora nulas y ninguna
  medición. La pantalla informa expresamente que el servicio no publica alertas;
  no afirma ausencia de riesgos, congestión cero ni tráfico fluido.
- La ETA siempre se identifica como estimación del plan y conserva su hora de
  cálculo; si no se informa finalización, se distingue la hora de solicitud.
- `TrafficSnapshot` y `RouteAlert` son modelos internos de presentación,
  **no una ampliación de OpenAPI ni un contrato remoto publicado**.
- Los escenarios sintéticos M02/M03 prueban tramos en minutos, riesgo frente
  a bloqueo, fuente/hora/alcance/severidad y degradación T1 conservando T0.
- La conservación del último dato es en memoria, dentro de la misma página,
  sesión y optimización. Sin historial, una caída produce SIN_DATOS con hora
  nula. Al cambiar fecha/optimización o cerrar sesión no se mezclan mediciones.
- No hay polling automático, proveedor real ni catálogo de congestión o
  antigüedad arbitrario. Para consumir tráfico/alertas reales se ajustará solo
  el adaptador cuando backend publique sus campos aprobados. No se afirma que
  esa integración pendiente esté terminada.

## Mapa y alternativa accesible

Leaflet **1.9.4**, con tipos **1.9.21**, se fija en package.json y lockfile.
Se carga de forma diferida junto a su CSS. GeoJSON mantiene
`[longitud, latitud]`; solo al pasar a Leaflet se transforma a `[latitud, longitud]`.
Las teselas usan `https://tile.openstreetmap.org/{z}/{x}/{y}.png`, con atribución
visible **© OpenStreetMap contributors** y enlace a copyright. Se respeta la
caché del navegador; no hay descarga masiva ni precarga offline de teselas.

La lista ordenada es una alternativa completa: no exige abrir un marcador para
consultar ETA, ventana, estado, ubicación o alertas. Sus elementos admiten foco
y cada parada tiene un botón «Ver parada N en mapa» que abre su detalle y lleva
el foco al mapa. Los números del mapa son indicadores; las acciones de selección
se ofrecen en la lista con objetivos amplios para evitar controles solapados.
El mapa permite desplazamiento con flechas, zoom con teclado y ocultación;
el enlace a la lista devuelve el foco a su encabezado.

Si fallan las teselas, el trazado vectorial y la lista siguen disponibles con
un aviso. Los fallos de inicialización del mapa tampoco ocultan la lista.
Riesgo informativo y bloqueo configurado se distinguen mediante texto e iconos;
una alerta informativa no excluye una vía automáticamente.

## Estados, privacidad y ciclo de vida

Se distinguen carga, error de consulta, fecha sin optimizaciones, ejecución
EN_PROCESO, FALLIDA y COMPLETADA sin rutas. Una actualización fallida puede
conservar el último plan de esa misma ejecución con advertencia de vigencia.
No se generan recorridos de ejemplo para ocultar un fallo. El contenido técnico
de errores del servidor no se muestra ni se registra con datos personales.

Las peticiones se cancelan al cambiar contexto/desmontar y las respuestas
antiguas se ignoran. La navegación limita el detalle general a Administrador
y Operador; el backend mantiene su RBAC independiente. Un 401 devuelve al
flujo de sesión; 403 y 404 no se confunden con ausencia de optimizaciones.

## Validación y límites

Las pruebas de dominio, servicio HTTP, página, mapa y navegación cubren M01–M06.
La suite final pasó **836 pruebas en 57 archivos** con dos workers, sin cambiar
los umbrales: líneas **97,84 %**, ramas **93,11 %**, funciones **95,27 %** y
sentencias **95,71 %**. Typecheck, lint y build también pasaron. El dominio y
el adaptador HTTP nuevos alcanzaron 100 % en las cuatro medidas de cobertura.

| Escenario | Comprobación |
|---|---|
| M01 | Fixtures ST-045, ejes GeoJSON, mismo orden en mapa/lista, foco y selección por teclado |
| M02 | Puerto de presentación sintético: tramos con unidad, fuente/hora y riesgo distinto de bloqueo |
| M03 | Tráfico en T0 y caída en T1, sin modificar artificialmente la hora ni perder el plan |
| M04 | Rechazo de geometría/secuencia inválida, errores seguros y navegación para cinco roles |
| M05 | SIN_DATOS con hora nula sin historial; caída real de peticiones de teselas controlada por el script |
| M06 | Vacío, EN_PROCESO y FALLIDA distintos; Chrome/Firefox y responsive |

La matriz compartida de 15 pruebas de US-006/US-009 y la validación humana
con lector de pantalla no se declaran completadas por estas comprobaciones.

El script `frontend/scripts/verify-operation-routes.mjs` prueba la SPA compilada
y Leaflet real con **respuestas HTTP interceptadas de los fixtures ST-045**.
No acredita autenticación real, integración con backend, optimizador real ni
proveedor de tráfico. Verifica Chrome y Firefox a 360/1280 px, teclado, caída
controlada de teselas, estados y accesibilidad con axe y Lighthouse snapshot.
Snapshot audita la página autenticada sin recargarla al login.

Ejecución final: Chrome **156.0.8078.80** y Firefox **146.0.1**. Los seis
cortes de viewport/tema tuvieron 0 violaciones de axe y ancho de documento
igual al viewport. Lighthouse accesibilidad obtuvo **100/100 (score 1,00)** en tema claro
y oscuro, sin auditorías fallidas. Se conservan dos resultados incompletos
de axe por corte (contraste y correspondencia de nombre de controles) para
revisión humana; no se cuentan como aprobaciones manuales.

Evidencia nueva, sin sobrescribir archivos anteriores:

- [Resultados finales y versiones de navegador](validaciones/evidencias/ECL-14/run-20261107-final/results.json)
- [Metadatos y hashes SHA-256 de las fuentes probadas](validaciones/evidencias/ECL-14/run-20261107-final/run-start.json)
- [Lighthouse claro](validaciones/evidencias/ECL-14/run-20261107-final/lighthouse-light.json) · [Lighthouse oscuro](validaciones/evidencias/ECL-14/run-20261107-final/lighthouse-dark.json)
- [Chrome 1280 claro](validaciones/evidencias/ECL-14/run-20261107-final/chrome-light-1280.png) · [Chrome 360 claro](validaciones/evidencias/ECL-14/run-20261107-final/chrome-light-360.png)
- [Chrome 1280 oscuro](validaciones/evidencias/ECL-14/run-20261107-final/chrome-dark-1280.png) · [Chrome 360 oscuro](validaciones/evidencias/ECL-14/run-20261107-final/chrome-dark-360.png)
- [Firefox 1280](validaciones/evidencias/ECL-14/run-20261107-final/firefox-light-1280.png) · [Firefox 360](validaciones/evidencias/ECL-14/run-20261107-final/firefox-light-360.png)

Las comprobaciones automáticas no equivalen a una sesión humana con lector de
pantalla. Los resultados incompletos de axe se conservan para revisión, al igual
que la auditoría independiente, las alertas CodeQL y la aprobación humana.

## Reproducción

Desde `frontend/`:

```powershell
npm.cmd ci
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run test:coverage -- --maxWorkers=2
$env:VITE_API_BASE_URL='http://127.0.0.1:8000'
$env:VITE_DEMO_ITINERARY='false'
npm.cmd run build
npm.cmd run preview -- --host 127.0.0.1 --port 5184 --strictPort
```

En otra consola, desde la raíz, con el preview activo:

```powershell
npm.cmd install --prefix .tmp-ecl14-browser --save-exact playwright@1.58.2
.\.tmp-ecl14-browser\node_modules\.bin\playwright.cmd install firefox
$env:ECL14_OUTPUT='.tmp-ecl14-browser/nueva-ejecucion'
node frontend/scripts/verify-operation-routes.mjs
python scripts/check_docs.py
```

Chrome se busca en la ubicación estándar de Windows; se puede configurar
`ECL14_CHROME`. `ECL14_TOOLS`, `ECL14_ORIGIN` y `ECL14_OUTPUT` permiten cambiar
las rutas de herramientas, origen y evidencias. El script rechaza sobrescribir
archivos de una ejecución anterior. No se modificaron evidencias versionadas,
requisitos, reglas de negocio, backend, migraciones ni OpenAPI.

Fuentes técnicas: [Leaflet 1.9.4](https://leafletjs.com/reference-1.9.4.html),
[política de teselas OSM](https://operations.osmfoundation.org/policies/tiles/).

[Índice del Sprint 4](README.md)

[← Volver al README principal](../../../README.md)
