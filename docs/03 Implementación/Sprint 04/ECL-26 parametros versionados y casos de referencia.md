# ECL-26 / EN-008 — Parámetros versionados y casos de referencia (RNF-011)

- [Volver ->](<../../../README.md>)

| Metadato | Valor |
|---|---|
| Ticket | [ECL-26](https://continental-team-il84x39k.atlassian.net/browse/ECL-26) |
| Implementación | Antony Munive — @ANTONY-MUNIVE |
| Fuentes y casos de referencia | Julio Naupari — @JulioNaupariC |
| Estado de los casos | **Pendiente:** el archivo de casos tiene solo la cabecera |

## Qué se versiona

| Código | Unidad | Uso | Origen del valor inicial |
|---|---|---|---|
| `PRECIO_COMBUSTIBLE_GALON` | PEN/gal | RN-011 | Valor de referencia de RN-011 (S/ 17,50 por galón de diésel); falta fuente de mercado |
| `LITROS_POR_GALON` | L/gal | Decisión 8 de la BDD de US-006 | 3,785411784 L: definición exacta del galón estadounidense (NIST Handbook 44, Apéndice C) |
| `COSTO_MANTENIMIENTO_KM` | PEN/km | RN-012 | Valor de referencia de RN-012 (S/ 1,20 por km); falta fuente de mercado |
| `CAPTURA_CO2_ARBOL_ANIO` | kgCO2/arbol/anio | RN-014 (opcional) | Sin valor: no hay factor con fuente, así que la compensación no se muestra |

- El factor de emisión (kg CO₂/km) y el rendimiento (km/L) son de cada vehículo (RN-013). La instantánea de cada optimización conserva los valores usados.
- Una versión nueva cierra la anterior en su `vigente_desde`; nada se edita ni se borra.
- `optimizacion.parametros_version` referencia una versión existente.

## Fórmulas (`backend/app/core/calculos.py`)

| Magnitud | Fórmula |
|---|---|
| Combustible (L) | km ÷ rendimiento_km_l |
| CO₂ (kg) | km × factor_co2_kg_km |
| Costo de combustible (S/) | litros ÷ LITROS_POR_GALON × PRECIO_COMBUSTIBLE_GALON |
| Costo de mantenimiento (S/) | km × COSTO_MANTENIMIENTO_KM |
| Costo de ruta (S/) | combustible + mantenimiento |
| Árboles equivalentes | CO₂ ÷ CAPTURA_CO2_ARBOL_ANIO; sin factor, no se calcula |

Nada se redondea en el cálculo; solo al presentar.

## Casos de referencia (RNF-011)

[ECL-26 casos de referencia RNF-011.csv](<ECL-26 casos de referencia RNF-011.csv>):
**20 casos** calculados a mano o en hoja de cálculo, **independientes del
código**. Una fila por caso, con punto decimal; los campos de árboles quedan
vacíos si no se usa el factor.

`backend/tests/unit/test_casos_referencia_rnf011.py` recalcula cada fila y
exige una diferencia absoluta ≤ 0,01 en combustible, CO₂, costo y árboles.
Mientras el archivo tenga menos de 20 casos, la prueba de completitud queda
marcada como **omitida** con el motivo «pendiente», nunca como aprobada.

[← Volver al README principal](../../../README.md)
