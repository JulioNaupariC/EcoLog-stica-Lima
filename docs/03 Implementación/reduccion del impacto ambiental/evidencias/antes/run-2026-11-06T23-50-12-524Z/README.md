# ECL-108 — Resultados reales de la línea base ANTES

La campaña obtuvo **3 corridas válidas de `/login`, 3 del itinerario del conductor
y 60 respuestas API HTTP 200**. Las vistas `/` y `/vehiculos` con Operador son
**no medibles en modo navegación con recarga completa**: el código base pierde
la identidad de ese rol al recargar y redirige a `/login`. Se conserva evidencia
del comportamiento; no se presentan resultados de login como si fueran de esas vistas.

## Entorno y trazabilidad

| Campo | Valor |
|---|---|
| Ticket | [ECL-108](https://continental-team-il84x39k.atlassian.net/browse/ECL-108) |
| Commit ANTES de `main` | `e09dcd80e32431018d4020bb02c89ffae7505705` |
| Head documental al medir | `5f381f3726c184ee951a86eee205d494b08b1377` |
| Comprobación de código | `git diff` entre ANTES y el árbol medido, limitado a `backend/`, `frontend/` y `compose.yaml`, vacío; el recolector lo exige antes de ejecutar |
| Fecha, zona | 06/11/2026, America/Lima (UTC−05:00) |
| Campaña principal | 18:50:12–18:52:27 Lima; 23:50:12–23:52:27 UTC |
| Comprobación final de Operador | Directorio `run-2026-11-06T23-56-10-225Z`; hora UTC en sus JSON |
| Equipo | Intel Core i9-14900HX; RAM física visible 15,73 GiB |
| Windows | Microsoft Windows 11 Home Single Language, 10.0.26300 |
| Chrome real | 156.0.8078.80; ventana visible, contextos de incógnito y extensiones deshabilitadas |
| Lighthouse | 12.8.2, API Node, modo Navigation, categoría Performance, preset Desktop |
| Viewport Lighthouse | 1350 × 940, DPR 1, sin emulación móvil |
| Throttling Lighthouse | `simulate`: RTT 40 ms, 10240 Kbps, CPU ×1, valores del preset Desktop |
| User agent emulado por el preset | Chrome/136 en macOS; no es la versión ni el sistema del equipo real, registrados arriba |
| Almacenamiento | `disableStorageReset: true`; caché HTTP vaciada y deshabilitada en cada corrida; sesiones separadas por página/rol |
| Network | Panel real de DevTools, sin throttling, `Disable cache` activado, `Keep log` desactivado; recarga completa y observación hasta `networkidle0` + 1 s |
| Aplicación | `compose.yaml` sin cambios, frontend Vite en desarrollo, API en puerto 8000 y frontend en 5173, origen `127.0.0.1` |
| Aislamiento | Proyecto `ecologistica-lima-ecl108`, base nueva `ecologistica_ecl108_demo`, volumen propio; no se reutilizaron recursos del clon anterior |
| Docker y migración | Docker Engine 29.9.2; PostgreSQL 16/PostGIS comprobado; `alembic current` y `heads`: `0013_incidencias (head)` |
| Dataset | Script existente `backend/scripts/seed_demo.py`, cargado el 06/11/2026: 8 clientes, 5 vehículos, 4 conductores, 20 pedidos, 5 asignaciones y 3 incidencias ficticias |

El `.env` privado y las contraseñas aleatorias locales están ignorados por Git.
No se exportaron cookies, contraseñas, cuerpos de respuesta de negocio ni HAR.
Vite ya había atendido las comprobaciones y accesos previos: se mide caché fría
del navegador, con el servidor de desarrollo ya iniciado; no su primer arranque.
No se verificó telemetría de procesos, alimentación o carga térmica del equipo.
Son límites de reproducibilidad que se deben controlar y registrar en ECL-115.

## Medianas por página

Mediana independiente de cada columna sobre tres corridas. Los tiempos se
redondean aquí a 2 decimales; los originales conservan su precisión.
**NM = no medible con el protocolo solicitado**, no cero ni estimación.

| Página | Rol | Corridas válidas | Performance /100 | FCP ms | LCP ms | TBT ms | CLS | Transferido bytes | Peticiones |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `/login` | Sin sesión | 3/3 | 55 | 5653,69 | 10743,54 | 0 | 0,000005295 | 11434626 | 88 |
| `/` | Operador | 0/3 | NM | NM | NM | NM | NM | NM | NM |
| `/vehiculos` | Operador | 0/3 | NM | NM | NM | NM | NM | NM | NM |
| `/conductor/itinerario` | Conductor demo | 3/3 | 55 | 5677,36 | 10911,03 | 0 | 0,019688179 | 11438644 | 90 |

Los bytes y peticiones proceden de una recarga Network separada, sin throttling,
por cada corrida Lighthouse. Son el total del modelo de peticiones de DevTools,
incluyendo cabeceras transferidas donde Chrome las contabiliza; no el tamaño
descomprimido de los recursos ni el peso estimado por Lighthouse.
Cada JSON Network conserva el intervalo observado en `observedMs`.

La línea base **no alcanza** Performance ≥90, FCP ≤1000 ms, LCP ≤1400 ms ni
peso ≤1,1 MB en las dos páginas medibles. Sus medianas sí quedan dentro de
TBT ≤85 ms y CLS ≤0,02. Esto describe ANTES; no demuestra una optimización.
Los reportes y Network muestran que Vite sirve módulos de desarrollo y rutas
importadas anticipadamente. No se extrapolan estos resultados a producción.

## Evidencia Lighthouse y Network válida

Cada captura Lighthouse renderiza su JSON original; no representa otra corrida.
Las capturas `-pagina.png` muestran la aplicación y las `-network.png` el panel
real de Chrome, sin escritorio ni pestañas personales.

| Página y corrida | JSON original | Reporte | Network |
|---|---|---|---|
| Login 1 | [JSON](login-01.lighthouse.json) | [Captura](login-01-lighthouse-reporte.png) | [Registro](login-01.network.json) · [Captura](login-01-network.png) |
| Login 2 | [JSON](login-02.lighthouse.json) | [Captura](login-02-lighthouse-reporte.png) | [Registro](login-02.network.json) · [Captura](login-02-network.png) |
| Login 3 | [JSON](login-03.lighthouse.json) | [Captura](login-03-lighthouse-reporte.png) | [Registro](login-03.network.json) · [Captura](login-03-network.png) |
| Conductor 1 | [JSON](itinerario-conductor-01.lighthouse.json) | [Captura](itinerario-conductor-01-lighthouse-reporte.png) | [Registro](itinerario-conductor-01.network.json) · [Captura](itinerario-conductor-01-network.png) |
| Conductor 2 | [JSON](itinerario-conductor-02.lighthouse.json) | [Captura](itinerario-conductor-02-lighthouse-reporte.png) | [Registro](itinerario-conductor-02.network.json) · [Captura](itinerario-conductor-02-network.png) |
| Conductor 3 | [JSON](itinerario-conductor-03.lighthouse.json) | [Captura](itinerario-conductor-03-lighthouse-reporte.png) | [Registro](itinerario-conductor-03.network.json) · [Captura](itinerario-conductor-03-network.png) |

[Datos completos de la campaña](resultados.json) ·
[Resultados login](login.resultado.json) ·
[Resultados conductor](itinerario-conductor.resultado.json) ·
[Vista del itinerario](itinerario-conductor-01-pagina.png).

## Páginas no medibles: evidencia y causa

La comprobación final espera que Inicio termine de renderizar, entra a la vista
mediante navegación normal, captura el rol Operador y hace una recarga completa.
Ambas páginas terminan en `/login`. No se modificó ni inyectó identidad para
forzar una medición. Los 88 requests y 11,43 MB de esas recargas corresponden
a **login**, por eso no aparecen como peso de Operador en la tabla anterior.

| Vista solicitada | Antes de recargar | Después | Diagnóstico |
|---|---|---|---|
| `/` | [Operador autenticado](../run-2026-11-06T23-56-10-225Z/inicio-operador-antes-recarga.png) | [Login](../run-2026-11-06T23-56-10-225Z/inicio-operador-01-pagina.png) | [Resultado](../run-2026-11-06T23-56-10-225Z/inicio-operador.resultado.json) |
| `/vehiculos` | [Vehículos con Operador](../run-2026-11-06T23-56-10-225Z/vehiculos-operador-antes-recarga.png) | [Login](../run-2026-11-06T23-56-10-225Z/vehiculos-operador-01-pagina.png) | [Resultado](../run-2026-11-06T23-56-10-225Z/vehiculos-operador.resultado.json) |

La causa es verificable en el commit fijo: `App.tsx` restaura `identity` con
`recallDriver`; `offlineAccess.ts` solo guarda y recupera CONDUCTOR. La cookie
HttpOnly no basta para reconstruir la identidad de Operador tras una carga de
documento. Resolverlo requiere un cambio de aplicación fuera de ECL-108.
No hay JSON Lighthouse válido de Operador ni se atribuyen métricas a esas vistas.

## API: medias sobre 20 respuestas por endpoint

Sesión real de Operador. Peticiones secuenciales a la API local, sin
calentamientos adicionales de API dentro de la campaña, con `Accept-Encoding:
identity`. Duración con `performance.now()` desde antes del envío hasta leer el
cuerpo completo; excluye login. Bytes del cuerpo recibido sin cabeceras, con
codificación `identity`, por lo que coinciden con los bytes sin comprimir.
Son un límite distinto del total transferido del navegador.

| GET | Respuestas 200 | Media ms | Media bytes | Mín.–máx. bytes | Muestras |
|---|---:|---:|---:|---|---|
| `/vehiculos` | 20/20 | 7,46 | 1183 | 1183–1183 | [CSV](api-vehiculos.csv) |
| `/conductores?page=1` | 20/20 | 8,09 | 951 | 951–951 | [CSV](api-conductores.csv) |
| `/incidencias?page=1` | 20/20 | 8,13 | 1255 | 1255–1255 | [CSV](api-incidencias.csv) |

## Reproducción y verificación

El [protocolo inicial](../README.md#protocolo-repetible-para-ecl-108-y-ecl-115)
se complementa con la configuración efectiva de este registro. En ECL-115
mantener equipo, dataset, Vite, configuración Lighthouse/Network, páginas y roles.
Documentar cualquier variación. Comparar solo páginas y condiciones equivalentes;
no calcular mejoras de las dos filas NM sin una medición ANTES válida.

Para recalcular y verificar los resultados conservados, sin levantar la app:

```powershell
python 'docs/03 Implementación/reduccion del impacto ambiental/evidencias/antes/run-2026-11-06T23-50-12-524Z/calcular.py'
python scripts/check_docs.py
```

[`calcular.py`](calcular.py) lee directamente los seis JSON Lighthouse y Network,
recalcula las medianas y verifica las 60 filas CSV HTTP 200. La reejecución local
dio `OK: 6 Lighthouse reports, 6 Network records and 60 HTTP 200 samples verified.`

El [recolector corregido](../run-2026-11-06T23-56-10-225Z/medir.mjs) se ejecuta
desde la raíz con Node 22.18.0. Necesita Lighthouse 12.8.2 y Puppeteer Core 24.43.1
en `.tmp-ecl108/node_modules`, Chrome en la ruta indicada en el script y el entorno
Compose iniciado. Lee las contraseñas demo de `.env` sin mostrarlas, hace login
real y mantiene la cookie solo en memoria. Cada ejecución crea una carpeta nueva;
no ejecutar sobre evidencias históricas ni versionar `.env` o los módulos temporales.

```powershell
npm.cmd install --prefix .tmp-ecl108 --no-save --package-lock=false lighthouse@12.8.2 puppeteer-core@24.43.1
# Quitar filtros de una comprobación parcial antes de repetir la campaña completa.
Remove-Item Env:ECL108_PAGES, Env:ECL108_SKIP_API -ErrorAction SilentlyContinue
node 'docs/03 Implementación/reduccion del impacto ambiental/evidencias/antes/run-2026-11-06T23-56-10-225Z/medir.mjs'
```

La campaña de esta carpeta usó la [versión inicial del recolector](medir.mjs).
Su fallo de navegación automatizada de vehículos se resolvió en la comprobación
final; las métricas válidas de login, conductor y API no se repitieron ni mezclaron.
La comprobación final se invocó con `ECL108_PAGES=inicio-operador,vehiculos-operador`
y `ECL108_SKIP_API=1`. [Capturar reportes](capturar-reportes.mjs) transforma JSON
Lighthouse en capturas y rechaza sobrescribir una captura existente.

## Intentos conservados y revisión pendiente

Todos los intentos son del mismo commit y dataset. Solo los seis reportes y
tres CSV enlazados en las tablas alimentan los resultados de esta entrega.

| Carpeta (hora UTC) | Resultado; uso |
|---|---|
| [23:46:38](../run-2026-11-06T23-46-38-851Z/resultados.json) | Chrome se cerró al cerrar su última pestaña; login y API diagnósticos, excluidos de las tablas |
| [23:47:43](../run-2026-11-06T23-47-43-784Z/resultados.json) | Selector de email incorrecto en la herramienta; timeouts de acceso, excluidos |
| [23:50:12](resultados.json) | Campaña principal: seis Lighthouse válidos y 60 API válidas; vehículos tuvo un timeout de navegación de la herramienta |
| [23:52:50](../run-2026-11-06T23-52-50-871Z/resultados.json) | Enlace de vehículos buscado antes de completar el renderizado de Inicio; intento excluido |
| [23:53:29](../run-2026-11-06T23-53-29-416Z/resultados.json) | Vehículos accedido correctamente y redirección real tras recarga; corroborado después |
| [23:56:10](../run-2026-11-06T23-56-10-225Z/resultados.json) | Comprobación final de las dos vistas de Operador, ambas NM; evidencia usada en la entrega |

El PR permanece en borrador para auditoría técnica independiente y posterior
revisión humana de @JulioNaupariC según la política del repositorio. El revisor
debe valorar las dos vistas no medibles expresamente documentadas; no se declara
el ticket Done ni se integra sin aprobación. La revisión de alertas de CodeQL
es independiente del resultado del workflow.

El índice `Sprint 04/README.md` y su marcador ECL-108 todavía no existen en el
commit base. El enlace desde ese índice queda pendiente de ECL-99; el README
principal ya enlaza este registro. No se creó planificación fuera del ticket.
No se calcularon kWh ni CO₂e: esta tarea captura la línea base, sin cifras estimadas.

[← Volver al README principal](../../../../../../README.md)
