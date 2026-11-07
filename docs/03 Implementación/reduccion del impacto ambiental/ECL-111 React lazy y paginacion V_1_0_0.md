# ECL-111 — React.lazy, Suspense y listados de 12 registros

| Campo | Valor |
|---|---|
| Ticket | [ECL-111](https://continental-team-il84x39k.atlassian.net/browse/ECL-111), 3 SP |
| Autor | José Delgadillo, frontend y QA |
| Rama | `feat/ECL-111-lazy-paginacion` |
| Revisores previstos | @GiancarloSE por frontend y @JulioNaupariC por documentación |
| Base de trabajo | `main`: `ed2b42804f73e94228a28cd4f8373ea7349b1809` |
| ANTES oficial | Commit de ECL-108: `e09dcd80e32431018d4020bb02c89ffae7505705` |
| Fecha de medición | 06/11/2026, America/Lima; los JSON conservan sus marcas UTC del 07/11 |

## Cambio implementado

Once páginas secundarias se importan con `React.lazy`: Inicio, itinerario,
registro de incidencias, pedidos, vehículos, conductores, preferencias, usuarios,
incidencias pendientes, cambio de contraseña y 404. Login y los shells permanecen
en la carga inicial. `Suspense` muestra «Cargando página…» con `role="status"`
y `aria-live="polite"`, dentro del contenido principal y conservando la navegación.
El título se actualiza con la página resuelta, después de cargar su chunk.

Los cuatro listados solicitan `page_size=12`; los controles tienen nombre de
navegación accesible, botones anterior/siguiente, límites deshabilitados y anuncio
de página con `aria-live="polite"`. La creación de un vehículo invalida la lista
antigua y actualiza la primera página. Se preserva la protección contra respuestas
tardías y se recupera una página válida si desaparece la última de vehículos.

### Dependencia ECL-109: implementación y límite actual

En el corte examinado, [ECL-109](https://continental-team-il84x39k.atlassian.net/browse/ECL-109)
estaba «Tareas por hacer» y `GET /vehiculos` aún devolvía un array completo.
No se modifica backend dentro de este ticket.

El servicio frontend acepta el sobre `{items, page, page_size, total}`, con
validación de tipos, límites y registros, y solicita explícitamente páginas de
12. Es el formato de paginación ya usado por los otros listados; su integración
real con vehículos debe confirmarse al entregar ECL-109.

Para conservar operativa la versión actual también admite el array existente:
lo conserva en memoria durante la vista y muestra como máximo 12 filas por página,
sin volver a descargarlo al cambiar de página. Actualizar o crear invalida esa
copia. **Esta compatibilidad no reduce el primer payload de vehículos** ni acredita
que el backend ya esté paginado. El formato paginado se verificó con pruebas
controladas; la navegación con la API real usó el contrato actual de `main`.

## Fragmentos ANTES / DESPUÉS para el informe 01

Las fuentes ANTES se guardaron antes de modificar código, extraídas directamente
del commit fijo de ECL-108. Las fuentes DESPUÉS incluyen ruta y hash de blob Git:

- [Fuentes ANTES](evidencias/ECL-111/fragmentos-antes.txt).
- [Fuentes DESPUÉS](evidencias/ECL-111/fragmentos-despues.txt).
- [Contexto, hashes y manifiesto offline](evidencias/ECL-111/contexto.json).

Ejemplo de `frontend/src/app/App.tsx`:

```tsx
// ANTES: la página se importa al iniciar.
import { VehiclesPage } from '../pages/VehiclesPage'

// DESPUÉS: se solicita cuando esa página se renderiza.
const VehiclesPage = lazy(() => import('../pages/VehiclesPage')
  .then(module => ({ default: module.VehiclesPage })))
```

El límite que envuelve las rutas en DESPUÉS es:

```tsx
function PageContent({ children }: { children: ReactNode }) {
  return <Suspense fallback={<p className="field-hint" role="status" aria-live="polite">Cargando página…</p>}>
    <PageTitle />{children}
  </Suspense>
}
```

En conductores se reemplazan `listDrivers(nextPage)` y la división entre `10`
por `listDrivers(nextPage, PAGE_SIZE)` y la división entre `PAGE_SIZE = 12`.
Usuarios e incidencias cambian su `PAGE_SIZE` de `20` a `12`. En vehículos se
introducen `listVehicles(targetPage, 12)`, los metadatos de página y los controles.
Los snapshots conservan las funciones completas, no ejemplos inventados de MERN.

## Build: medición ANTES / DESPUÉS

Se construyó un checkout aislado del frontend ANTES y el árbol DESPUÉS con los
mismos paquetes fijados, Node 22.18.0, Vite 8.3.5 y
`VITE_API_BASE_URL=http://127.0.0.1:8001`. Ambos ejecutaron `npm run build`.
Los logs se conservaron en UTF-8, sin alterar sus cifras:
[build ANTES](evidencias/ECL-111/build-antes.txt) y
[build DESPUÉS](evidencias/ECL-111/build-despues.txt).

| Medida | ANTES | DESPUÉS |
|---|---:|---:|
| Chunk de entrada, tamaño mostrado por Vite | 436,20 kB | 253,64 kB |
| Chunk de entrada, gzip mostrado por Vite | 130,87 kB | 79,67 kB |
| JavaScript inicial completo, bytes reales | 436200 | 327683 |
| gzip inicial completo, cálculo independiente Node | 129680 | 104588 |
| Total de archivos JS generados, bytes | 436200 | 446139 |

El **JavaScript inicial completo disminuye 24,88 %**. Se suman el script de
entrada y sus dependencias estáticas precargadas por `index.html`; no se toma
solo el chunk de entrada para anunciar la reducción. DESPUÉS incluye `index`,
`ui` y `offlineStorage`. La reducción gzip calculada con `node:zlib.gzipSync`
es **19,35 %**; ese cálculo independiente tiene valores distintos al compresor
del reporte de Vite y no se mezclan ambas series.

El total generado de JavaScript aumenta 9939 bytes por la separación en módulos.
El precache existente descarga todos los JS/CSS/fuentes para el modo offline;
por ello el ahorro inicial de ejecución no equivale a una reducción de toda la
transferencia de instalación del service worker. No se afirma cumplir los umbrales
de FCP, LCP, TBT o peso total de la rúbrica con esta medición de build.

[Medición exacta, archivos y hashes](evidencias/ECL-111/medicion-bundle.json) ·
[Script de recálculo](evidencias/ECL-111/medir-bundle.mjs).

## Offline y navegación por roles

`scripts/build-offline.mjs` ya enumera todos los `.js`, `.css` y `.woff2` de
`dist/assets`. Se verificó que incluye los chunks nuevos `DriverItineraryPage`
e `IncidentCreatePage`; no fue necesario cambiar el script ni el service worker.
Su manifiesto y versión exacta están conservados en `contexto.json`.

| Verificación | Resultado | Evidencia |
|---|---|---|
| Navegación y títulos | 55/55: once rutas por cada uno de los cinco roles, con login real y denegaciones según RBAC | [Resultados](evidencias/ECL-111/navegacion/results.json) |
| Primer acceso a chunk no visitado | Formulario de incidencia abierto sin red, sin visita anterior de su módulo por la página, y recargado offline | [Captura](evidencias/ECL-111/navegacion/chunk-no-visitado-offline.png) |
| Sincronización Chrome | 10/10 ciclos offline/recarga/reconexión, ACK perdido y replay sin duplicados | [Resultados y versiones](evidencias/ECL-111/offline/results.json) |
| Sincronización Firefox | 10/10 ciclos con las mismas comprobaciones y API real | [Resultados y versiones](evidencias/ECL-111/offline/results.json) |
| Capturas offline | Formulario y estado de reconexión por navegador | [Chrome offline](evidencias/ECL-111/offline/chrome-offline.png) · [Chrome reconectado](evidencias/ECL-111/offline/chrome-reconnected.png) · [Firefox offline](evidencias/ECL-111/offline/firefox-offline.png) · [Firefox reconectado](evidencias/ECL-111/offline/firefox-reconnected.png) |

Se ejecutó `npm run test:incidents-offline`, el script existente de ECL-76 sin
modificaciones; por eso su JSON original conserva `ticket: ECL-76`. La repetición
se usa como prueba de regresión de ECL-111, con salida en una carpeta nueva.
Creó datos ficticios únicamente en la base demo aislada del proyecto
`ecologistica-lima-ecl111`, con API 8001 y preview 5174. La demo anterior no se
detuvo ni se reutilizó su volumen. Las credenciales y cookies permanecieron privadas.

## Accesibilidad Lighthouse

Los JSON históricos de ECL-108 solo midieron Performance: no contenían una
puntuación de Accesibilidad. Se añadió una **medición complementaria** del código
de ese mismo commit ANTES, sin modificar las evidencias originales.

Ambas versiones se sirvieron en modo producción/preview (ANTES 5175, DESPUÉS 5174),
con el mismo API y dataset de itinerario, Chrome 156.0.8078.80, Lighthouse 12.8.2,
Navigation Desktop, incógnito y extensiones deshabilitadas. Se mantuvo la sesión
del conductor, `disableStorageReset: true`, y se vació la caché HTTP antes de cada
corrida. Solo se seleccionó la categoría Accesibilidad. Son condiciones nuevas
comparables entre sí; no se reinterpretan como la campaña histórica de Performance
con Vite en desarrollo de ECL-108.

| Página | ANTES: tres corridas | Mediana ANTES | DESPUÉS: tres corridas | Mediana DESPUÉS |
|---|---|---:|---|---:|
| `/login`, sin sesión | 100 / 100 / 100 | 100 | 100 / 100 / 100 | 100 |
| `/conductor/itinerario`, conductor demo | 100 / 100 / 100 | 100 | 100 / 100 / 100 | 100 |

[Resumen](evidencias/ECL-111/accesibilidad/results.json) ·
[Doce JSON Lighthouse originales](evidencias/ECL-111/accesibilidad/).
No se atribuye una puntuación Lighthouse a las vistas de Operador que pierden
su identidad al recargar en el código base; la matriz de navegador prueba sus
rutas mediante navegación SPA. Un 100 automatizado tampoco declara conformidad
WCAG completa ni reemplaza la comprobación manual.

## Pruebas y reproducción

`npm run typecheck`, `npm run lint` y la ejecución final
`npm run test -- --coverage --maxWorkers=2` pasaron. Esta última ejecuta la suite
Vitest completa: **51 archivos y 746 pruebas aprobadas**, sin aumentar los
tiempos máximos ni modificar aserciones para ocultar fallos.

| Cobertura global | Valor | Umbral |
|---|---:|---:|
| Sentencias | 95,41 % | 80 % |
| Ramas | 92,95 % | 80 % |
| Funciones | 94,75 % | 80 % |
| Líneas | 97,66 % | 80 % |

[Reporte textual](evidencias/ECL-111/cobertura.txt). Los módulos de aplicación
afectados también superan el 80 % de ramas: App 80,35 %, vehículos 98,46 %,
conductores 90,21 %, usuarios 86,30 % y servicio de vehículos 100 %.
Las pruebas nuevas verifican el fallback pendiente, el título al resolver,
13 vehículos repartidos 12+1 con teclado, respuesta paginada y metadatos inválidos,
recuperación de última página y el envío de `page_size=12`.

La [primera ejecución completa](evidencias/ECL-111/cobertura-inicial.txt) también
pasó con el paralelismo predeterminado. Una
[repetición posterior](evidencias/ECL-111/paralela-con-timeouts.txt) registró
34 timeouts de cinco segundos, incluidos módulos sin cambios. Se repitió con
dos workers para limitar la concurrencia y pasó 746/746 en 101,56 s. No se atribuye
una causa de hardware como hecho probado; se conserva el resultado fallido y la
configuración de la ejecución final para revisión.

Los scripts de reproducción conservados son
[navegación](evidencias/ECL-111/verificar-navegacion.mjs),
[accesibilidad](evidencias/ECL-111/accesibilidad.mjs) y
[medición de bundle](evidencias/ECL-111/medir-bundle.mjs).
Los dos primeros usan las dependencias temporales en `.tmp-ecl108/node_modules`
(Playwright Core 1.65.0, Puppeteer Core 24.43.1 y Lighthouse 12.8.2), Chrome instalado
y el `.env` privado con cuentas demo. Para repetir, instalar esas versiones en
esa carpeta temporal ignorada; servir los builds comparados en los puertos
indicados y preparar la API con CORS para ambos orígenes. La configuración temporal
de puertos y CORS no es un cambio de infraestructura de la aplicación.

Para conservar los registros históricos, usar directorios de salida nuevos:

```powershell
# Desde frontend/: verificaciones de código.
npm run typecheck
npm run lint
npm run test -- --coverage --maxWorkers=2
npm run build

# Desde la raíz: recalcular sin sobrescribir el JSON existente.
node 'docs/03 Implementación/reduccion del impacto ambiental/evidencias/ECL-111/medir-bundle.mjs' .tmp-ecl111/antes/frontend/dist frontend/dist .tmp-ecl111/otra-medicion.json
$env:ECL111_NAV_OUTPUT = '.tmp-ecl111/otra-navegacion'
node 'docs/03 Implementación/reduccion del impacto ambiental/evidencias/ECL-111/verificar-navegacion.mjs'
$env:ECL111_A11Y_OUTPUT = '.tmp-ecl111/otra-accesibilidad'
node 'docs/03 Implementación/reduccion del impacto ambiental/evidencias/ECL-111/accesibilidad.mjs'
python scripts/check_docs.py
```

La regresión offline requiere preview del build, no Vite dev. Desde `frontend/`,
definir privadamente `OFFLINE_API_URL`, `OFFLINE_PREVIEW_URL`, `PLAYWRIGHT_MODULE`,
`PLAYWRIGHT_BROWSERS_PATH` y un `ECL76_OUTPUT` nuevo antes de ejecutar
`npm run test:incidents-offline`. Los valores usados se describen arriba; Firefox
de pruebas se instaló bajo `.tmp-ecl111/browsers`. Las variables de contraseña
se leen del `.env` de la raíz y nunca se pasan por argumento ni se serializan.

Antes del cierre falta confirmar el contrato real paginado de ECL-109, auditoría
técnica independiente y revisión humana por los dueños de ambas áreas. El PR se
entrega en borrador; no se declara integrado ni se modifica planificación o
requisitos para ocultar esa dependencia.

Referencias de implementación:
[React.lazy](https://react.dev/reference/react/lazy) y
[Suspense](https://react.dev/reference/react/Suspense).

[← Índice del Sprint 4](<../Sprint 04/README.md>)

[← Volver al README principal](../../../README.md)
