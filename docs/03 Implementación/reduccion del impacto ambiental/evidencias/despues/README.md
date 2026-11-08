# ECL-115 — Medición DESPUÉS de Green IT

Se obtuvieron **6 JSON Lighthouse válidos en la campaña principal, 6 en una
campaña suplementaria y 60 respuestas API HTTP 200**. Login e itinerario cumplen
los umbrales de la rúbrica en los dos escenarios medidos. Inicio y Vehículos
con Operador siguen redirigiendo a login al recargar: **NM**, sin porcentajes
de mejora ni acreditación de rendimiento para esas dos páginas.

La [tabla ANTES vs. DESPUÉS](comparacion.md) contiene valores, variaciones
absolutas y porcentuales por métrica; [comparacion.json](comparacion.json)
conserva los datos para ECL-116 y ECL-117. Los porcentajes describen campañas
con cambios declarados de modo de servicio y caché; no aíslan causalmente
el efecto de cada optimización ni acreditan ahorros de energía.

## Trazabilidad y condiciones

| Campo | Valor |
|---|---|
| Ticket | [ECL-115](https://continental-team-il84x39k.atlassian.net/browse/ECL-115) |
| ANTES | `e09dcd80e32431018d4020bb02c89ffae7505705`; [registro ECL-108](../antes/run-2026-11-06T23-50-12-524Z/README.md) |
| DESPUÉS medido | `e58c65d35002b3b5bed270f7f40ae687096367b0`, sin cambios pendientes de aplicación |
| ECL-113 integrado | PR #99, merge `9348593`; configuración de producción más la corrección autorizada de Nginx |
| Rama | `docs/ECL-115-medicion-despues`, desde `main` actualizado `69bd05b` |
| Responsable | José Delgadillo; identidad Git cotejada con la cuenta conectada `JoseDelgadillo277` |
| Revisores | @JulioNaupariC (documentación), @GiancarloSE (frontend) |
| Fecha de medición | 08/11/2026, America/Lima (UTC−05:00) |
| Principal | 01:50:38–01:51:53 Lima; `run-2026-11-08T06-50-38-119Z` |
| Suplementaria | Inicio 01:52:40 Lima; tiempos exactos en sus JSON |
| Equipo | Mismo CPU i9-14900HX, RAM 15,73 GiB, Windows 11 10.0.26300 y Chrome 156.0.8078.80 que ANTES; [consulta real](equipo.json) |
| Herramientas | Node 22.18.0, Lighthouse 12.8.2, Puppeteer Core 24.34.0; dependencias de medición aisladas en `.tmp-ecl115/` |
| Navegador | Chrome visible, sin extensiones, contextos de incógnito separados por página/rol |
| Lighthouse | Navigation, Performance, Desktop, 1350 × 940, DPR 1, `simulate`, RTT 40 ms, 10240 Kbps, CPU ×1, `disableStorageReset: true` |
| Network | DevTools real, sin throttling, `Disable cache` activo, `Keep log` desactivado, recarga completa hasta `networkidle0` + 1 s |
| API | `http://127.0.0.1:8000`; 20 GET secuenciales por endpoint, cookie de Operador solo en memoria, `Accept-Encoding: identity`, sin calentamientos adicionales dentro del recolector |
| Aplicación | `compose.yaml` + `compose.prod.yaml`; build React/Vite con Nginx 1.31.6; frontend `http://127.0.0.1:5173` |
| Docker / esquema | Engine 29.9.2, PostgreSQL 16/PostGIS comprobado; `alembic current` = `heads` = `0017_parametros_versionados (head)` |
| Aislamiento | Proyecto `ecologistica-lima-ecl115`; volumen nuevo y exclusivo; no se modificaron los proyectos ECL-108 ni ECL-29 |
| Dataset | `scripts/seed_demo.py` del commit medido: 8 clientes, 5 vehículos, 4 conductores, 20 pedidos, 5 asignaciones y 3 incidencias ficticias; agrega 1 versión de parámetros |

El usuario autorizó recrear un entorno demo aislado. Conserva los conteos de
negocio de ANTES, pero se sembró el 08/11/2026: cambian UUID, fechas y esquema;
no es una copia byte a byte de la base del 06/11. La API permanece en
`APP_ENV=development`, igual que el Compose de ANTES; «producción» identifica
el build y servidor del frontend, no un despliegue endurecido del sistema.
No se midió consumo eléctrico ni se verificó por software el modo de alimentación.

## Variaciones del protocolo y límites

1. El ticket y ECL-113 requieren producción, mientras ECL-108 usó Vite de
   desarrollo. Se conserva equipo, navegador, preset, roles, URLs, tres corridas
   por página medible y 20 peticiones por endpoint; se declara el cambio de
   servidor. No se presenta la comparación como condiciones idénticas.
2. Producción registra `sw.js`; desarrollo no lo hacía. Con el procedimiento
   original, una visita previa al login instala la caché offline. Deshabilitar
   caché HTTP no evita Cache Storage. La campaña principal mide recargas con
   ese efecto: **1.020 bytes en login y 3.103 en conductor**, no primera visita.
3. La campaña suplementaria usa `page.setBypassServiceWorker(true)` antes de
   navegar. Mantiene las demás condiciones y tres corridas, solo login y
   conductor; no repite las 60 peticiones API. Sus JSON Network registran
   explícitamente el bypass y el estado del service worker. No se mezcla con
   la principal ni representa la instalación inicial y precarga del shell.
4. Las capturas HTML de los reportes principales se renderizaron mientras
   comenzaba la campaña suplementaria. Es una carga concurrente leve y un
   límite de comparación; sus tiempos no se atribuyen exclusivamente al build.
5. La campaña principal no ejecutó tests ni builds concurrentes. Las pruebas de
   frontend se ejecutaron después de finalizar ambas campañas de medición.
6. El preset emula un user agent Chrome/macOS; Chrome y Windows reales son
   los de la tabla. Los tiempos Lighthouse son simulados, no cronometraje
   directo de una descarga. El JSON conserva precisión y `fetchTime` por corrida.

## Resultados y causas

| Mediana | Login principal | Conductor principal | Login sin SW | Conductor sin SW |
|---|---:|---:|---:|---:|
| Performance /100 | 100 | 100 | 100 | 99 |
| FCP ms | 25,84 | 38,09 | 652,92 | 722,06 |
| LCP ms | 29,90 | 194,10 | 652,92 | 902,48 |
| TBT ms | 0 | 0 | 0 | 0 |
| CLS | 0,000005295 | 0,019688179 | 0,000005295 | 0,019688179 |
| Network bytes | 1020 | 3103 | 433643 | 459748 |
| Peticiones | 8 | 14 | 8 | 14 |

En estas dos páginas no queda un umbral incumplido: Performance ≥90, FCP
≤1000 ms, LCP ≤1400 ms, TBT ≤85 ms, CLS ≤0,02 y peso ≤1.100.000 bytes.
Los archivos compilados y la carga diferida sustituyen módulos de desarrollo;
la caché offline explica los valores especialmente pequeños de la principal.
El CLS de conductor queda cercano al límite y no mejora frente a ANTES.

Inicio y Vehículos son NM por el mismo problema documentado en ECL-108:
`frontend/src/app/App.tsx` restaura identidad mediante `recallDriver`, y
`offlineAccess.ts` solo persiste CONDUCTOR. Se accedió con login real y
navegación normal, se capturó antes de recargar y se conservó la redirección
a login. Sus Network no se contabilizan como rendimiento de Operador.
No se inyectó identidad ni se cambió autenticación para fabricar resultados.

La media API de Vehículos pasa de 1183 a 1227 bytes (+44, +3,72%): ECL-109
cambia la lista por `VehiclePage` con `items`, `page`, `page_size` y `total`.
Con solo cinco vehículos se devuelve todo el conjunto y se agrega el envoltorio.
Conductores e Incidencias conservan 951 y 1255 bytes. Los tiempos medios pasan
de 7,46/8,09/8,13 ms a 9,90/9,69/8,25 ms: no se observa mejora. Una campaña
de 20 muestras no permite atribuir ese aumento a una causa concreta; cambian
esquema, servicios y condiciones del entorno. No se añadieron calentamientos
para seleccionar un resultado favorable.

Gzip está configurado y una petición Node con `Accept-Encoding: gzip` recibió
`Content-Encoding: gzip` y `Cache-Control: public, max-age=31536000, immutable`.
Sin embargo, Chrome transfirió los estáticos sin compresión observable: sus
tamaños en Lighthouse/Network incluyen el cuerpo completo y cabeceras.
El [diagnóstico separado](diagnostico-headers.json) confirma `identity` aunque
Chrome anuncia Gzip. La causa de esa diferencia queda sin determinar; no se
atribuye a Gzip una reducción que no aparece en esas mediciones.

## Entrega a Antony (ECL-116) y Julio (ECL-117)

Usar [comparacion.md](comparacion.md) y [comparacion.json](comparacion.json)
con sus escenarios explícitos. Bytes totales observados por recarga sin SW:
**login 433643 y conductor 459748**; ANTES 11434626 y 11438644. Son medianas
Network sin throttling, incluyendo cabeceras según Chrome, con caché HTTP
deshabilitada. No sumar otra vez los cuerpos API que ya están en el tráfico
de la página. No usar 1020/3103 como primera visita ni extrapolar NM a cero.

Estas cifras no incluyen la precarga inicial de todos los chunks del shell
offline. Para un modelo que incluya instalación inicial, debe medirse ese
escenario y declararse su frecuencia; ECL-116 decide el límite de cálculo y
los supuestos SWDM v4. No se calcularon kWh ni CO₂e en este ticket.
La entrega queda publicada con el PR; no se afirma recepción del equipo.

## Corrección autorizada de Nginx

La configuración integrada de ECL-113 no arrancaba: `unknown directive
"8,}\\.(js|css|woff2|png|svg)$"` en la línea 13. El usuario autorizó envolver
la expresión de `location` en comillas. Único cambio de aplicación:
`frontend/nginx.prod.conf`, commit `e58c65d`; `nginx -t` pasó y el contenedor
quedó saludable. ANTES recuperable con
`git show 69bd05b:frontend/nginx.prod.conf`. No se modifica la semántica de
la expresión ni se amplía el trabajo a autenticación o compresión.

## Reproducción y verificaciones

Desde la raíz, preparar privadamente `.env` y las variables `SEED_DEMO_PASSWORD_*`
de una base demo autorizada; no imprimirlas. Usar el arranque del README con
`-p ecologistica-lima-ecl115 -f compose.yaml -f compose.prod.yaml`, migraciones
y siembra de demostración. Nunca eliminar volúmenes para repetir la campaña.
El recolector exige no tener cambios de aplicación respecto a `HEAD`.

```powershell
npm.cmd install --prefix .tmp-ecl115 --cache .npm-cache --no-audit --no-fund --save-exact lighthouse@12.8.2 puppeteer-core@24.34.0
Remove-Item Env:ECL115_BYPASS_SW -ErrorAction SilentlyContinue
node 'docs/03 Implementación/reduccion del impacto ambiental/evidencias/despues/medir.mjs'
$env:ECL115_BYPASS_SW = '1'
node 'docs/03 Implementación/reduccion del impacto ambiental/evidencias/despues/medir.mjs'
Remove-Item Env:ECL115_BYPASS_SW
python 'docs/03 Implementación/reduccion del impacto ambiental/evidencias/despues/comparar.py' 'docs/03 Implementación/reduccion del impacto ambiental/evidencias/despues/run-2026-11-08T06-50-38-119Z' 'docs/03 Implementación/reduccion del impacto ambiental/evidencias/despues/run-2026-11-08T06-52-40-316Z'
python scripts/check_docs.py
```

El comparador vuelve a leer JSON y CSV originales, comprueba URLs, errores,
tres corridas, caché, versión/configuración Lighthouse, 20 respuestas 200 por
endpoint y recalcula medianas/medias/deltas. No reemplaza las evidencias.
`--write` solo crea la comparación si aún no existe; nuevas mediciones deben
usar carpetas y comparaciones nuevas. Para capturas de reportes nuevos, ejecutar
`capturar-reportes.mjs` con la ruta de la nueva campaña como argumento.

Validaciones locales: build de producción correcto; `nginx -t` correcto;
frontend `npm run typecheck`, `npm run lint` y `npm run test` correctos
(60 archivos, 892 tests). Backend no modificado; no se reejecutan sus tests.
CI, auditoría técnica independiente y aprobación humana se verifican en el PR.
Se conserva como borrador hasta auditarlo, según la política del repositorio.
El alcance de cuatro páginas sigue limitado por las dos filas NM.

No se versionan `.env`, cookies, contraseñas, HAR ni cuerpos de negocio.
Las capturas muestran cuentas/direcciones ficticias. Se conservan intactas
todas las evidencias ANTES y se crean archivos nuevos en DESPUÉS.

## Artefactos originales por corrida

| Campaña / página / corrida | Lighthouse | Captura reporte | Network | Captura Network | Página |
|---|---|---|---|---|---|
| run-2026-11-08T06-50-38-119Z / itinerario-conductor-01 | [JSON](run-2026-11-08T06-50-38-119Z/itinerario-conductor-01.lighthouse.json) | [PNG](run-2026-11-08T06-50-38-119Z/itinerario-conductor-01-lighthouse-reporte.png) | [JSON](run-2026-11-08T06-50-38-119Z/itinerario-conductor-01.network.json) | [PNG](run-2026-11-08T06-50-38-119Z/itinerario-conductor-01-network.png) | [PNG](run-2026-11-08T06-50-38-119Z/itinerario-conductor-01-pagina.png) |
| run-2026-11-08T06-50-38-119Z / itinerario-conductor-02 | [JSON](run-2026-11-08T06-50-38-119Z/itinerario-conductor-02.lighthouse.json) | [PNG](run-2026-11-08T06-50-38-119Z/itinerario-conductor-02-lighthouse-reporte.png) | [JSON](run-2026-11-08T06-50-38-119Z/itinerario-conductor-02.network.json) | [PNG](run-2026-11-08T06-50-38-119Z/itinerario-conductor-02-network.png) | [PNG](run-2026-11-08T06-50-38-119Z/itinerario-conductor-02-pagina.png) |
| run-2026-11-08T06-50-38-119Z / itinerario-conductor-03 | [JSON](run-2026-11-08T06-50-38-119Z/itinerario-conductor-03.lighthouse.json) | [PNG](run-2026-11-08T06-50-38-119Z/itinerario-conductor-03-lighthouse-reporte.png) | [JSON](run-2026-11-08T06-50-38-119Z/itinerario-conductor-03.network.json) | [PNG](run-2026-11-08T06-50-38-119Z/itinerario-conductor-03-network.png) | [PNG](run-2026-11-08T06-50-38-119Z/itinerario-conductor-03-pagina.png) |
| run-2026-11-08T06-50-38-119Z / login-01 | [JSON](run-2026-11-08T06-50-38-119Z/login-01.lighthouse.json) | [PNG](run-2026-11-08T06-50-38-119Z/login-01-lighthouse-reporte.png) | [JSON](run-2026-11-08T06-50-38-119Z/login-01.network.json) | [PNG](run-2026-11-08T06-50-38-119Z/login-01-network.png) | [PNG](run-2026-11-08T06-50-38-119Z/login-01-pagina.png) |
| run-2026-11-08T06-50-38-119Z / login-02 | [JSON](run-2026-11-08T06-50-38-119Z/login-02.lighthouse.json) | [PNG](run-2026-11-08T06-50-38-119Z/login-02-lighthouse-reporte.png) | [JSON](run-2026-11-08T06-50-38-119Z/login-02.network.json) | [PNG](run-2026-11-08T06-50-38-119Z/login-02-network.png) | [PNG](run-2026-11-08T06-50-38-119Z/login-02-pagina.png) |
| run-2026-11-08T06-50-38-119Z / login-03 | [JSON](run-2026-11-08T06-50-38-119Z/login-03.lighthouse.json) | [PNG](run-2026-11-08T06-50-38-119Z/login-03-lighthouse-reporte.png) | [JSON](run-2026-11-08T06-50-38-119Z/login-03.network.json) | [PNG](run-2026-11-08T06-50-38-119Z/login-03-network.png) | [PNG](run-2026-11-08T06-50-38-119Z/login-03-pagina.png) |
| run-2026-11-08T06-52-40-316Z / itinerario-conductor-01 | [JSON](run-2026-11-08T06-52-40-316Z/itinerario-conductor-01.lighthouse.json) | [PNG](run-2026-11-08T06-52-40-316Z/itinerario-conductor-01-lighthouse-reporte.png) | [JSON](run-2026-11-08T06-52-40-316Z/itinerario-conductor-01.network.json) | [PNG](run-2026-11-08T06-52-40-316Z/itinerario-conductor-01-network.png) | [PNG](run-2026-11-08T06-52-40-316Z/itinerario-conductor-01-pagina.png) |
| run-2026-11-08T06-52-40-316Z / itinerario-conductor-02 | [JSON](run-2026-11-08T06-52-40-316Z/itinerario-conductor-02.lighthouse.json) | [PNG](run-2026-11-08T06-52-40-316Z/itinerario-conductor-02-lighthouse-reporte.png) | [JSON](run-2026-11-08T06-52-40-316Z/itinerario-conductor-02.network.json) | [PNG](run-2026-11-08T06-52-40-316Z/itinerario-conductor-02-network.png) | [PNG](run-2026-11-08T06-52-40-316Z/itinerario-conductor-02-pagina.png) |
| run-2026-11-08T06-52-40-316Z / itinerario-conductor-03 | [JSON](run-2026-11-08T06-52-40-316Z/itinerario-conductor-03.lighthouse.json) | [PNG](run-2026-11-08T06-52-40-316Z/itinerario-conductor-03-lighthouse-reporte.png) | [JSON](run-2026-11-08T06-52-40-316Z/itinerario-conductor-03.network.json) | [PNG](run-2026-11-08T06-52-40-316Z/itinerario-conductor-03-network.png) | [PNG](run-2026-11-08T06-52-40-316Z/itinerario-conductor-03-pagina.png) |
| run-2026-11-08T06-52-40-316Z / login-01 | [JSON](run-2026-11-08T06-52-40-316Z/login-01.lighthouse.json) | [PNG](run-2026-11-08T06-52-40-316Z/login-01-lighthouse-reporte.png) | [JSON](run-2026-11-08T06-52-40-316Z/login-01.network.json) | [PNG](run-2026-11-08T06-52-40-316Z/login-01-network.png) | [PNG](run-2026-11-08T06-52-40-316Z/login-01-pagina.png) |
| run-2026-11-08T06-52-40-316Z / login-02 | [JSON](run-2026-11-08T06-52-40-316Z/login-02.lighthouse.json) | [PNG](run-2026-11-08T06-52-40-316Z/login-02-lighthouse-reporte.png) | [JSON](run-2026-11-08T06-52-40-316Z/login-02.network.json) | [PNG](run-2026-11-08T06-52-40-316Z/login-02-network.png) | [PNG](run-2026-11-08T06-52-40-316Z/login-02-pagina.png) |
| run-2026-11-08T06-52-40-316Z / login-03 | [JSON](run-2026-11-08T06-52-40-316Z/login-03.lighthouse.json) | [PNG](run-2026-11-08T06-52-40-316Z/login-03-lighthouse-reporte.png) | [JSON](run-2026-11-08T06-52-40-316Z/login-03.network.json) | [PNG](run-2026-11-08T06-52-40-316Z/login-03-network.png) | [PNG](run-2026-11-08T06-52-40-316Z/login-03-pagina.png) |

### Diagnóstico de Operador y API

- inicio-operador: [antes de recargar](run-2026-11-08T06-50-38-119Z/inicio-operador-antes-recarga.png), [tras recarga](run-2026-11-08T06-50-38-119Z/inicio-operador-01-pagina.png), [Network](run-2026-11-08T06-50-38-119Z/inicio-operador-01.network.json), [diagnóstico](run-2026-11-08T06-50-38-119Z/inicio-operador.resultado.json).
- vehiculos-operador: [antes de recargar](run-2026-11-08T06-50-38-119Z/vehiculos-operador-antes-recarga.png), [tras recarga](run-2026-11-08T06-50-38-119Z/vehiculos-operador-01-pagina.png), [Network](run-2026-11-08T06-50-38-119Z/vehiculos-operador-01.network.json), [diagnóstico](run-2026-11-08T06-50-38-119Z/vehiculos-operador.resultado.json).
- API vehiculos: [20 muestras CSV](run-2026-11-08T06-50-38-119Z/api-vehiculos.csv).
- API conductores: [20 muestras CSV](run-2026-11-08T06-50-38-119Z/api-conductores.csv).
- API incidencias: [20 muestras CSV](run-2026-11-08T06-50-38-119Z/api-incidencias.csv).

[Datos completos de la principal](run-2026-11-08T06-50-38-119Z/resultados.json) · [Datos completos de la suplementaria](run-2026-11-08T06-52-40-316Z/resultados.json).

[← Volver al README principal](../../../../../README.md)
