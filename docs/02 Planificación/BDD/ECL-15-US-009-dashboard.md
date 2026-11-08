# ECL-97 / ECL-15 — Reglas y BDD de US-009: dashboard

> **Estado: APROBADO — BDD v1.0.0 (07/11/2026).** Ratificación expresa de
> Julio para los criterios de aceptación de US-009; no contiene resultados
> de pruebas ejecutadas ni indicadores ambientales reales.

| Metadato | Valor |
|---|---|
| Versión | 1.0.0 |
| Fecha | 06/11/2026, America/Lima |
| Autor | Frank Roy Yupanqui Acevedo — @FrankRoyYA |
| Ticket / historia | [ECL-97](https://continental-team-il84x39k.atlassian.net/browse/ECL-97) / [ECL-15, US-009](https://continental-team-il84x39k.atlassian.net/browse/ECL-15) |
| Ratificación de negocio | Julio Armando Naupari Camarena — @JulioNaupariC; 07/11/2026 |
| Dependencia | US-006, parámetros versionados y contrato ST-045; dashboard de Giancarlo |

## Fuentes y alcance

- [RF-009, RF-001 y equivalencia ambiental RF-011](<../../01 Inicio/06. Requisitos funcionales V_1_1_0.md>).
- [RN-002, RN-011 a RN-014 y parámetros históricos](<../../01 Inicio/09. Reglas de negocio V_1_1_0.md>).
- [RNF-004, RNF-009, RNF-011 y RNF-012](<../../01 Inicio/07. Requisitos no funcionales V_1_2_0.md>).
- [ruta, parada_ruta, optimizacion y parametro](<../../01 Inicio/11. Base de datos V_1_4_0.md>),
  [BDD US-006](ECL-12-US-006-rutas-optimizadas.md),
  [matriz de roles](<../../01 Inicio/08. Usuarios V_1_0_0.md>) y
  [contrato ST-045](../../../backend/app/schemas/rutas.py).

Solo especificación de consulta y pruebas. No crea dashboards, cambia la
matriz de permisos ni declara rutas efectivamente recorridas a partir de ETA.

## Reglas y decisiones propuestas

### Acceso, periodo y ruta cerrada

`GET /indicadores/sostenibilidad?desde=YYYY-MM-DD&hasta=YYYY-MM-DD` requiere
sesión. Administrador, Operador y Analista están en el contrato de Frank;
la matriz y ST-045 incluyen además al Auditor en lectura agregada. Se ratifica conservar Auditor con acceso exclusivamente agregado, sin datos
personales, de acuerdo con la matriz.
Conductor 403, sin sesión 401. No se entregan conductores, ubicaciones,
pedidos individuales ni geometrías en este agregado; auditoría sin datos personales.

Fechas válidas, `desde≤hasta`; ambos días inclusivos en America/Lima. Propuesta:
filtrar por instante `cerrada_en`, desde 00:00 del primer día inclusive hasta
00:00 del día posterior a `hasta` exclusivo. No usar fecha de solicitud de
optimización como sustituto del cierre. El modelo objetivo y ST-045 no tienen
`cerrada_en`: requiere ratificación y actualización del contrato/modelo por el
ticket implementador, sin alterar la línea base en esta tarea.

**Ruta cerrada (definición candidata):** ruta con estado CERRADA persistido
mediante transición autorizada por Operador, fecha de cierre y todas las
paradas terminales (ATENDIDA o NO_ATENDIDA con resultado explícito). No cerrar
por alcanzar una ETA ni por tener una optimización COMPLETADA. No cerrar con
paradas PENDIENTE. Una NO_ATENDIDA no se presenta como entrega exitosa.
Transición propuesta PLANIFICADA → EN_CURSO → CERRADA; reintento no duplica
la ruta agregada ni su auditoría de cierre. El endpoint de cierre no se define
ni se implementa como parte de esta BDD de lectura.

### Indicadores, unidades y exactitud

| Indicador | Definición propuesta |
|---|---|
| rutas_cerradas | Conteo de rutas únicas con cierre válido dentro del periodo. |
| distancia_km / co2_kg / combustible_l / costo_soles | Suma de métricas persistidas de las rutas incluidas, con parámetros y fuente conservados; fórmulas de US-006 y RN-011–013. |
| ahorro_vs_secuencial por magnitud | Suma de referencia secuencial comparable menos suma optimizada; misma cobertura de pedidos, periodo y versiones. |
| ahorro_vs_secuencial.pct | Propuesta: ahorro de distancia, 100 × (Σsecuencial_km − Σoptimizada_km) / Σsecuencial_km. No promediar porcentajes de rutas. Base cero: null. |
| cumplimiento_ventanas_pct | Propuesta: 100 × paradas ATENDIDA dentro de su ventana / todas las paradas terminales de las rutas cerradas del periodo. NO_ATENDIDA cuenta como incumplida; se usa atendida_en real, no ETA. Sin denominador: null. |
| parametros_versiones | Versiones distintas realmente usadas, ordenadas de forma estable; no recalcular el pasado con valores actuales. |
| Equivalente ambiental | Solo con factor de captura vigente, unidad, fuente y proyecto registrado (RN-014); sin ellos, «No disponible». No implica crédito certificado. |

Distinguir en la UI estimaciones de planificación de mediciones reales de
operación. Si la ruta solo dispone de métricas estimadas del plan, se identifican
como estimadas; CERRADA no las convierte en telemetría medida. RF-009 exige
equivalente ambiental, ausente en ST-045; se propone extensión nullable con
valor, unidad, factor, fuente y versión, ratificada antes de implementarla.

No inventar factores ni componentes de costo. Conversión de galón a litros
debe resolverse como en US-006. Presentación redondeada por unidad, cálculos
sin redondeos intermedios; error absoluto ≤0,01 en 20 referencias RNF-011.

### Sin datos, errores y transferencia

- Sin rutas cerradas: 200, `con_datos:false`, `rutas_cerradas:0`,
  `parametros_versiones:[]`, métricas y objeto de ahorro `null`;
  cumplimiento `null`. El cero del conteo es real; no reemplazar indicadores
  ausentes por 0, porcentajes ficticios ni ejemplos del contrato.
- Periodo con rutas cerradas y una métrica calculada igual a cero: con_datos
  true, cero válido identificado como medición/cálculo, distinto de null.
  Si faltan datos necesarios de una ruta, no descartarla silenciosamente ni
  mostrar sumas parciales como completas; error controlado seguro y registro
  del problema. La definición de cierre debe garantizar los datos obligatorios.
- `desde>hasta`, fecha inválida o ausente: 422 sin eco de valores.
  Errores de servidor o sesión no se muestran como «Sin datos».
- RNF-012: respuesta agregada ≤250 KB sin mapa; propuesta verificable:
  JSON UTF-8 sin compresión ≤250 000 bytes, guardar también bytes transferidos
  y revisión del plan/índices de consulta. No transportar geometrías para calcular
  KPIs en el navegador. Ratificar unidad KB antes de la campaña.
- Mostrar periodo, unidades y estado de carga/error en texto accesible.
  Respuestas `simulado:true` se muestran como datos de prueba, nunca evidencia
  ambiental real.

## Datos de prueba previstos

Dos rutas cerradas sintéticas de un mismo periodo: métricas optimizadas
(100 km, 20 kg, 10 L, 160 S/) y (50 km, 10 kg, 5 L, 80 S/), secuenciales
(120 km, 24 kg, 12 L, 192 S/) y (80 km, 16 kg, 8 L, 128 S/).
Agregado esperado: 150 km, 30 kg, 15 L, 240 S/; ahorro 50 km, 10 kg,
5 L, 80 S/, 25 % de distancia. Cuatro paradas terminales: tres a tiempo
y una NO_ATENDIDA → 75 %. Agregar rutas fuera del periodo, PLANIFICADA
y EN_CURSO que no deben contarse. Son expectativas, no resultados ejecutados.

## Escenarios Gherkin — ruta dorada

### D01 — Periodo con rutas cerradas

- **DADO** usuario autorizado y las dos rutas cerradas del fixture, más rutas excluidas.
- **CUANDO** consulta el periodo en API y dashboard.
- **ENTONCES** obtiene los agregados esperados, 2 rutas, 25 % de ahorro ponderado por distancia y 75 % de cumplimiento, con unidades y periodo; no se filtran datos personales.

## Escenarios Gherkin — ruta feliz

### D02 — Parámetros históricos y exactitud

- **DADO** rutas cerradas con versiones distintas de parámetros y factores conocidos.
- **CUANDO** cambia el parámetro actual y vuelve a consultar el periodo histórico.
- **ENTONCES** conserva las cifras históricas y enumera sus versiones.
- **Y** 20 cálculos independientes de CO₂/costo difieren como máximo 0,01; conversión de combustible y precio es dimensionalmente correcta.

### D03 — Equivalencia ambiental condicionada

- **DADO** un factor vigente y proyecto registrado; repetir sin factor o sin proyecto.
- **CUANDO** consulta el equivalente ambiental del periodo.
- **ENTONCES** solo muestra una cifra calculada con unidad, fuente y versión cuando se cumplen ambos requisitos; en otro caso indica «No disponible» sin cifra inventada ni crédito certificado.

## Escenarios Gherkin — ruta infeliz

### D04 — Filtros o permisos inválidos

- **DADO** desde posterior a hasta, fecha inválida o ausente (cada caso separado).
- **CUANDO** consulta indicadores.
- **ENTONCES** recibe 422 sin eco; la UI indica corrección de filtros, sin interpretar el error como periodo vacío.
- **DADO** ausencia de sesión o sesión Conductor.
- **CUANDO** consulta.
- **ENTONCES** recibe 401 o 403; probar también los demás roles según decisión de Julio sobre Auditor.

### D05 — Cierre incompleto o datos faltantes

- **DADO** ruta con parada pendiente o métricas obligatorias ausentes.
- **CUANDO** se intenta cerrar y después consultar.
- **ENTONCES** no se confirma cierre inválido ni se publican agregados parciales como completos; un fallo de carga conserva un estado de error distinto de «Sin datos».

## Escenarios Gherkin — ruta de borde

### D06 — Sin datos frente a cero real

- **DADO** periodo sin rutas cerradas y otro con rutas cuyos valores válidos son cero.
- **CUANDO** consulta ambos.
- **ENTONCES** el primero devuelve con_datos false e indicadores null; el segundo conserva con_datos true y ceros reales, sin confundirlos.
- **Y** denominador secuencial cero produce pct null; los ahorros negativos no se ocultan ni recortan a cero.

### D07 — Cierre, límites del periodo y reintento

- **DADO** cierres exactamente al inicio del primer día, al final del último y al inicio del siguiente, con zonas equivalentes.
- **CUANDO** consulta un periodo incluso de un solo día y repite un cierre ya persistido.
- **ENTONCES** incluye solo los dos primeros cierres, sin duplicados, usando instantes Lima; estado COMPLETADA de optimización por sí solo no suma rutas.

### D08 — Agregado accesible y limitado

- **DADO** dataset representativo del periodo, sin incluir geometrías.
- **CUANDO** consulta API e interfaz en Chrome y Firefox con versiones registradas.
- **ENTONCES** JSON UTF-8 cumple el límite propuesto de 250 000 bytes, se documenta plan de consultas y las cifras/unidades/filtros son legibles por teclado y lector.

## Trazabilidad y pruebas previstas

| Escenario | RF / RN / RNF | Prueba prevista |
|---|---|---|
| D01 | RF-009; RN-011–013; RNF-004, RNF-011 | BD/API/UI con agregado de referencia y exclusión de estados/periodos. |
| D02 | RF-009; RN-011–013; RNF-011 | 20 referencias, historial y unidades/precios por versión. |
| D03 | RF-009, RF-011; RN-014 | Unitarias/API/UI con factor/proyecto presentes y ausentes. |
| D04 | RF-001, RF-009; RN-002; RNF-003, RNF-004 | API cinco roles, filtros y respuestas saneadas. |
| D05 | RF-009; RN-015; modelo ruta/parada_ruta | Integración transaccional, datos incompletos y UI de error. |
| D06 | RF-009; RNF-011 | API/UI: null frente a cero, división por cero y ahorro negativo. |
| D07 | RF-009; RN-002; modelo ruta/parada_ruta | BD con reloj fijo, límites de fecha y cierre repetido. |
| D08 | RF-009; RNF-009, RNF-012 | Medición de bytes, revisión EXPLAIN e inclusión en matriz crítica de 15 flujos compartida con US-006/008. |

## Cambios al contrato provisional

Posición técnica de Antony del 06/11/2026, 19:18 (America/Lima), en su
[comentario de backend](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/91#pullrequestreview-5808785030).
Es una propuesta para Julio; no ratifica decisiones ni modifica las reglas.

| Decisión pendiente | Impacto para ST-045 y modelo | Posición técnica (backend) |
|---|---|---|
| Auditor autorizado en agregado | ST-045/matriz lo permiten; el prompt no lo lista. Se propone conservarlo sin datos personales; ratificar. | Propone mantener la matriz vigente, pero no concreta una decisión sobre Auditor en dashboard; decide Julio. |
| Cierre explícito y cerrada_en | Ausente en modelo/contrato actual; necesario para filtro por cierre y definición verificable. Ratificar estados terminales y responsable, sin implementar endpoint de cierre aquí. | Sin precisión específica en el comentario; pendiente de decisión de Julio. |
| Definición de pct y cumplimiento | Precisar que pct compara distancia agregada y que cumplimiento usa resultados reales, incluidos NO_ATENDIDA en denominador. No inferirlo de ETA. | No concreta la magnitud de pct ni el denominador de cumplimiento; decide Julio. |
| Null con datos y porcentajes negativos | El esquema actual obliga todos los indicadores con con_datos true y acota pct a [-100,100]. Debe admitir denominador cero en porcentajes y empeoramiento mayor al 100 %. | Indica que puede ajustar ST-045 con pct nulo y negativos en este sprint. |
| Equivalente ambiental nullable | RF-009 lo exige, falta en ST-045. Propuesta de objeto con unidad, factor, fuente y versión; sin configuración no inventar valor. | Sin precisión específica en el comentario; pendiente de decisión de Julio. |

## Ratificación de Julio — 07/11/2026

Julio ratifica las reglas y escenarios D01–D08 de US-009 con las precisiones:

- Acceso a agregados: Administrador, Operador, Analista y Auditor autorizado,
  sin datos personales; Conductor no autorizado al agregado.
- Ruta cerrada: transición persistida autorizada por Operador, `cerrada_en`
  y todas las paradas terminales; una optimización COMPLETADA o una ETA
  alcanzada no cierran la ruta. La ampliación de modelo/contrato sigue pendiente.
- Periodos: extremos diarios inclusivos de Lima implementados con límite
  superior exclusivo al inicio del día siguiente, basado en `cerrada_en`.
- Ahorros: comparar sumas agregadas con igual cobertura; porcentaje de
  distancia desde sumas, no promedio de porcentajes. Denominador cero =>
  `null`; valores negativos permitidos sin truncamiento artificial.
- Cumplimiento de ventanas: paradas `ATENDIDA` dentro de ventana frente a
  todas las terminales; `NO_ATENDIDA` cuenta en denominador y no es éxito.
  Solo tiempos reales `atendida_en`, nunca ETA de planificación.
- Equivalente ambiental: solo presentar cifra cuando haya proyecto registrado,
  factor vigente, unidad, fuente y versión. Si falta, «No disponible», nunca
  crédito ambiental certificado inventado.
- Sin datos frente a cero: distinguir ausencia de información de un cero
  real. Preservar parámetros históricos y las pruebas de exactitud.
- RNF-012: mantener la propuesta comprobable de límite JSON sin comprimir
  de 250 000 bytes para validación; distinguir del tamaño transferido. Se
  verifica en implementación, no se presenta como medición ya realizada.

La aprobación de la BDD no acredita rutas cerradas reales, mediciones de
carbono ni cumplimiento de rendimiento; esas verificaciones corresponden
a los tickets implementadores y sus evidencias.

## Aprobación y entrega

Ratificación de negocio registrada el 07/11/2026; la auditoría técnica
independiente, los checks, revisión de Frank y merge se verifican en el PR.
No se modifican requisitos, permisos ni fixtures mediante esta BDD.

| Versión | Fecha | Cambio |
|---|---|---|
| 0.1.0 | 06/11/2026 | Escenarios D01–D08, cierre, métricas, null, periodo y decisiones de contrato. |
| 0.1.1 | 06/11/2026 | Incorpora la propuesta técnica de backend y navegación del Sprint 4; reglas sin cambios y aprobación de Julio pendiente. |
| 1.0.0 | 07/11/2026 | Ratificación expresa de acceso, cierre, periodos, agregados, equivalentes ambientales y valores nulos; implementación pendiente. |

[Índice del Sprint 4](<../../03 Implementación/Sprint 04/README.md>) ·
[← Volver al README principal](../../../README.md)
