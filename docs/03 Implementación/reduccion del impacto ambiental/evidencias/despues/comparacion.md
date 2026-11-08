# ECL-115 — Comparación reproducible ANTES vs. DESPUÉS

Δ = DESPUÉS − ANTES; Δ% = 100 × Δ / ANTES. Base cero: porcentaje indefinido.
Mediana independiente de cada métrica de tres corridas. MB decimal (1,1 MB = 1 100 000 bytes).
NM = no medible; nunca se sustituye por cero. API: media de 20 respuestas HTTP 200.

Producción cambia el modo de servicio respecto a Vite desarrollo. La campaña principal conserva
el procedimiento original y reutiliza Cache Storage del service worker. La suplementaria
evita el service worker: es otro escenario, no una repetición exacta ni una primera visita con precarga.

## `/login`

| Métrica | ANTES | DESPUÉS principal | Δ | Δ% | DESPUÉS sin SW | Δ sin SW | Δ% sin SW |
|---|---:|---:|---:|---:|---:|---:|---:|
| Performance /100 | 55 | 100 | 45 | 81.818181818 | 100 | 45 | 81.818181818 |
| FCP ms | 5653.6906 | 25.838169098 | -5627.852430902 | -99.542985796 | 652.922 | -5000.7686 | -88.451401992 |
| LCP ms | 10743.5359 | 29.897302628 | -10713.638597372 | -99.721718223 | 652.922 | -10090.6139 | -93.922652597 |
| TBT ms | 0 | 0 | 0 | N/A (base cero) | 0 | 0 | N/A (base cero) |
| CLS | 0.000005295 | 0.000005295 | 0 | 0 | 0.000005295 | 0 | 0 |
| Transferido bytes | 11434626 | 1020 | -11433606 | -99.991079726 | 433643 | -11000983 | -96.207632851 |
| Peticiones | 88 | 8 | -80 | -90.909090909 | 8 | -80 | -90.909090909 |

| Umbral | Principal | Sin SW |
|---|---|---|
| Performance /100: ≥ 90 | Cumple | Cumple |
| FCP ms: ≤ 1000 | Cumple | Cumple |
| LCP ms: ≤ 1400 | Cumple | Cumple |
| TBT ms: ≤ 85 | Cumple | Cumple |
| CLS: ≤ 0.02 | Cumple | Cumple |
| Transferido bytes: ≤ 1100000 | Cumple | Cumple |

## `/`

| Métrica | ANTES | DESPUÉS principal | Δ | Δ% | DESPUÉS sin SW | Δ sin SW | Δ% sin SW |
|---|---:|---:|---:|---:|---:|---:|---:|
| Todas | NM | NM | N/A | N/A | NM | N/A | N/A |

La recarga completa redirige a login; no hay tres corridas válidas de esta vista.

## `/vehiculos`

| Métrica | ANTES | DESPUÉS principal | Δ | Δ% | DESPUÉS sin SW | Δ sin SW | Δ% sin SW |
|---|---:|---:|---:|---:|---:|---:|---:|
| Todas | NM | NM | N/A | N/A | NM | N/A | N/A |

La recarga completa redirige a login; no hay tres corridas válidas de esta vista.

## `/conductor/itinerario`

| Métrica | ANTES | DESPUÉS principal | Δ | Δ% | DESPUÉS sin SW | Δ sin SW | Δ% sin SW |
|---|---:|---:|---:|---:|---:|---:|---:|
| Performance /100 | 55 | 100 | 45 | 81.818181818 | 99 | 44 | 80 |
| FCP ms | 5677.355 | 38.094455719 | -5639.260544281 | -99.329010504 | 722.0605 | -4955.2945 | -87.281744756 |
| LCP ms | 10911.0325 | 194.098038629 | -10716.934461371 | -98.221084589 | 902.4847 | -10008.5478 | -91.728695703 |
| TBT ms | 0 | 0 | 0 | N/A (base cero) | 0 | 0 | N/A (base cero) |
| CLS | 0.019688179 | 0.019688179 | 0 | 0 | 0.019688179 | 0 | 0 |
| Transferido bytes | 11438644 | 3103 | -11435541 | -99.972872659 | 459748 | -10978896 | -95.980747368 |
| Peticiones | 90 | 14 | -76 | -84.444444444 | 14 | -76 | -84.444444444 |

| Umbral | Principal | Sin SW |
|---|---|---|
| Performance /100: ≥ 90 | Cumple | Cumple |
| FCP ms: ≤ 1000 | Cumple | Cumple |
| LCP ms: ≤ 1400 | Cumple | Cumple |
| TBT ms: ≤ 85 | Cumple | Cumple |
| CLS: ≤ 0.02 | Cumple | Cumple |
| Transferido bytes: ≤ 1100000 | Cumple | Cumple |

## API (Accept-Encoding: identity)

| Endpoint | Métrica | ANTES | DESPUÉS | Δ | Δ% |
|---|---|---:|---:|---:|---:|
| `/vehiculos` | Media ms | 7.460595 | 9.90085 | 2.440255 | 32.708584235 |
| `/vehiculos` | Media bytes cuerpo | 1183 | 1227 | 44 | 3.719357566 |
| `/vehiculos` | Min bytes | 1183 | 1227 | 44 | 3.719357566 |
| `/vehiculos` | Max bytes | 1183 | 1227 | 44 | 3.719357566 |
| `/conductores?page=1` | Media ms | 8.09236 | 9.69475 | 1.60239 | 19.801269345 |
| `/conductores?page=1` | Media bytes cuerpo | 951 | 951 | 0 | 0 |
| `/conductores?page=1` | Min bytes | 951 | 951 | 0 | 0 |
| `/conductores?page=1` | Max bytes | 951 | 951 | 0 | 0 |
| `/incidencias?page=1` | Media ms | 8.127395 | 8.25252 | 0.125125 | 1.539546189 |
| `/incidencias?page=1` | Media bytes cuerpo | 1255 | 1255 | 0 | 0 |
| `/incidencias?page=1` | Min bytes | 1255 | 1255 | 0 | 0 |
| `/incidencias?page=1` | Max bytes | 1255 | 1255 | 0 | 0 |

[← Volver al README principal](../../../../../README.md)
