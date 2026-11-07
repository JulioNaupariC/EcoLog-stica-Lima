# ECL-112 Recursos estáticos del frontend

## Propósito y trazabilidad

Optimizaciones 3, 5 y 6 de Green IT: reducir los recursos que se distribuyen,
analizar dependencias y verificar los SVG inline sin alterar el diseño aprobado.
Se conserva Inter, su rango de pesos y `font-display: swap`. No se introduce
una pila tipográfica distinta ni se fabrican imágenes para convertirlas.

| Referencia | Estado usado |
|---|---|
| Línea base ECL-108 | `e09dcd80e32431018d4020bb02c89ffae7505705` |
| Main antes de ECL-112 | `1b8a5501d27bf42c3bd04718add156eb5ba89f67`, incluye ECL-87 |
| Rama | `feat/ECL-112-recursos-estaticos` |
| Revisión | José para frontend y un dueño de documentación según CODEOWNERS |
| Medición global posterior | ECL-115; este informe no sustituye esa campaña |

El [registro real de ECL-108](<evidencias/antes/run-2026-11-06T23-50-12-524Z/README.md>)
contiene seis corridas Lighthouse válidas de login/conductor. Inicio y vehículos
de Operador son NM tras recargar, por la identidad conservada solo en memoria.
No se presentan las redirecciones a login como mediciones de esas vistas.

Los fragmentos ANTES se conservaron antes de modificar estilos:
[CSS ECL-108](evidencias/ECL-112/ecl108-base.css.txt),
[CSS main inmediato](evidencias/ECL-112/main-antes-base.css.txt),
[package ECL-108](evidencias/ECL-112/ecl108-package.json) y
[package main inmediato](evidencias/ECL-112/main-antes-package.json).
Los JSON de medición registran commit, cambios locales y SHA-256 del CSS.
No se modificó ninguna evidencia histórica de otros tickets.

## Inventario y área 3

| Recurso | Inventario y decisión |
|---|---|
| `frontend/public/sw.js` | 2 793 bytes; único archivo propio de `public/`. Se conserva sin cambios. |
| Favicon e iconos PWA propios | No existen archivos ni referencias en `index.html`; no se añaden recursos ficticios. |
| Manifest PWA | No hay `manifest.webmanifest`. `offline-shell.json` es un inventario de precarga generado por el build, no un manifest de instalación. |
| Raster propios en `src/` y `public/` | Ninguno: no hay PNG/JPEG/WebP/AVIF propios que convertir ni necesidad de `<picture>`. |
| Inter Latin WOFF2 | 48 256 bytes; se conserva con `swap`, pesos 100–900 y su `unicode-range` original. |
| Inter Latin Extended WOFF2 | 85 068 bytes; se elimina su referencia CSS y deja de emitirse y precargarse. |
| Iconos de la UI | Componentes Lucide, SVG inline; no se añaden peticiones de archivos SVG. |
| Mapa incorporado en ECL-14 | Usa teselas PNG externas de OpenStreetMap y tres `data:image/png` del CSS de Leaflet. Son recursos de una dependencia/integración, no imágenes propias. No se convierten ni se declara que toda la app carezca de raster. |

El subconjunto latino cubre los caracteres españoles comprobados. Los caracteres
fuera de su rango usan los fallbacks existentes de `--font-sans`; no se promete
Inter para otros alfabetos. No se modifican tokens de color, tamaño, espaciado,
foco ni estructura accesible.

## Fragmentos ANTES y DESPUÉS

Ruta en ambos commits ANTES: `frontend/src/styles/base.css`. Ya existía
`font-display: swap`: se conserva, no se atribuye como una optimización nueva.
Además de la regla latina, ANTES se declaraba este segundo archivo:

```css
@font-face {
  font-family: "Inter Variable";
  font-style: normal;
  font-display: swap;
  font-weight: 100 900;
  src: url("@fontsource-variable/inter/files/inter-latin-ext-wght-normal.woff2") format("woff2-variations");
  unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329,
    U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF;
}
```

DESPUÉS se elimina esa regla y se conserva únicamente esta:

```css
@font-face {
  font-family: "Inter Variable";
  font-style: normal;
  font-display: swap;
  font-weight: 100 900;
  src: url("@fontsource-variable/inter/files/inter-latin-wght-normal.woff2") format("woff2-variations");
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308,
    U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
}
```

La regla de `frontend/scripts/build-offline.mjs` que precarga los WOFF2 no
cambia: al emitirse un único archivo, el inventario offline se reduce solo.
En `.dockerignore` se añade `.tmp-*/` para excluir las herramientas y resultados
temporales de auditoría de la imagen local; no se modifica Compose ni el
servidor de estáticos de ECL-113.

## Dependencias y área 5

El [análisis ANTES](evidencias/ECL-112/bundle-antes.json) y el
[análisis DESPUÉS](evidencias/ECL-112/bundle-despues.json) se obtienen con Vite
real y su inventario de módulos emitidos. Incluyen tamaños, SHA-256, gzip
calculado por `node:zlib`, archivos estáticos y módulos por chunk. No se instala
un visualizador en la app ni se altera el lockfile.

Las seis dependencias directas tienen uso: React/React DOM para la UI,
React Router DOM para navegación, Lucide para iconos, Leaflet para el mapa
diferido y Fontsource para el WOFF2 autoalojado. No se retira una dependencia
necesaria para aparentar ahorro. React Router DOM puede quedar como fachada
sin módulo emitido propio, delegando a `react-router`; eso no significa desuso.
La mejora concreta es retirar el recurso latino extendido del artefacto y la
precarga, conservando el paquete de la fuente que sí se utiliza.

| Paquete emitido | Módulos conservados | Longitud renderizada |
|---|---:|---:|
| react-dom | 4 | 536 687 |
| leaflet | 2 | 242 177 |
| react-router | 1 | 92 651 |
| lucide-react | 65 | 30 241 |
| react | 4 | 17 166 |
| scheduler | 2 | 9 212 |

Estas longitudes son la medida de módulos de Vite/Rolldown antes de la
minificación final; no equivalen a bytes transferidos ni deben sumarse como
peso HTTP. El JavaScript final de ambos builds suma 620 775 bytes en 27 archivos.

## SVG inline y área 6

El módulo de iconos contiene 2 118 archivos `.mjs` disponibles, pero el resultado
conserva 53 módulos de iconos, dentro de 65 módulos Lucide incluyendo auxiliares.
El informe enumera los módulos efectivos y su chunk: evidencia de tree-shaking,
sin afirmar que todo el catálogo llegue al navegador.

Los componentes ya renderizaban SVG inline ANTES; se mantiene ese patrón.
Por ejemplo, en `frontend/src/components/ui/Button.tsx`:

```tsx
{Icon ? <Icon aria-hidden="true" size={18} strokeWidth={2} /> : null}
```

En login hay seis SVG inline decorativos con `aria-hidden="true"`, cero
`img/picture` y ninguna petición de archivo SVG en las corridas conservadas.
La referencia URL de la fuente no se confunde con los SVG de componentes.
No había un icono propio servido aparte en la ruta crítica que integrar.

## Resultados locales del 7 de noviembre de 2026

Equipo: Intel Core i7-10700F, 15,90 GiB de RAM, Windows 11 Pro 10.0.26200,
Chrome 157.0.8103.38, Node 22.20.0, Lighthouse 12.8.2 y Puppeteer Core 24.43.1.
Es distinto del equipo/Chrome de ECL-108: no se calculan porcentajes de mejora
contra aquella campaña ni se atribuyen a ECL-112 los cambios de otros tickets.

### Archivos distribuidos y precarga de producción

| Medida | ANTES inmediato | DESPUÉS | Diferencia |
|---|---:|---:|---:|
| WOFF2 emitidos/precargados | 2 | 1 | −1 |
| Bytes de fuentes | 133 324 | 48 256 | −85 068; −63,8 % |
| JavaScript emitido | 620 775 | 620 775 | 0 |
| Archivos declarados en precarga | 32 | 31 | −1 solicitud declarada |
| Bytes de cuerpos declarados en precarga | 817 671 | 732 243 | −85 428, incluyendo la reducción de CSS |

La precarga se comprobó en Chrome real con builds de producción aislados:
[resultado offline y visual](evidencias/ECL-112/offline-y-visual.json).
Cache Storage contiene dos fuentes ANTES y una DESPUÉS. El shell público
recarga sin red y la fuente española sigue disponible. Los bytes anteriores
son tamaños de archivos/cuerpos, sin cabeceras: no son el total de Network ni
una campaña autenticada del conductor. No se ejecutó aquí el E2E de incidencias.

Las capturas de login de esos dos builds tienen exactamente el mismo SHA-256.
El protocolo CSS de Chrome identifica Inter personalizado para los 16 glifos
de `áéíóúÁÉÍÓÚüÜñÑ¿¡`, tanto ANTES como DESPUÉS.

### Login con el protocolo de Lighthouse y Network de ECL-108

Chrome visible en contexto de incógnito, sin extensiones; viewport 1350 × 940,
DPR 1. Vite de desarrollo servido por Docker en 5173, con una navegación previa
de calentamiento del servidor. Tres recargas con caché HTTP vaciada/deshabilitada,
Network sin throttling observado hasta `networkidle0` + 1 s y tres Lighthouse
Navigation, Performance, Desktop, `disableStorageReset: true`. Lighthouse usa
simulación Desktop: RTT 40 ms, 10 240 Kbps y CPU ×1. Accesibilidad se audita
aparte para conservar las corridas Performance del protocolo.

| Mediana independiente | ANTES inmediato | DESPUÉS |
|---|---:|---:|
| Performance /100 | 55 | 55 |
| FCP ms | 5 007,27 | 4 981,55 |
| LCP ms | 9 504,91 | 9 455,32 |
| TBT ms | 0 | 0 |
| CLS | 0,000005302 | 0,000005302 |
| Network total transferido, bytes | 10 760 850 | 10 760 429 |
| Peticiones totales | 58 | 58 |
| Accesibilidad Lighthouse /100 | 100 | 100 |

La fuente latina extendida no se solicita en login: no se atribuye una petición
menos a esa navegación. Los 421 bytes de reducción observados corresponden al
CSS servido por Vite; la mejora principal está en la distribución/precarga.
Las pequeñas diferencias temporales no prueban un efecto causal de la fuente.
Vite de desarrollo sigue sin alcanzar Performance, FCP, LCP y peso de la rúbrica.
No se reemplazan estos valores por los resultados de producción del CI.

Fuentes de las medianas y configuración:
[ANTES](evidencias/ECL-112/antes-local-2026-11-07/resultados.json) y
[DESPUÉS](evidencias/ECL-112/despues-local-2026-11-07/resultados.json).

| Fase | Lighthouse originales | Network originales | Capturas representativas |
|---|---|---|---|
| ANTES | [1](evidencias/ECL-112/antes-local-2026-11-07/login-01.lighthouse.json), [2](evidencias/ECL-112/antes-local-2026-11-07/login-02.lighthouse.json), [3](evidencias/ECL-112/antes-local-2026-11-07/login-03.lighthouse.json) | [1](evidencias/ECL-112/antes-local-2026-11-07/login-01.network.json), [2](evidencias/ECL-112/antes-local-2026-11-07/login-02.network.json), [3](evidencias/ECL-112/antes-local-2026-11-07/login-03.network.json) | [Página](evidencias/ECL-112/antes-local-2026-11-07/login-01-pagina.png), [Network](evidencias/ECL-112/antes-local-2026-11-07/login-01-network.png) |
| DESPUÉS | [1](evidencias/ECL-112/despues-local-2026-11-07/login-01.lighthouse.json), [2](evidencias/ECL-112/despues-local-2026-11-07/login-02.lighthouse.json), [3](evidencias/ECL-112/despues-local-2026-11-07/login-03.lighthouse.json) | [1](evidencias/ECL-112/despues-local-2026-11-07/login-01.network.json), [2](evidencias/ECL-112/despues-local-2026-11-07/login-02.network.json), [3](evidencias/ECL-112/despues-local-2026-11-07/login-03.network.json) | [Página](evidencias/ECL-112/despues-local-2026-11-07/login-01-pagina.png), [Network](evidencias/ECL-112/despues-local-2026-11-07/login-01-network.png) |

La campaña local se limita a login público y los recursos estáticos. No accede
a contraseñas, no exporta HAR/cookies y no modifica autenticación para medir
las páginas protegidas. La campaña global con los roles, dataset y condiciones
de ECL-108 corresponde a ECL-115. Tampoco se calcula energía/CO₂e: es ECL-116.

## Accesibilidad y validación

- Type-check, lint y build de producción se comprobaron localmente.
- `scripts/check-contrast.mjs` mantiene los mínimos AA en ambos temas.
- Giancarlo informó: «Se ve igual y teclado/Narrador correctos», tras recargar
  el login local. Es un resultado manual comunicado, sin grabación adjunta.
- La verificación de producción comprueba igualdad visual, glifos españoles y
  shell público offline; no atribuye resultados de lector a Lighthouse.
- La primera suite tuvo 862 aprobadas y un timeout de 5 s en la prueba existente
  del título de la pestaña. Esa prueba pasó aislada sin cambios y la suite
  completa pasó con dos trabajadores: 57 archivos y 863 pruebas aprobadas en
  110,82 s, sin aumentar los límites ni cambiar las pruebas.
- Auditoría independiente, aprobación humana y checks del PR deben comprobarse
  antes de integrar. Este documento no acredita esos eventos futuros.

## Reproducción

Herramientas:
[inventario del bundle](../../../frontend/scripts/analyze-static-resources.mjs),
[medición local](../../../frontend/scripts/measure-static-resources.mjs) y
[verificación offline/visual](../../../frontend/scripts/verify-static-resources.mjs).
Los informes se escriben con exclusión de archivos existentes; usar nombres
nuevos en cada ejecución. Desde `frontend/`:

```powershell
npm ci
npm run typecheck
npm run lint
npm run test -- --maxWorkers=2
npm run build
node scripts/check-contrast.mjs

$stamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH-mm-ss-fffZ')
node scripts/analyze-static-resources.mjs "../docs/03 Implementación/reduccion del impacto ambiental/evidencias/ECL-112/bundle-$stamp.json"

# Herramientas fijadas y temporales: no se modifica package.json/package-lock.json.
npm install --prefix .tmp-ecl112 --no-save --package-lock=false --no-audit --no-fund lighthouse@12.8.2 puppeteer-core@24.43.1

# Antes, reconstruir/levantar el frontend Docker del código que se va a medir.
node scripts/measure-static-resources.mjs "../docs/03 Implementación/reduccion del impacto ambiental/evidencias/ECL-112/login-$stamp"
```

Para reconstruir ANTES, usar un checkout/worktree independiente del commit
`1b8a5501d27bf42c3bd04718add156eb5ba89f67`, conservar su `dist/` tras `npm ci`
y `npm run build`, y comparar con el `dist/` de esta rama. La herramienta nueva
de análisis puede copiarse al checkout ANTES sin cambiar `src/`, los paquetes
ni la configuración de Vite. No cambiar el clon de trabajo con cambios pendientes.

En esta ejecución se conservaron los builds locales en `.tmp-ecl112/`:

```powershell
node scripts/verify-static-resources.mjs .tmp-ecl112/dist-antes .tmp-ecl112/dist-despues "../docs/03 Implementación/reduccion del impacto ambiental/evidencias/ECL-112/offline-$stamp.json"
```

Esos builds temporales no están versionados; en otro equipo deben generarse a
partir de los commits indicados y pasarse sus directorios a la herramienta.
Los conceptos de los informes siguen el
[glosario del Sprint 4](<../Sprint 04/CONVENCIONES_Y_GLOSARIO_ECL99.md>).

[Índice del Sprint 4](<../Sprint 04/README.md>)

[Volver al README principal](../../../README.md)
