# Informe 01 — Reducción del impacto ambiental (Green IT)

**Proyecto:** EcoLogística Lima — DistriRápido S.A.C.

| Metadato | Valor |
|---|---|
| Ticket | [ECL-117](https://continental-team-il84x39k.atlassian.net/browse/ECL-117), 3 SP |
| Autor | Antony Munive Rios — @ANTONY-MUNIVE. ECL-117 se reasignó a él el 10/11/2026 para cumplir el plazo del 12/11/2026. La redacción contó con apoyo de IA (Claude) y cada cifra se contrastó con la evidencia enlazada |
| Revisor | Frank Roy Yupanqui Acevedo — @FrankRoyYA; Julio Armando Naupari Camarena — @JulioNaupariC, opcional |
| Versión | 1.0.0 |
| Fecha de elaboración | 10/11/2026, America/Lima |
| ANTES | `e09dcd80e32431018d4020bb02c89ffae7505705`, commit de `main` medido en ECL-108 el 06/11/2026 |
| DESPUÉS | `e58c65d35002b3b5bed270f7f40ae687096367b0`, medido en ECL-115 el 08/11/2026 |
| Rúbrica | Inspección 4, «Reducción del impacto ambiental, estándares de ingeniería de software»: criterios 1, 3 y 4 |

## 1. Introducción y propósito

EcoLogística Lima optimiza rutas de reparto para reducir recorrido, consumo y
emisiones. Una aplicación que promueve la sostenibilidad también debe medir su
propio impacto: cada byte que viaja por la red y cada petición que atiende un
servidor consumen energía en el centro de datos, en la red y en el dispositivo
del usuario.

Este informe documenta **las ocho optimizaciones de la rúbrica** aplicadas al
sistema, con su código ANTES y DESPUÉS, la comparación de las mediciones
reproducibles de ECL-108 (ANTES) y ECL-115 (DESPUÉS) y la estimación de energía
y CO₂e con el modelo SWDM v4 (ECL-116). El
[Informe 02](<02 Estandares Ingeniería de software V_1_0_0.md>) contiene el marco
de estándares (ISO/IEC 25010, GSF, W3C WSG 1.0 y matriz de mapeo).

**Regla de honestidad.** Toda cifra procede de una medición o de un cálculo
reproducible. Cuando un umbral no se pudo medir o la mejora no apareció, se
informa el valor real y la causa. No se copian cifras ni código del ejemplo MERN
del docente.

## 2. Diagnóstico inicial (línea base ECL-108)

La línea base se midió el 06/11/2026 sobre el commit ANTES, con el frontend
servido por Vite en modo desarrollo. El
[registro completo](<evidencias/antes/run-2026-11-06T23-50-12-524Z/README.md>)
conserva los JSON originales de Lighthouse y de Network.

| Campo | Valor |
|---|---|
| Equipo | Intel Core i9-14900HX, 15,73 GiB de RAM, Windows 11 Home Single Language 10.0.26300 |
| Navegador y herramienta | Chrome 156.0.8078.80 en incógnito y sin extensiones; Lighthouse 12.8.2, Navigation, Performance, Desktop |
| Lighthouse | 1350 × 940, DPR 1, throttling `simulate` con RTT 40 ms, 10 240 Kbps y CPU ×1, `disableStorageReset: true` |
| Network | DevTools real, sin throttling, `Disable cache` activo, recarga completa hasta `networkidle0` + 1 s |
| Aplicación | `compose.yaml` sin cambios; Vite en desarrollo, API en el puerto 8000 y frontend en el 5173 |
| Migración | `0013_incidencias (head)` |
| Dataset | 8 clientes, 5 vehículos, 4 conductores, 20 pedidos, 5 asignaciones y 3 incidencias ficticias (`backend/scripts/seed_demo.py`) |
| Muestra | 3 corridas por página y 20 respuestas por endpoint; la mediana de cada métrica es independiente |

| Página | Rol | Corridas | Performance /100 | FCP ms | LCP ms | TBT ms | CLS | Transferido (bytes) | Peticiones |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `/login` | Sin sesión | 3/3 | 55 | 5653,69 | 10743,54 | 0 | 0,000005295 | 11 434 626 | 88 |
| `/` | Operador | 0/3 | NM | NM | NM | NM | NM | NM | NM |
| `/vehiculos` | Operador | 0/3 | NM | NM | NM | NM | NM | NM | NM |
| `/conductor/itinerario` | Conductor demo | 3/3 | 55 | 5677,36 | 10911,03 | 0 | 0,019688179 | 11 438 644 | 90 |

**NM = no medible.** En el código base, la identidad de Operador solo vive en
memoria: al recargar, la aplicación redirige a `/login` (`recallDriver` en
`frontend/src/app/App.tsx`; `offlineAccess.ts` solo persiste el rol Conductor).
Una redirección a login no es una medición de Inicio ni de Vehículos, de modo
que esas dos páginas no tienen cifras ni porcentajes de mejora en este informe.

La línea base no cumple Performance ≥ 90, FCP ≤ 1,0 s, LCP ≤ 1,4 s ni
peso ≤ 1,1 MB. Solo TBT y CLS están dentro de los umbrales. Línea base de la API
(media de 20 respuestas HTTP 200, `Accept-Encoding: identity`):

| Endpoint | Media ms | Media bytes del cuerpo |
|---|---:|---:|
| `/vehiculos` | 7,46 | 1183 |
| `/conductores?page=1` | 8,09 | 951 |
| `/incidencias?page=1` | 8,13 | 1255 |

## 3. Las ocho optimizaciones

### 3.0 Equivalencias MERN → FastAPI, SQLAlchemy, PostgreSQL y React

La rúbrica se plantea con MERN. Nuestro sistema usa otro stack; esta tabla
explica la equivalencia de cada técnica y dónde no aplica igual.

| Técnica de la rúbrica (MERN) | Equivalente en EcoLogística Lima |
|---|---|
| `.select()` + `.lean()` de Mongoose | `select(col1, col2…)` + `.mappings()` de SQLAlchemy: filas planas sin hidratar entidades ORM |
| `skip()` / `limit()` | `OFFSET` / `LIMIT` con `page` y `page_size` |
| Índices de MongoDB | Índices de PostgreSQL (`EXPLAIN`); ver la limitación en 3.1 |
| `compression` de Express | `GZipMiddleware` de Starlette (API) y `gzip` de Nginx (estáticos) |
| `ETag` / `Cache-Control` de Express | `ConditionalGetMiddleware` propio (ETag débil, 304) y `Cache-Control` de Nginx |
| `React.lazy` / `Suspense` | Igual; Vite genera un chunk por página |
| Imágenes WebP/AVIF | No aplica a la aplicación: no hay imágenes raster propias; se optimizó la fuente tipográfica |
| Reducción de dependencias | Análisis del bundle de Vite; las seis dependencias directas se usan |
| SVG inline | Iconos Lucide como componentes React que renderizan SVG inline |

### 3.1 Optimización 1 — Consultas con columnas mínimas (ECL-109)

**Diagnóstico.** El listado de conductores cargaba las entidades `Conductor` y
`Usuario` completas, incluidos DNI, teléfono, número de licencia, correo y hash
de contraseña, aunque la respuesta solo muestra ocho campos.

**Implementación.** `backend/app/repositories/conductores.py` selecciona solo
las ocho columnas necesarias y devuelve filas planas. Los datos personales ya no
salen de la base de datos en el listado, lo que además refuerza la minimización
de datos.

```python
# ANTES (e09dcd8): entidades ORM completas
query = (
    select(Conductor, Usuario)
    .outerjoin(Usuario, Usuario.usuario_id == Conductor.usuario_id)
    .order_by(Conductor.conductor_id)
    .offset((page - 1) * page_size)
    .limit(page_size)
)
rows = [(driver, account) for driver, account in self._session.execute(query)]
```

```python
# DESPUÉS (ECL-109): ocho columnas como filas planas
query = (
    select(
        Conductor.conductor_id, Conductor.nombre,
        Conductor.disponible_desde, Conductor.disponible_hasta,
        Conductor.estado, Conductor.licencia_vigente_hasta,
        Usuario.rol.label("cuenta_rol"), Usuario.estado.label("cuenta_estado"),
    )
    .outerjoin(Usuario, Usuario.usuario_id == Conductor.usuario_id)
    .order_by(Conductor.conductor_id)
    .offset((page - 1) * page_size)
    .limit(page_size)
)
return list(self._session.execute(query).mappings()), total or 0
```

**Resultado y límites.** En la medición real, los cuerpos de `/conductores?page=1`
(951 bytes) y de `/incidencias?page=1` (1255 bytes) no cambian: con 4 y 3
registros, la proyección de columnas no modifica el JSON de respuesta. El beneficio
es que no se leen ni hidratan columnas sensibles. **No se agregó ningún índice
nuevo** y no se declara mejora por índices: el dataset de la medición es de unos
pocos registros y no permite observar ese efecto. Los tiempos medios de la API no
mejoraron (ver 3.2 y la sección 4). Detalle y pruebas:
[ECL-109 en el README del backend](<../../../backend/README.md#green-it-consultas-y-paginación--ecl-109>).

### 3.2 Optimización 2 — Paginación de 12 registros (ECL-109 y ECL-111)

**Diagnóstico.** `GET /vehiculos` devolvía la flota completa como lista y los
listados de usuarios, conductores, clientes e incidencias usaban 20 registros por
página por defecto.

**Implementación backend.** `GET /vehiculos` devuelve `{items, page, page_size, total}`
con `page_size` de 12 por defecto (máximo 100). Los otros cuatro listados bajan su
`page_size` por defecto de 20 a 12 sin cambiar sus máximos.

```python
# ANTES (e09dcd8): toda la flota
@router.get("", response_model=list[VehicleResponse])
def list_vehicles(...) -> list[VehicleResponse]:
    return [VehicleResponse.model_validate(row) for row in _translate(service.list_all)]
```

```python
# DESPUÉS (ECL-109): una página
@router.get("", response_model=VehiclePage)
def list_vehicles(..., page: int = Query(1, ge=1),
                  page_size: int = Query(12, ge=1, le=100)) -> VehiclePage:
    return _translate(lambda: service.list_page(page, page_size))
```

**Implementación frontend (ECL-111).** Los cuatro listados piden `page_size=12`
y muestran controles accesibles de página anterior y siguiente. En conductores se
sustituye `listDrivers(nextPage)` y la división entre `10` por
`listDrivers(nextPage, PAGE_SIZE)` con `PAGE_SIZE = 12`; usuarios e incidencias
cambian su `PAGE_SIZE` de `20` a `12`. Los fragmentos completos ANTES y DESPUÉS
están en [ECL-111](<ECL-111 React lazy y paginacion V_1_0_0.md>).

**Resultado.** Cálculo sintético, **no** es la medición DESPUÉS: con la flota de
50 vehículos de `loadtest/campaign.py`, el JSON pasa de 11 691 B a 2878 B en la
primera página de 12 (75,4 % menos antes de GZip). En el dataset real de 5
vehículos se devuelve todo el conjunto más el envoltorio de página, por lo que el
cuerpo de `/vehiculos` **aumenta** de 1183 a 1227 bytes (+44; +3,72 %) y la media
de 7,46 ms a 9,90 ms. Con 20 muestras no se atribuye ese aumento a una causa
concreta ni se oculta: la paginación solo reduce el payload cuando hay más de 12
registros.

### 3.3 Optimización 3 — Recursos estáticos y fuentes; sin imágenes raster (ECL-112)

**Diagnóstico.** El inventario de `frontend/public/` y `frontend/src/` no
contiene PNG, JPEG, WebP ni AVIF propios: no hay imágenes que convertir y no se
fabricaron imágenes para cumplir la rúbrica. El recurso estático más pesado era
la fuente Inter, que se distribuía en dos archivos (subconjuntos latino y latino
extendido).

**Implementación.** Se elimina la regla `@font-face` del subconjunto latino
extendido y se conserva el latino, que cubre los caracteres del español
comprobados. Se mantienen `font-display: swap` y los pesos 100–900.
Fragmento ANTES (ruta `frontend/src/styles/base.css`, en ambos commits ANTES):

```css
/* ANTES: segundo archivo de la misma familia */
@font-face {
  font-family: "Inter Variable";
  font-style: normal;
  font-display: swap;
  font-weight: 100 900;
  src: url("@fontsource-variable/inter/files/inter-latin-ext-wght-normal.woff2") format("woff2-variations");
  unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, /* … */ U+A720-A7FF;
}
```

```css
/* DESPUÉS: se conserva solo el subconjunto latino */
@font-face {
  font-family: "Inter Variable";
  font-style: normal;
  font-display: swap;
  font-weight: 100 900;
  src: url("@fontsource-variable/inter/files/inter-latin-wght-normal.woff2") format("woff2-variations");
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, /* … */ U+FEFF, U+FFFD;
}
```

**Resultado.**

| Medida (build de producción) | ANTES inmediato | DESPUÉS | Diferencia |
|---|---:|---:|---:|
| WOFF2 emitidos y precargados | 2 | 1 | −1 |
| Bytes de fuentes | 133 324 | 48 256 | −85 068 (−63,8 %) |
| Archivos declarados en la precarga offline | 32 | 31 | −1 |

«ANTES inmediato» es `main` `1b8a5501d27bf42c3bd04718add156eb5ba89f67`, que ya
incluye ECL-87, y no el commit de la línea base ECL-108; así se aísla el cambio
de ECL-112 de los demás tickets.

La fuente extendida no se solicita en login, por lo que la reducción está en lo
que se distribuye y precarga, no en la transferencia de esa navegación (la
mediana de login varió solo 421 bytes, por el CSS servido). Las capturas de login
antes y después tienen el mismo SHA-256 y Chrome identifica Inter para los 16
glifos del español comprobados. Detalle y evidencias: [ECL-112](<ECL-112 recursos estaticos V_1_0_0.md>).

### 3.4 Optimización 4 — Carga diferida y división de código (ECL-111)

**Diagnóstico.** Todas las páginas se importaban al iniciar y se empaquetaban en
un único chunk de entrada de 436 200 bytes.

**Implementación.** Once páginas secundarias se importan con `React.lazy` y se
envuelven en `Suspense`, con un mensaje accesible (`role="status"`,
`aria-live="polite"`). Login y los contenedores principales permanecen en la
carga inicial.

```tsx
// ANTES: la página se importa al iniciar.
import { VehiclesPage } from '../pages/VehiclesPage'

// DESPUÉS: se solicita cuando esa página se renderiza.
const VehiclesPage = lazy(() => import('../pages/VehiclesPage')
  .then(module => ({ default: module.VehiclesPage })))
```

```tsx
function PageContent({ children }: { children: ReactNode }) {
  return <Suspense fallback={<p className="field-hint" role="status" aria-live="polite">Cargando página…</p>}>
    <PageTitle />{children}
  </Suspense>
}
```

**Resultado** (misma versión de Node, Vite y dependencias en ambos builds):

| Medida | ANTES | DESPUÉS |
|---|---:|---:|
| Chunk de entrada según Vite | 436,20 kB | 253,64 kB |
| JavaScript inicial completo (entrada y dependencias estáticas), bytes | 436 200 | 327 683 |
| gzip inicial, cálculo independiente con `node:zlib` | 129 680 | 104 588 |
| JavaScript total generado, bytes | 436 200 | 446 139 |

El JavaScript inicial baja **24,88 %** y su gzip **19,35 %**. El total generado
**aumenta** 9939 bytes por la división en módulos. Además, el precaché del
service worker descarga todos los chunks para el modo offline, por lo que el
ahorro inicial no equivale a una menor transferencia de instalación. Se verificó
la navegación por roles (55/55 rutas) y la sincronización offline en Chrome y
Firefox (10/10 ciclos cada uno).

### 3.5 Optimización 5 — Dependencias y APIs nativas (ECL-112)

**Diagnóstico.** Se inventariaron los módulos emitidos por Vite en el build
ANTES y DESPUÉS. Las seis dependencias directas tienen uso: React y React DOM
(interfaz), React Router DOM (navegación), Lucide (iconos), Leaflet (mapa, de
carga diferida) y Fontsource (fuente autoalojada).

**Decisión.** No se retiró ninguna dependencia necesaria para aparentar ahorro.
La mejora concreta fue retirar del artefacto el recurso de fuente que no se
usaba (3.3). Los módulos conservados por paquete (longitud renderizada antes de
minificar, que no equivale a bytes transferidos):

| Paquete | Módulos | Longitud renderizada |
|---|---:|---:|
| react-dom | 4 | 536 687 |
| leaflet | 2 | 242 177 |
| react-router | 1 | 92 651 |
| lucide-react | 65 | 30 241 |
| react | 4 | 17 166 |
| scheduler | 2 | 9 212 |

El JavaScript final de ambos builds suma 620 775 bytes en 27 archivos, sin
cambios por este punto. La conclusión se limita a eso: las dependencias están
justificadas y el análisis es reproducible con `frontend/scripts/analyze-static-resources.mjs`.

### 3.6 Optimización 6 — Menos peticiones y SVG inline (ECL-112)

**Diagnóstico.** Los iconos de la interfaz ya eran componentes Lucide que
renderizan SVG inline, sin peticiones de archivos SVG. Se mantiene ese patrón y
se verificó.

```tsx
// frontend/src/components/ui/Button.tsx (igual ANTES y DESPUÉS)
{Icon ? <Icon aria-hidden="true" size={18} strokeWidth={2} /> : null}
```

**Resultado.** El paquete de iconos ofrece 2118 módulos `.mjs`, pero el build
conserva 53 módulos de iconos (65 módulos Lucide con auxiliares), es decir,
`tree-shaking` efectivo. Login contiene seis SVG inline decorativos con
`aria-hidden="true"` y ninguna petición de archivo SVG. La reducción de
peticiones observada en la comparación global (88 → 8 en login y 90 → 14 en
itinerario) se debe principalmente al build de producción y al código dividido,
no solo a los SVG. El mapa usa teselas PNG de OpenStreetMap y tres imágenes
`data:` del CSS de Leaflet, recursos de una dependencia que no se convierten.

### 3.7 Optimización 7 — Caché HTTP (ECL-110 para la API y ECL-113 para los estáticos)

**API — ETag y revalidación.** `backend/app/api/conditional_get.py` agrega un
`ETag` débil (SHA-256 del JSON sin comprimir) a los `GET` elegibles y responde
`304 Not Modified` sin cuerpo si el navegador envía `If-None-Match`. Solo son
elegibles los catálogos sin datos personales (`/vehiculos`) y las respuestas que
ya declaran `Cache-Control: private`. **Nunca** se etiqueta una respuesta
`no-store`, que cubre credenciales, preferencias, listados con datos personales y
métricas. En el ANTES la API no emitía `ETag` ni respondía `304`; solo declaraba
`Cache-Control: no-store` en las rutas sensibles y `private, max-age` en los
indicadores operativos, y esas políticas se conservan.

**Estáticos — `Cache-Control` inmutable.** En el ANTES no había un servidor de
estáticos ni una política de caché propia para ellos (el contenedor ejecutaba
`npm run dev`, ver ECL-113). En producción, Nginx sirve los archivos con hash en
el nombre con caché de un año y exige revalidar lo que cambia entre versiones.

```nginx
# DESPUÉS (frontend/nginx.prod.conf, commit e58c65d)
location ~* "^/assets/.+-[A-Za-z0-9_-]{8,}\.(js|css|woff2|png|svg)$" {
    try_files $uri =404;
    add_header Cache-Control "public, max-age=31536000, immutable";
}
location ~ ^/(sw\.js|offline-shell\.json|manifest\.json|manifest\.webmanifest)$ {
    add_header Cache-Control "no-cache";
}
location / {
    try_files $uri $uri/ /index.html;
    add_header Cache-Control "no-cache";
}
```

**Verificación.** El
[diagnóstico de cabeceras](evidencias/despues/diagnostico-headers.json) confirma
`Cache-Control: public, max-age=31536000, immutable` en los activos con hash
servidos por Nginx 1.31.6. La configuración integrada de ECL-113 no arrancaba:
la expresión de `location` sin comillas producía `unknown directive "8,}\\.(js|css|woff2|png|svg)$"`;
ECL-115 la corrigió envolviéndola en comillas, sin cambiar su semántica, y `nginx -t`
pasó. Las mediciones de ECL-108 y ECL-115 vacían o deshabilitan la caché HTTP,
por lo que **no miden el beneficio de esta caché**: el ahorro en visitas
repetidas queda sin medir y no se declara cifra.

### 3.8 Optimización 8 — Compresión Gzip/Brotli (ECL-110 para la API y ECL-113 para los estáticos)

**API.** `GZipMiddleware` de Starlette comprime los cuerpos de al menos
1000 bytes cuando el cliente envía `Accept-Encoding: gzip`. Se registra por fuera
del ETag, de modo que la etiqueta describe el JSON y no su forma comprimida. Las
respuestas pequeñas, como `/health`, no se comprimen.

```python
# ANTES (e09dcd8): sin compresión ni ETag; solo CORS, métricas y cabeceras de seguridad
# DESPUÉS (ECL-110), de dentro hacia fuera:
GZIP_MINIMUM_BYTES = 1000
app.add_middleware(ConditionalGetMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=GZIP_MINIMUM_BYTES)
```

**Estáticos.** Nginx habilita `gzip on`, `gzip_comp_level 6` y `gzip_min_length 1024`
para CSS, JavaScript, JSON, manifiestos y SVG. **Brotli no se implementó**: la
configuración de ECL-113 solo habilita Gzip, y así se informa.

**Resultado y límite.** Una petición de Node con `Accept-Encoding: gzip` recibió
`Content-Encoding: gzip`. **Sin embargo, Chrome transfirió los estáticos sin
compresión observable** aunque anuncia `gzip, deflate, br, zstd`: el
[diagnóstico](evidencias/despues/diagnostico-headers.json) registra
`contentEncoding: identity` en los archivos del build. La causa de esa diferencia
queda sin determinar y no se le atribuye ninguna reducción. Las mediciones de la
API se hicieron con `Accept-Encoding: identity`, por lo que tampoco miden Gzip.
Por eso la reducción global de la sección 4 **no** incluye un efecto de compresión
y se atribuye sobre todo al build de producción.

## 4. Comparación ANTES vs. DESPUÉS

### 4.1 Condiciones y variaciones declaradas

Se conservan el equipo, Chrome, preset de Lighthouse, tres corridas por página y
20 peticiones por endpoint. **Cambia el modo de servicio**: ANTES usó Vite en
desarrollo y DESPUÉS el build de producción con Nginx (ECL-113), y por eso la
comparación **no es de condiciones idénticas**. Además:

- El producto en producción registra un service worker (`sw.js`) que Vite en
  desarrollo no registraba. La campaña **principal** mide recargas con el
  caché offline ya instalado; es otro escenario, no una primera visita.
- La campaña **suplementaria** omite el service worker (`setBypassServiceWorker(true)`)
  y es el escenario comparable con ANTES, porque ambos son una carga completa con
  caché deshabilitada. Es la que se usa para calcular reducciones.
- La base se recreó el 08/11/2026 con los mismos conteos de negocio (8, 5, 4, 20, 5
  y 3) y cambian los UUID, las fechas y el esquema (`0017_parametros_versionados`).
- El entorno API sigue en `APP_ENV=development`: «producción» identifica el build
  y servidor del frontend, no un despliegue endurecido del sistema.
- Las capturas HTML de los reportes principales se renderizaron mientras empezaba
  la campaña suplementaria: una carga concurrente leve.

### 4.2 Páginas medidas (mediana de 3 corridas)

**`/login`** (sin sesión)

| Métrica | ANTES | DESPUÉS sin service worker | Variación | DESPUÉS con service worker |
|---|---:|---:|---:|---:|
| Performance /100 | 55 | 100 | +45 | 100 |
| FCP ms | 5653,69 | 652,92 | −88,45 % | 25,84 |
| LCP ms | 10 743,54 | 652,92 | −93,92 % | 29,90 |
| TBT ms | 0 | 0 | sin cambio | 0 |
| CLS | 0,000005295 | 0,000005295 | sin cambio | 0,000005295 |
| Transferido (bytes) | 11 434 626 | 433 643 | −96,21 % | 1020 |
| Peticiones | 88 | 8 | −90,91 % | 8 |

**`/conductor/itinerario`** (conductor demo)

| Métrica | ANTES | DESPUÉS sin service worker | Variación | DESPUÉS con service worker |
|---|---:|---:|---:|---:|
| Performance /100 | 55 | 99 | +44 | 100 |
| FCP ms | 5677,36 | 722,06 | −87,28 % | 38,09 |
| LCP ms | 10 911,03 | 902,48 | −91,73 % | 194,10 |
| TBT ms | 0 | 0 | sin cambio | 0 |
| CLS | 0,019688179 | 0,019688179 | sin cambio | 0,019688179 |
| Transferido (bytes) | 11 438 644 | 459 748 | −95,98 % | 3103 |
| Peticiones | 90 | 14 | −84,44 % | 14 |

La columna «con service worker» solo describe recargas con caché offline
(visita recurrente) y **no cuenta como reducción**. El TBT parte de 0 y no tiene
porcentaje. El CLS de itinerario queda cerca del límite de 0,02 y no mejora.

**`/` y `/vehiculos` con Operador: NM antes y después.** La recarga completa
redirige a login; no hay tres corridas válidas, por lo que no se informan
porcentajes ni cumplimiento de umbrales para esas dos páginas.

### 4.3 Cumplimiento de los umbrales de la rúbrica

| Umbral | ANTES | DESPUÉS (login e itinerario, sin SW) |
|---|---|---|
| Performance ≥ 90 | No cumple (55) | Cumple (100 y 99) |
| FCP ≤ 1,0 s | No cumple (5,65 s y 5,68 s) | Cumple (0,65 s y 0,72 s) |
| LCP ≤ 1,4 s | No cumple (10,74 s y 10,91 s) | Cumple (0,65 s y 0,90 s) |
| TBT ≤ 85 ms | Cumple (0 ms) | Cumple (0 ms) |
| CLS ≤ 0,02 | Cumple | Cumple |
| Peso ≤ 1,1 MB | No cumple (11,43 MB) | Cumple (0,43 MB y 0,46 MB) |

### 4.4 API (media de 20 respuestas HTTP 200, `Accept-Encoding: identity`)

| Endpoint | Media ms ANTES → DESPUÉS | Bytes del cuerpo ANTES → DESPUÉS |
|---|---|---|
| `/vehiculos` | 7,46 → 9,90 (+32,71 %) | 1183 → 1227 (+3,72 %) |
| `/conductores?page=1` | 8,09 → 9,69 (+19,80 %) | 951 → 951 (sin cambio) |
| `/incidencias?page=1` | 8,13 → 8,25 (+1,54 %) | 1255 → 1255 (sin cambio) |

**No se observa mejora en la API.** El dataset es de pocos registros y las 20
muestras no permiten atribuir el aumento a una causa concreta; cambian el esquema,
los servicios y las condiciones del entorno. No se añadieron calentamientos para
seleccionar un resultado favorable.

### 4.5 Qué explica la reducción

La mayor parte de la mejora viene del **cambio de servidor de desarrollo a build
de producción** (código minificado, archivos compilados en lugar de módulos de
desarrollo, y 88 peticiones en login antes frente a 8 después). Las optimizaciones
individuales de este informe se verificaron una a una (secciones 3.1 a 3.8), pero
**este diseño de medición no aísla el efecto causal de cada una**: no hay una
campaña con una optimización a la vez. Se informan los efectos medidos por
separado donde existen (JavaScript inicial, fuentes) y se declara que los demás
no tienen medición aislada.

## 5. Impacto ambiental con SWDM v4 (ECL-116)

### 5.1 Modelo

`backend/scripts/swdm_v4.py` convierte los bytes transferidos en kWh y g CO₂e por
visita con la metodología Sustainable Web Design Model v4. Parámetros (fuentes
consultadas el 06/11/2026; detalle en el
[README del backend](<../../../backend/README.md#green-it-energía-y-co₂e-con-swdm-v4--ecl-116>)):

| Parámetro | Valor |
|---|---|
| Energía operacional (kWh/GB) | centro de datos 0,055; red 0,059; dispositivo 0,080 |
| Energía incorporada (kWh/GB) | centro de datos 0,012; red 0,013; dispositivo 0,081 |
| Total | 0,300 kWh/GB |
| Intensidad global | 494 g CO₂e/kWh (Ember, mundo) |
| Análisis adicional con red de Perú | 263,27 g CO₂e/kWh, solo segmentos operacionales (Ember, CO2.js 0.19.0) |
| Convención | 1 GB = 10⁹ bytes; toda visita se toma como nueva y sin hosting verde (caso conservador) |

No se usan los coeficientes de la versión 3 del ejemplo del docente. El factor
oficial del SEIN peruano no se encontró en una fuente oficial de COES ni MINEM,
por lo que el valor de Perú se presenta como análisis adicional y no reemplaza al
global. Las pruebas comparan cada resultado con CO2.js 0.19.0 de The Green Web
Foundation, con precisión de 10⁻⁹.

### 5.2 Resultados por visita y proyección anual

**Supuesto anual:** 4500 visitas al año = 15 vehículos (escenario de RNF-001) × 1
carga de itinerario por jornada × 300 jornadas. Es un supuesto de escala y no un
dato de DistriRápido; se cambia con `--visitas-anuales`.

| Página | Campaña | Bytes | kWh/visita | g CO₂e/visita | g CO₂e Perú | Calificación | kWh/año | kg CO₂e/año |
|---|---|---:|---:|---:|---:|:-:|---:|---:|
| `/login` | ANTES | 11 434 626 | 0,003430 | 1,6946 | 1,1828 | F | 15,437 | 7,626 |
| `/login` | DESPUÉS (sin SW) | 433 643 | 0,000130 | 0,0643 | 0,0449 | A | 0,585 | 0,289 |
| `/conductor/itinerario` | ANTES | 11 438 644 | 0,003432 | 1,6952 | 1,1832 | F | 15,442 | 7,628 |
| `/conductor/itinerario` | DESPUÉS (sin SW) | 459 748 | 0,000138 | 0,0681 | 0,0476 | A | 0,621 | 0,307 |

La reducción de bytes, de energía y de CO₂e es de **96,2 %** en login y **96,0 %**
en itinerario. La proyección conservadora para el itinerario pasa de 7,628 a
0,307 kg CO₂e al año. La meta de 1,1 MB de la rúbrica equivale a 0,163 g CO₂e por
visita (calificación C); ambas páginas quedan por debajo.

### 5.3 Límites

- Son **estimaciones del modelo** a partir de bytes transferidos, no consumo
  eléctrico medido; no se midió potencia ni se verificó por software el modo de
  alimentación del equipo.
- La recarga con service worker (1020 y 3103 bytes, unos 0,0002 y 0,0005 g por
  visita) es una visita recurrente: dar un 100 % de reducción con ella sería
  engañoso y no se usa.
- Las cifras no incluyen la instalación inicial del shell offline ni la frecuencia
  con que ocurre; modelarla exige medir ese escenario y declarar su frecuencia.
- La mayor parte de la reducción viene del cambio de modo de servicio (4.5).
- `/` y `/vehiculos` siguen NM y no se cuentan como cero.

Reproducción desde `backend/`:

```powershell
python scripts/swdm_v4.py                # ANTES de ECL-108
python scripts/swdm_v4.py --despues      # ECL-115 sin service worker
python -m pytest tests/unit/test_swdm_v4.py -q
```

## 6. Evidencias Lighthouse y auditoría en CI

**Evidencias originales** (JSON de Lighthouse y Network, capturas del reporte,
de Network y de la página por corrida, y las 20 muestras CSV por endpoint):

- ANTES, ECL-108: [carpeta `evidencias/antes`](<evidencias/antes/README.md>) y
  [campaña válida](<evidencias/antes/run-2026-11-06T23-50-12-524Z/README.md>).
- DESPUÉS, ECL-115: [carpeta `evidencias/despues`](<evidencias/despues/README.md>),
  [campaña principal](<evidencias/despues/run-2026-11-08T06-50-38-119Z/resultados.json>),
  [campaña sin service worker](<evidencias/despues/run-2026-11-08T06-52-40-316Z/resultados.json>)
  y [comparación completa](<evidencias/despues/comparacion.md>).
- Evidencias por optimización: [ECL-111](<ECL-111 React lazy y paginacion V_1_0_0.md>),
  [ECL-112](<ECL-112 recursos estaticos V_1_0_0.md>) y la
  [configuración de ECL-113](<../Sprint 04/ECL-113 build produccion.md>).

**Auditoría continua (criterio 3 de la rúbrica).** El workflow
`.github/workflows/green-audit.yml` ejecuta Lighthouse CI sobre `/login` en cada
`push` y `pull_request`, con tres corridas, el preset Desktop y aserciones por
mediana sobre Performance, FCP, LCP, TBT, CLS y peso total. Conserva los reportes
como artefacto durante 30 días, sin secretos. No existía en el ANTES. Una
validación local del workflow dio Performance 1,00, FCP 632 ms, LCP 672 ms,
TBT 0 ms y 425 312 bytes de transferencia; es una comprobación de la
herramienta sobre un build estático y no sustituye la campaña de ECL-115. El check
queda opcional. Detalle: [ECL-114](<ECL-114 auditoria Green IT en CI.md>).

## 7. Gestión de versiones y secuencia Git

### 7.1 Secuencia Git usada

`main` está protegida: nada se publica directo. Cada entrega sigue esta secuencia
sobre una rama y un pull request; este informe se publicó así:

```powershell
git checkout main
git pull --ff-only
git checkout -b docs/ECL-117-informe-impacto-ambiental
mkdir -Force 'docs/03 Implementación/reduccion del impacto ambiental'
# redactar el informe con el nombre exacto de la rúbrica
python scripts/check_docs.py
git add 'docs/03 Implementación/reduccion del impacto ambiental/01 Informe de reduccion del impacto ambiental V_1_0_0.md' README.md
git commit -m "docs(ECL-117): informe 01 de reducción del impacto ambiental"
git push -u origin docs/ECL-117-informe-impacto-ambiental
# abrir el pull request en GitHub; el autor mergea tras la aprobación del dueño de docs/
```

### 7.2 Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 10/11/2026 | Primera versión completa: ocho optimizaciones con código ANTES y DESPUÉS, comparación ECL-108 y ECL-115, impacto SWDM v4 y evidencias. Pendiente de revisión humana. |

## 8. Límites generales del informe

1. La comparación mezcla el cambio de servidor de desarrollo a producción con las
   ocho optimizaciones; no hay campaña que aísle cada una.
2. `/` y `/vehiculos` con Operador no son medibles por la pérdida de identidad al
   recargar; no se fabricó una identidad ni se cambió la autenticación para
   medirlas.
3. Brotli no se implementó y Chrome no mostró compresión en los estáticos; la
   causa no está determinada.
4. La caché inmutable y el ETag no se midieron en visitas repetidas.
5. No se agregaron índices de PostgreSQL ni se midió su efecto.
6. La API no muestra mejora de tiempo ni de bytes con el dataset de la demo.
7. Las cifras de energía y CO₂e son estimaciones del modelo SWDM v4, no medición
   eléctrica, y la proyección anual depende de un supuesto de 4500 visitas.

[Índice del Sprint 4](<../Sprint 04/README.md>) · [Informe 02](<02 Estandares Ingeniería de software V_1_0_0.md>) · [← Volver al README principal](../../../README.md)
