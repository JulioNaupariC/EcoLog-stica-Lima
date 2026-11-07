# ECL-97 / ECL-12 — Reglas y BDD de US-006: rutas optimizadas

> **Estado: BORRADOR.** Requiere ratificación de Julio antes de la implementación
> dependiente (acción A4). Define resultados esperados y pruebas previstas;
> no acredita ejecución ni aprobación. Las precisiones propuestas no modifican
> los requisitos aprobados.

| Metadato | Valor |
|---|---|
| Versión | 0.1.1 |
| Fecha | 06/11/2026, America/Lima |
| Autor | Frank Roy Yupanqui Acevedo — @FrankRoyYA |
| Ticket | [ECL-97](https://continental-team-il84x39k.atlassian.net/browse/ECL-97), 3 SP para las cuatro BDD |
| Historia | [ECL-12 / US-006](https://continental-team-il84x39k.atlassian.net/browse/ECL-12) |
| Revisor y aprobación | Julio Armando Naupari Camarena — @JulioNaupariC; pendiente |
| Dependientes | Modelo y optimizador de Antony; mapa de José; dashboard de Giancarlo |

## Fuentes y alcance

- [RF-006 y RF-001](<../../01 Inicio/06. Requisitos funcionales V_1_1_0.md>).
- [RN-002 a RN-013 y gestión de parámetros](<../../01 Inicio/09. Reglas de negocio V_1_1_0.md>).
- [RNF-001, RNF-003, RNF-004, RNF-009 y RNF-011](<../../01 Inicio/07. Requisitos no funcionales V_1_2_0.md>).
- [Modelo objetivo: optimizacion, ruta, parada_ruta y parametro](<../../01 Inicio/11. Base de datos V_1_1_0.md>).
- [Matriz de roles aprobada](<../../01 Inicio/08. Usuarios V_1_0_0.md>),
  [contrato ST-045](../../../backend/README.md#api-de-rutas-contrato-con-datos-simulados--ecl-94--st-045),
  [esquemas provisionales](../../../backend/app/schemas/rutas.py) y
  [límites del spike ECL-93](../../../backend/evidencias/ECL-93/README.md).
- Contrato proporcionado por Frank para ECL-97. Ante diferencias con la matriz
  o ST-045, la sección de cambios pide decisión expresa; no se adapta el RF al código.

Alcance: reglas, escenarios y trazabilidad. No implementa endpoints, worker,
migraciones, UI ni modifica fixtures. El spike ECL-93 y el contrato simulado ST-045
ya están integrados en main mediante #88 y #89; no se retrofecha A4 ni se los
presenta como implementación funcional aprobada de US-006. El índice Sprint 04
ya existe tras #90; el glosario sigue a cargo de ECL-99.
Estas BDD se mantienen en Planificación, como exige el ticket.

## Reglas de negocio y contrato candidato

### Entradas, permisos y estados

- Sesión por cookie. El contrato de Frank propone Administrador y Operador
  para `POST /optimizaciones`, permiso candidato `rutas.optimizar`;
  Analista, Conductor y Auditor reciben 403. Sin sesión, 401.
  La matriz vigente solo concede `optimizaciones.ejecutar` al Operador:
  **la habilitación del Administrador requiere ratificación expresa y control
  de cambios de permisos antes de aprobar esta BDD** (R11).
- `fecha_operacion` es una fecha ISO válida. Listas omitidas seleccionan todos
  los pedidos PENDIENTE de la fecha y vehículos ACTIVO elegibles. Propuesta:
  omitir o enviar `null` equivale; `[]`, UUID inválidos, duplicados y campos
  extra reciben 422. De 1 a 150 pedidos y de 1 a 15 vehículos; si la selección
  automática supera esos máximos, 422, sin truncar silenciosamente.
- Se valida la selección explícita contra registros existentes y elegibilidad;
  no se ignoran IDs desconocidos, pedidos de otra fecha o no PENDIENTE.
  Campos de error identifican el problema sin repetir los valores enviados.
- Sin pedidos o vehículos utilizables: 422 y ninguna ejecución creada. Si hay
  vehículos utilizables y un pedido válido no puede asignarse, el resultado
  informa la causa; no se transforma esa inviabilidad individual en error global.
- `202` crea ejecución `EN_PROCESO`; se consulta con
  `GET /optimizaciones/{optimizacion_id}`. En MVP síncrono se admite `201`
  solo con estado `COMPLETADA`; nunca se anuncia éxito antes de persistir.
  Transiciones: `EN_PROCESO → COMPLETADA | FALLIDA`; estados finales inmutables.
  En proceso: resumen `null`, rutas y no asignados vacíos. Fallida: error seguro,
  sin trazas ni solución parcial publicada como completa. ID inexistente: 404.
- Detalle para Administrador/Operador. Listado paginado, `page≥1`,
  `1≤page_size≤100` (20 por defecto), filtro de fecha, orden por
  `solicitada_en DESC` e ID ascendente en empate. Página vacía: 200 con total real.
  Lectura agregada de Analista/Auditor se conserva según matriz; no expone
  nombres de conductores fuera del detalle autorizado. Toda llamada se audita
  sin cuerpos, coordenadas, nombres, DNI ni contacto en el detalle de auditoría.

### Restricciones duras y blandas

| Tipo | Condición verificable |
|---|---|
| Dura: capacidad (RN-003) | En cada ruta, suma de pesos ≤ capacidad_kg y suma de volúmenes ≤ capacidad_m3 del vehículo; igualdad válida. No se divide un pedido ni se duplica su asignación. |
| Dura: recursos (RN-004) | No usar vehículos inactivos, averiados o con restricción de placa aplicable. No solapar rutas del mismo vehículo ni asignaciones incompatibles del mismo conductor. |
| Dura: ventana (RN-006) | Ventana con inicio < fin; propuesta de aceptación: ETA de inicio de servicio dentro de ambos límites, inclusivos. Esperar antes del inicio es válido si el resto de restricciones se cumple. |
| Dura: conducción (RN-005) | Máximo 8 h acumuladas de conducción y 4 h continuas; antes de seguir tras 4 h continuas, descanso de al menos 1 h. El descanso no aumenta las 8 h permitidas de conducción. Servicio, espera y descanso se distinguen de conducción y quedan dentro de la disponibilidad del conductor. |
| Dura: ubicación y vías | WGS84, latitud [-90,90], longitud [-180,180], finitas. Una referencia verificable debe resolverse a coordenadas antes de calcular; ausencia de posición resoluble produce SIN_UBICACION. Un bloqueo configurado por Administrador excluye la vía; una alerta no validada no la bloquea. |
| Blanda: objetivo (RF-006/RN-007) | Distancia, CO₂, costo, prioridad y riesgo vial participan según parámetros versionados, con unidades/pesos publicados. Mayor penalización de perecederos/express conforme a RN-007. Ninguna mejora del objetivo permite violar una restricción dura. |
| Blanda: riesgo (RN-010) | Alerta configurada aumenta costo; solo el bloqueo explícito prohíbe tránsito. Tráfico y restricciones usados conservan fuente y hora; datos sintéticos no se etiquetan como tráfico real. |

RN-007 habla de penalización por tardanza y RF-006 exige ventanas factibles.
Para este contrato las ventanas permanecen duras: no se ofrece entrega tardía
como factible. El peso por omisión/prioridad y el tratamiento de tardanza fuera
de esta solución requieren ratificación; no se afirma que ambos sean equivalentes.

Una ruta con `conductor: null` y
`motivo_sin_conductor: SIN_CONDUCTOR_ELEGIBLE` es propuesta sin asignación humana
(ECL-79); no habilita despacho ni acredita RN-005 de un conductor real.
Debe poder distinguirse de una ruta asignada y operable.

### Métricas y referencia secuencial

Se conserva `parametros_version` de cada ejecución y la instantánea de flota,
pedidos y matriz de distancias/tiempos usada. Un cambio de parámetros no
reescribe resultados históricos.

Referencia propuesta, coherente con el spike: mismos pedidos efectivamente
atendidos, en orden de registro (desempate por ID), flota en orden estable
documentado y depósito de la ejecución; se carga hasta capacidad y se retorna
al depósito antes del siguiente viaje. La secuencial no optimiza ni respeta
necesariamente ventanas: mostrar su cobertura y límite evita equipararla con
una alternativa factible. No comparar conjuntos de pedidos diferentes ni
presentar Haversine ajustada como distancia vial medida.

| Magnitud | Cálculo de referencia |
|---|---|
| Distancia (km) | Suma de tramos incluyendo salida y retorno al depósito. |
| Combustible (L) | Σ distancia_km / rendimiento_km_l de cada vehículo. |
| CO₂ (kg) | Σ distancia_km × factor_co2_kg_km del vehículo (RN-013). |
| Costo (S/) | Combustible por precio en S/L, más distancia por mantenimiento en S/km (RN-011/RN-012); otros componentes solo con definición versionada aprobada. |
| Ahorro absoluto | Secuencial − optimizada, por magnitud. |
| Ahorro porcentual | 100 × (secuencial − optimizada) / secuencial. Si base = 0, `null` y «No calculable»; no dividir por cero ni inventar 0 %. Ahorros negativos se conservan. |

El precio inicial de RN-011 está en S/ por galón; no multiplicarlo por litros
sin conversión. La unidad de galón y su factor deben quedar en parámetros
versionados antes de aprobar cálculos; no se supone un factor no ratificado.
RNF-011: 20 cálculos de referencia con diferencia absoluta ≤0,01 por resultado,
sin redondeos intermedios que cambien la comparación. No se exige un ahorro
mínimo universal: la solución factible y las métricas se verifican por separado.

### Motivos de no asignación

Cada pedido seleccionado aparece una vez entre asignados y no asignados;
ambos conjuntos son disjuntos. `COMPLETADA` puede contener todos los pedidos
no asignados si no existe solución factible individual; se explica cada caso.

| Motivo candidato | Condición |
|---|---|
| SIN_UBICACION | No se obtiene posición verificable a partir de coordenadas o referencia. |
| EXCEDE_CAPACIDAD | No cabe en kg o m³ en ningún vehículo elegible, incluso vacío. |
| VENTANA_INVIABLE | Ubicación y capacidad válidas, pero no se puede atender en ventana. |
| SIN_VEHICULO | No queda recurso compatible para el pedido dentro de una selección global utilizable. |
| JORNADA_INVIABLE (propuesto) | La conducción, disponibilidad o descanso impiden una asignación que sería posible sin esa restricción. |
| RESTRICCION_VIAL (propuesto) | Bloqueo o restricción vial configurada impide el acceso compatible. |

Si concurren causas se propone evaluar en el orden de esta tabla, con
ubicación/capacidad antes del solver y clasificación comprobable después.
Agotar el tiempo de búsqueda no prueba inviabilidad de ventana: si no se puede
justificar un motivo, publicar `FALLIDA` con error seguro de cálculo, sin
inventar una causa ni declarar óptimo global.

## Datos y medición previstos

Solo datos sintéticos. Conjunto dorado: exactamente 150 pedidos y 15 vehículos,
depósito, semillas, ventanas, tiempos de servicio, conductores elegibles y
parámetros fijados, con hash del dataset y versión de herramientas.
Verificador independiente recalcula capacidad, tiempos, descansos y exclusividad.
RNF-001 se acredita con P95 ≤45 s en **30 ejecuciones** de carga normal; no por
una sola corrida ni por el tiempo hasta recibir 202. Medir desde solicitud
válida aceptada hasta resultado consultable, incluyendo espera de cola si existe;
registrar también `duracion_s` del cálculo y método P95 (rango más próximo,
posición ceil(0,95 × 30) = 29). Esta delimitación es propuesta para Julio.

## Escenarios Gherkin — ruta dorada

### R01 — Optimizar 150 pedidos con 15 vehículos

- **DADO** Operador autenticado, dataset dorado y parámetros versionados.
- **CUANDO** solicita optimización y consulta hasta un estado final.
- **ENTONCES** obtiene resultado persistido con cada pedido asignado una vez o con causa, rutas verificadas sin violaciones y métricas frente a la secuencial sobre el mismo conjunto atendido.
- **Y** se ejecuta la campaña de 30 corridas; P95 ≤45 s con entorno, datos y tiempos documentados, sin presentar el 202 como fin del cálculo.

## Escenarios Gherkin — ruta feliz

### R02 — Entrada explícita y selección automática

- **DADO** pedidos PENDIENTE de dos fechas y vehículos activos/inactivos.
- **CUANDO** envía listas válidas y luego omite las listas en otra ejecución.
- **ENTONCES** la primera usa exactamente la selección autorizada y la segunda solo pedidos de la fecha y vehículos elegibles; no trunca ni mezcla otras fechas.

### R03 — Capacidad, ventanas y prioridades

- **DADO** pesos y volúmenes distintos, ventanas, prioridades y parámetros de penalización fijados.
- **CUANDO** optimiza un caso con alternativas factibles y otro con capacidad limitada.
- **ENTONCES** cada carga y ETA respeta límites duros y la selección refleja las penalizaciones aprobadas sin convertir la prioridad en permiso de tardanza.

### R04 — Comparación reproducible y parámetros históricos

- **DADO** un fixture de 100 km optimizados, 120 km secuenciales, rendimiento 10 km/L, factor 0,2 kg/km, precio sintético 4 S/L y mantenimiento 1,2 S/km.
- **CUANDO** calcula métricas y luego cambia los parámetros vigentes para nuevas ejecuciones.
- **ENTONCES** el fixture conserva 10/12 L, 20/24 kg CO₂ y 160/192 S/ (optimizada/secuencial), y ahorro 16,666… % antes del redondeo de presentación.
- **Y** el resultado histórico conserva su versión; se amplía a 20 cálculos con error absoluto ≤0,01. Son expectativas de prueba, no mediciones reales.

## Escenarios Gherkin — ruta infeliz

### R05 — Pedido excede toda la flota

- **DADO** flota utilizable y un pedido mayor que toda capacidad en kg; repetir excediendo solo m³.
- **CUANDO** optimiza junto con pedidos factibles.
- **ENTONCES** ese pedido queda EXCEDE_CAPACIDAD y los demás conservan rutas válidas, sin partir ni perder el pedido.

### R06 — Entradas o acceso inválidos

- **DADO** UUID inválido/repetido/inexistente, lista vacía o excesiva, fecha inválida, pedido no elegible o campo extra (cada caso separado).
- **CUANDO** solicita optimización.
- **ENTONCES** recibe 422 sin eco de valores ni ejecución parcial.
- **DADO** sesión ausente o rol no autorizado, con entrada válida.
- **CUANDO** intenta la misma operación o consulta protegida.
- **ENTONCES** recibe 401 o 403 según corresponda, sin datos ni cálculo. Administrador se prueba conforme a la decisión R11, no conforme al comportamiento provisional.

### R07 — Restricciones y fallo de cálculo

- **DADO** casos aislados de ventana imposible, jornada inviable, vía bloqueada y recurso incompatible, y otro caso de fallo interno del motor.
- **CUANDO** termina la ejecución.
- **ENTONCES** cada caso de negocio informa el motivo definido sin violaciones; el fallo interno termina FALLIDA sin trazas, valores enviados ni métricas ficticias.

## Escenarios Gherkin — ruta de borde

### R08 — Sin vehículos, sin pedidos o sin ubicación

- **DADO** cero vehículos elegibles o cero pedidos elegibles (casos separados).
- **CUANDO** solicita optimización.
- **ENTONCES** recibe 422 con motivo y sin ejecución.
- **DADO** flota utilizable y pedido con referencia no resoluble y sin coordenadas.
- **CUANDO** optimiza.
- **ENTONCES** recibe resultado con SIN_UBICACION para ese pedido, sin fabricar una posición ni modificar el pedido original.

### R09 — Igualdad de límites y descanso

- **DADO** carga igual a kg/m³ máximos, ETA igual a inicio/fin de ventana y 8 h de conducción acumulada; repetir con exceso mínimo de cada límite.
- **CUANDO** optimiza y verifica el cronograma.
- **ENTONCES** admite igualdades y rechaza excesos; conducir después de 4 h continuas requiere 1 h de descanso previa, y ni espera ni servicio se presentan como descanso automáticamente.

### R10 — Estados, paginación y ahorro no calculable

- **DADO** ejecuciones EN_PROCESO, COMPLETADA y FALLIDA, y un fixture con base secuencial cero.
- **CUANDO** consulta detalle, páginas válidas/vacías, filtros, ID inexistente y paginación inválida.
- **ENTONCES** respeta proyecciones y códigos definidos, orden estable y total real; la base cero muestra ahorro porcentual null y la base con empeoramiento conserva el signo negativo.

### R11 — Ratificar la matriz de permisos

- **DADO** matriz vigente y contrato candidato con diferencias de rol/permiso.
- **CUANDO** Julio decide los permisos de optimizar y consultar cada proyección.
- **ENTONCES** se registra la decisión y su control de cambios; después se parametrizan pruebas de los cinco roles para todos los endpoints, sin ampliar acceso por omisión.

## Trazabilidad escenario ↔ requisito ↔ prueba prevista

| Escenario | RF / RN / RNF | Prueba prevista |
|---|---|---|
| R01 | RF-006; RN-003–009; RNF-001 | Integración con BD y motor reales, verificador independiente, 30 mediciones P95. |
| R02 | RF-004, RF-006; RN-004, RN-006 | API/BD: selección exacta, fecha, estados y límites automáticos. |
| R03 | RF-006; RN-003, RN-006, RN-007 | Unitarias del dominio y solver: pesos de objetivo y verificación de restricciones. |
| R04 | RF-006, RF-009; RN-011–013; RNF-011 | 20 referencias independientes y persistencia de versión histórica. |
| R05 | RF-006; RN-003, RN-009 | Integración: exceso de kg y de m³ por separado, resto intacto. |
| R06 | RF-001, RF-006; RN-002; RNF-003, RNF-004 | API: validación y matriz RBAC; inspección de errores y auditoría. |
| R07 | RF-006; RN-004–010 | Dominio/API: cada causa, fallo interno y no publicación parcial. |
| R08 | RF-006; RN-006, RN-009 | API/BD: conjuntos vacíos y localización resoluble/no resoluble. |
| R09 | RF-006; RN-003, RN-005, RN-006 | Límites inclusivos y exceso; conducción, servicio, espera y descanso separados. |
| R10 | RF-006; RN-002; RNF-011 | API/UI: estados, paginación, null y ahorro negativo. |
| R11 | RF-001, RF-006; RN-002; RNF-003, RNF-004 | Revisión de aprobación y matriz API de los cinco roles. |

### Matriz de compatibilidad prevista — RNF-009

Cada una de estas 15 pruebas debe aprobarse en Chrome y Firefox; registrar
versiones exactas y entorno antes de ejecutar, no elegirlas retrospectivamente.
Son flujos observables de UI/API de US-006/008/009, no mediciones ya realizadas.

| Caso | Flujo y escenarios de referencia |
|---|---|
| B01 | Solicitar y consultar la optimización dorada (R01). |
| B02 | Selección explícita y automática con fecha (R02). |
| B03 | Validaciones y conservación de filtros tras 422 (R06). |
| B04 | Sesión vencida y rol sin permiso sin exposición de datos (R06/M04/D04). |
| B05 | Resultado con pedido no asignado y causa (R05/R08). |
| B06 | Estados EN_PROCESO, COMPLETADA y FALLIDA (R10/M06). |
| B07 | Listado paginado, filtro y página vacía (R10). |
| B08 | Trazado, secuencia y ETA en Lima (M01). |
| B09 | Lista alternativa con teclado y lector (M01/M06). |
| B10 | Alertas y bloqueo distinguibles sin depender solo del color (M02). |
| B11 | Tráfico caído con último dato y hora conservados (M03). |
| B12 | Sin caché de tráfico o con tiles caídos (M05). |
| B13 | Dashboard con unidades, periodo y agregado de referencia (D01). |
| B14 | Dashboard sin datos, cero real y porcentaje no calculable (D06). |
| B15 | Cambio de periodo, filtro inválido y límites inclusivos (D04/D07). |

## Cambios al contrato provisional

Posición técnica de Antony del 06/11/2026, 19:18 (America/Lima), en su
[comentario de backend](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/91#pullrequestreview-5808785030).
Es una propuesta para Julio; no ratifica decisiones ni modifica las reglas.

| Decisión pendiente de Julio | Diferencia / impacto para ST-045 y dependientes | Posición técnica (backend) |
|---|---|---|
| RBAC (R11) | El prompt propone Administrador/Operador y `rutas.optimizar`; matriz/ST-045 solo Operador y `optimizaciones.ejecutar`. No cambiar matriz desde esta BDD. Mantener consultas agregadas de Analista/Auditor según matriz; resolver detalle por rol explícitamente. | Antony propone mantener la matriz vigente: solo el Operador optimiza, como en #89. |
| Estructura de métricas | ST-045 ya agrupa `resumen.optimizada` y `ruta.metricas`, añade `simulado`, timestamps, carga y descansos. Se propone conservar esa estructura publicada en lugar de campos planos del prompt, sin cambiar las cuatro magnitudes exigidas. | Acuerdo técnico general con las propuestas; no formula una decisión específica sobre la estructura. |
| Motivos adicionales | Proponer JORNADA_INVIABLE y RESTRICCION_VIAL para RN-005/RN-009, ausentes del enum actual. ST-045 debe ajustar OpenAPI y fixtures tras ratificación. | Propone incorporar JORNADA_INVIABLE en este sprint y diferir RESTRICCION_VIAL hasta que exista el registro de bloqueos. |
| Porcentajes | Admitir null con base cero y negativos sin truncar; el límite actual [-100,100] rechaza empeoramientos mayores al 100 %. Propuesta: límite superior 100, sin piso fijo para ahorro negativo. | Indica que puede ajustar ST-045 con pct nulo y negativos en este sprint. |
| Tiempo y precisión | Ratificar medición end-to-end además de duracion_s, ETA inclusiva de inicio de servicio, reglas de clasificación y conversión del precio por galón. | Sin precisión específica en el comentario; pendiente de decisión de Julio. |
| Jornada | El spike cuenta servicio/espera como conducción, una simplificación técnica; esta BDD distingue los conceptos de RN-005. No se modifica RN-005 para acomodar el spike. | Indica que el spike cuenta servicio y espera como conducción y es más estricto: puede dejar pedidos sin asignar. Propone implementar la distinción de la BDD en ST-047. |

## Aprobación y entrega

Julio debe resolver las decisiones anteriores y aprobar esta historia con fecha,
versión y enlace a revisión reales. Solo entonces se cambia BORRADOR a APROBADO
y se entrega a implementadores; cualquier cambio posterior requiere revisión
del nuevo commit. La auditoría independiente precede a Ready for Review según
la política del repositorio. No se comunica al equipo ni se modifica Jira desde este documento.

| Versión | Fecha | Cambio |
|---|---|---|
| 0.1.0 | 06/11/2026 | Borrador ECL-97: reglas, contrato candidato, escenarios R01–R11 y decisiones para ratificación. |
| 0.1.1 | 06/11/2026 | Incorpora la propuesta técnica de backend y navegación del Sprint 4; reglas sin cambios y aprobación de Julio pendiente. |

[Mapa US-008](ECL-14-US-008-mapa.md) · [Dashboard US-009](ECL-15-US-009-dashboard.md) ·
[Reoptimización US-007](ECL-13-US-007-reoptimizacion.md)

[Índice del Sprint 4](<../../03 Implementación/Sprint 04/README.md>) ·
[← Volver al README principal](../../../README.md)
