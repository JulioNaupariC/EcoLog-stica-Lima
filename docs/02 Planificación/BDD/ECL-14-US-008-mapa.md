# ECL-97 / ECL-14 — Reglas y BDD de US-008: mapa operativo

> **Estado: BORRADOR.** Aprobación de Julio pendiente antes de implementar
> esta historia (A4). Escenarios previstos, sin resultados de prueba ejecutados.

| Metadato | Valor |
|---|---|
| Versión | 0.1.0 |
| Fecha | 06/11/2026, America/Lima |
| Autor | Frank Roy Yupanqui Acevedo — @FrankRoyYA |
| Ticket / historia | [ECL-97](https://continental-team-il84x39k.atlassian.net/browse/ECL-97) / [ECL-14, US-008](https://continental-team-il84x39k.atlassian.net/browse/ECL-14) |
| Revisor | Julio Armando Naupari Camarena — @JulioNaupariC |
| Dependencias | BDD de US-006 aprobada y contrato ST-045 ajustado; implementación del mapa de José según el ticket proporcionado |

## Fuentes y alcance

- [RF-008 y RF-001](<../../01 Inicio/06. Requisitos funcionales V_1_1_0.md>).
- [RN-002, RN-006, RN-009 y RN-010](<../../01 Inicio/09. Reglas de negocio V_1_1_0.md>).
- [RNF-003 a RNF-006, RNF-009 y cumplimiento transversal](<../../01 Inicio/07. Requisitos no funcionales V_1_2_0.md>).
- [ruta y parada_ruta](<../../01 Inicio/11. Base de datos V_1_1_0.md>),
  [C4 e integraciones degradadas](<../../01 Inicio/12. Modelo C4 V_1_0_0.md>),
  [contrato publicado provisional](../../../backend/app/schemas/rutas.py) y
  [BDD US-006](ECL-12-US-006-rutas-optimizadas.md).

Define observables del mapa y su alternativa accesible. No diseña ni implementa
pantallas, proveedor de tráfico, rutas ni tiles. Datos de fixtures deben seguir
identificados como simulados; disponer de una geometría no demuestra una red vial real.

## Reglas

1. Administrador y Operador consultan el detalle operativo general mediante
   `GET /optimizaciones/{id}`; sin sesión 401, otro rol sin alcance de detalle
   403. No se revoca el acceso propio del Conductor ni el agregado/anonimizado
   de Analista/Auditor de la matriz global: esas proyecciones no se implementan
   mediante este endpoint general. Resolver RBAC junto con R11 de US-006.
2. Geometría GeoJSON `LineString`, posiciones `[longitud, latitud]`, WGS84
   SRID 4326, con al menos dos posiciones válidas. Marcadores usan `latitud`
   y `longitud` de cada parada sin invertir ejes.
3. La secuencia es única y consecutiva desde 1 por ruta; mapa y lista muestran
   la misma versión, pedidos y orden. ETA incluye fecha y offset `-05:00`,
   ventanas completas y unidad de duración por tramo (minutos). Nunca calcular
   tiempo por tramo restando ETA sin separar servicio/espera/descanso.
4. ETA es estimación, distinta de `atendida_en` real. Si cambia por tráfico,
   indicar origen y hora de la actualización; no sobrescribir hechos ejecutados.
5. RN-010: alerta de seguridad aumenta costo informativo; solo un bloqueo
   configurado por Administrador excluye una vía. El mapa indica severidad,
   fuente, hora, alcance y condición de bloqueo en texto, no solo color.
6. Fuente de tráfico caída: conservar último dato válido con su hora y fuente,
   mostrar «Tráfico no disponible; último dato…» y estado degradado. No actualizar
   artificialmente la hora, ni repetir solicitudes sin control. Con primera
   consulta sin dato previo, mostrar «Sin datos de tráfico» con hora `null`;
   nunca «fluido», cero congestión ni ETA en tiempo real inventados.
7. Si no hay actualización de tráfico, conservar el plan con su ETA y hora de
   cálculo identificadas como tales; no atribuir la ETA al proveedor caído.
   Caída de tiles/mapa no impide consultar la lista previamente obtenida.
8. La lista de paradas es alternativa funcional al mapa: secuencia, ubicación
   textual permitida, ETA, ventana, estado y alertas en texto, accesible con
   teclado, foco visible y lector de pantalla. No requiere interacción sobre
   un marcador para acceder a la misma información operativa.
9. Sin rutas: estado vacío explícito, sin trazados de ejemplo reales. EN_PROCESO
   muestra espera; FALLIDA muestra error seguro. Un fallo de carga no se confunde
   con conjunto vacío. Evitar nombres/DNI/contacto en logs o errores.

## Datos y contrato candidato de tráfico

Propuesta **pendiente de Julio**, ausente en ST-045 actual: agregar al detalle
`trafico` con `estado` (`DISPONIBLE`, `DEGRADADO`, `SIN_DATOS`), `fuente`
nullable, `actualizado_en` nullable (hora del dato, no de la última consulta),
y `tramos` con referencia a secuencias origen/destino, `tiempo_min` y nivel de
congestión nullable. Inicio/retorno se identifican expresamente como depósito.
En SIN_DATOS: sin mediciones y fuente/hora ausentes si nunca se obtuvieron.
Agregar `alertas` con ID, tipo, severidad, texto seguro, fuente, hora,
ubicación o tramo afectado y `bloqueo: boolean`. Vacío significa ninguna alerta
en esa fuente/corte, no garantía de ausencia de riesgos en la ciudad.
Ratificar catálogo de congestión y antigüedad máxima antes de implementarlos;
no se fija un umbral arbitrario en esta BDD.

Fixture sintético: ruta con depósito y tres paradas, ETA en Lima, alerta de
riesgo no bloqueante y un bloqueo explícito en otro tramo. Tráfico válido
en T0 y fallo en T1 > T0; probar también caché vacía. No son hechos observados.

## Escenarios Gherkin — ruta dorada

### M01 — Ver ruta y alternativa accesible

- **DADO** Operador autenticado y una optimización COMPLETADA con tres paradas ordenadas.
- **CUANDO** abre la ruta y alterna mapa y lista mediante teclado.
- **ENTONCES** ambos muestran el mismo orden, ETA con fecha/zona, ventanas y alertas; GeoJSON se interpreta sin invertir coordenadas y cada parada se identifica en texto.
- **Y** puede consultar toda la información sin manipular el mapa.

## Escenarios Gherkin — ruta feliz

### M02 — Tiempos y alertas vigentes

- **DADO** datos válidos de tráfico por tramo con fuente/hora y dos alertas, una informativa y otra configurada como bloqueo.
- **CUANDO** consulta los tramos y alertas.
- **ENTONCES** ve minutos por tramo y congestión con fuente y hora; distingue riesgo de bloqueo mediante texto e icono, y el riesgo no bloquea automáticamente la vía.

### M03 — Fuente caída con último dato

- **DADO** último dato en T0 y proveedor sin respuesta en T1.
- **CUANDO** carga o actualiza la ruta.
- **ENTONCES** conserva el dato de T0 con su fuente y hora, muestra aviso de degradación y no lo etiqueta como recién actualizado.
- **Y** conserva ETA del plan con su hora de cálculo, sin presentarla como tráfico en vivo.

## Escenarios Gherkin — ruta infeliz

### M04 — Acceso o geometría inválidos

- **DADO** sesión ausente, rol sin detalle general o ID inexistente (casos separados).
- **CUANDO** solicita el detalle.
- **ENTONCES** recibe 401, 403 o 404 sin datos personales ajenos.
- **DADO** fixture defectuoso con coordenadas fuera de rango o secuencias duplicadas.
- **CUANDO** se valida la respuesta antes de representarla.
- **ENTONCES** se informa error de datos sin dibujar un recorrido inventado ni ocultar la incoherencia ordenando solo visualmente.

## Escenarios Gherkin — ruta de borde

### M05 — Sin historial de tráfico o sin proveedor de mapa

- **DADO** proveedor de tráfico caído sin caché previa.
- **CUANDO** abre la ruta.
- **ENTONCES** muestra SIN_DATOS, hora null y aviso; mantiene lista y ETA del plan identificada como estimación.
- **DADO** datos de ruta cargados y tiles inaccesibles.
- **CUANDO** usa la alternativa accesible.
- **ENTONCES** accede a la secuencia y alertas sin necesitar tiles.

### M06 — Estados de ejecución y compatibilidad

- **DADO** una ejecución EN_PROCESO, FALLIDA o COMPLETADA sin rutas (casos separados).
- **CUANDO** consulta la pantalla.
- **ENTONCES** distingue espera, fallo y vacío sin dibujar ejemplos; conserva `simulado` visible cuando corresponde.
- **Y** se verifica teclado, lector, foco, alertas no basadas solo en color y ancho 360 px en Chrome y Firefox.

## Trazabilidad y pruebas previstas

| Escenario | RF / RN / RNF | Prueba prevista |
|---|---|---|
| M01 | RF-008; RN-002, RN-006; RNF-005, RNF-009 | UI/E2E: misma ruta mapa/lista, secuencia, coordenadas, ETA, lector/teclado. |
| M02 | RF-008; RN-010 | Adaptador/API/UI: fuente, hora, unidades, riesgo distinto de bloqueo. |
| M03 | RF-008; RNF-006, cumplimiento transversal | Fallo controlado en T1 con caché T0, sin hora ficticia y sin perder el plan. |
| M04 | RF-001, RF-008; RN-002; RNF-003, RNF-004 | API cinco roles y UI con respuesta inválida, sin fugas. |
| M05 | RF-008; RNF-005, RNF-006 | Integración/UI: proveedor y tiles caídos, sin caché, lista utilizable. |
| M06 | RF-008; RNF-005, RNF-009 | Estados y matriz crítica de 15 pruebas compartida con US-006/009, con versiones exactas de ambos navegadores antes de ejecutar. |

## Cambios al contrato provisional

| Propuesta para Julio | Impacto |
|---|---|
| Añadir trafico, tramos y alertas | El contrato actual solo tiene geometría, paradas y ETA; no permite probar fuente, hora, congestión, degradación ni alertas. Ajustar ST-045, fixtures y UI tras ratificación. |
| Contrato de detalle y privacidad | Mantener solo Administrador/Operador en detalle; otras proyecciones conservan su matriz. Ratificar junto a R11, sin conceder acceso general al Conductor. |
| Lista equivalente y estados | Hace verificable accesibilidad y degradación sin inventar otro endpoint. `simulado` del contrato publicado se conserva visible. |

## Aprobación y entrega

BORRADOR hasta auditoría independiente y aprobación real de Julio, con enlace,
fecha y versión. No se asume aprobado por tener fixtures ni por aprobar otra
historia. Publicar los cambios de contrato antes de implementar sus consumidores.

| Versión | Fecha | Cambio |
|---|---|---|
| 0.1.0 | 06/11/2026 | Escenarios M01–M06, alternativa accesible y propuesta de tráfico degradado. |

[← Volver al README principal](../../../README.md)
