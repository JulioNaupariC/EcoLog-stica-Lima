# ECL-97 / ECL-13 — Reglas y BDD de US-007: reoptimización

> **Estado: BORRADOR — EXTENSIÓN.** Puede aprobarse después de US-006,
> US-008 y US-009; no autoriza iniciar su implementación. Escenarios previstos,
> sin pruebas ejecutadas ni aprobación atribuida al equipo.

| Metadato | Valor |
|---|---|
| Versión | 0.1.1 |
| Fecha | 06/11/2026, America/Lima |
| Autor | Frank Roy Yupanqui Acevedo — @FrankRoyYA |
| Ticket / historia | [ECL-97](https://continental-team-il84x39k.atlassian.net/browse/ECL-97) / [ECL-13, US-007](https://continental-team-il84x39k.atlassian.net/browse/ECL-13) |
| Revisor y aprobación | Julio Armando Naupari Camarena — @JulioNaupariC; pendiente |
| Dependencias | US-006 aprobada, modelo de rutas/paradas, validación de incidencias y contrato de extensión ratificado |

## Fuentes y alcance

- [RF-007 y RF-001](<../../01 Inicio/06. Requisitos funcionales V_1_1_0.md>).
- [RN-002 a RN-010, RN-015, RN-019](<../../01 Inicio/09. Reglas de negocio V_1_1_0.md>).
- [RNF-002 a RNF-004 y RNF-009](<../../01 Inicio/07. Requisitos no funcionales V_1_2_0.md>).
- [Modelo ruta, parada_ruta, incidencia y optimizacion](<../../01 Inicio/11. Base de datos V_1_1_0.md>),
  [BDD de incidencias](ECL-72-ST-039-incidencias.md),
  [BDD US-006](ECL-12-US-006-rutas-optimizadas.md) y
  [matriz RBAC](<../../01 Inicio/08. Usuarios V_1_0_0.md>).

No implementa validación de incidencias, motor, persistencia ni endpoint.
ST-045 no publica reoptimización: toda interfaz nueva descrita abajo es
candidata y debe ratificarse antes de desarrollo. El mero reporte de un
Conductor no valida, bloquea ni reoptimiza automáticamente (RN-019).

## Reglas

1. Operador con `rutas.reoptimizar` solicita recálculo de jornada en curso;
   no se conceden permisos nuevos al Administrador por analogía. Sesión ausente
   401, otros roles 403 según matriz vigente. Consultas siguen las proyecciones
   autorizadas de US-006. Cualquier cambio RBAC exige decisión de Julio.
2. Eventos elegibles: pedido nuevo persistido, cancelación efectiva o incidencia
   validada de tráfico/avería. Un UUID enviado por cliente no acredita validación;
   el servidor comprueba estado, jornada y vínculo. Pendiente/descartada no dispara cálculo.
3. Solo se recalculan paradas PENDIENTE. ATENDIDA y NO_ATENDIDA son terminales,
   conservan resultado, horas, vínculo e historial. No resucitar cancelados ni
   asignarlos como pendientes. Viajes ya ejecutados no se vuelven a recorrer.
4. La instantánea incluye posición/tiempo operativo vigente y conducción
   acumulada, última pausa y disponibilidad; no reinicia la jornada al reoptimizar.
   Se conserva máximo 8 h conducción y descanso 1 h tras 4 h continuas, así como
   capacidad remanente de kg/m³, ventanas, bloqueo y recursos elegibles.
5. Avería validada excluye el vehículo afectado de nuevas asignaciones.
   Las entregas ya realizadas se conservan. Carga aún a bordo no se transfiere
   ficticiamente: la factibilidad de traslado debe estar confirmada por Operación;
   sin ella se informa recurso no disponible para esos pedidos.
6. Tráfico validado actualiza tiempos/costos; una alerta de riesgo no bloquea
   automáticamente. Solo bloqueo explícito de Administrador prohíbe la vía.
7. Si no hay alternativa factible, identificar pedidos afectados con motivos
   de US-006, sin omitirlos, incumplir restricciones ni borrar el plan previo.
   Con cero pendientes: propuesta 409 «Sin paradas pendientes», sin ejecución.
8. Crear nueva optimización enlazada a origen y versión del plan. No reescribir
   el original. Publicación de la propuesta no equivale a cambiar entregas
   ejecutadas ni despachar una ruta sin conductor elegible.
9. Propuesta de concurrencia: al publicar, verificar que la versión y estados
   de origen siguen vigentes. Si una parada fue atendida/cancelada mientras se
   calculaba, no sobrescribirla; fallar de forma controlada por conflicto y
   exigir nueva instantánea. No confirmar una propuesta obsoleta como vigente.
10. Cada solicitud registra actor, referencia, evento y transición sin payload,
    coordenadas, DNI, nombres ni trazas personales. Fallo de almacenamiento no
    confirma nueva versión; rollback conserva el último plan válido.

## Contrato de extensión candidato

Propuesta para decisión de Julio, **no endpoint disponible**:
`POST /optimizaciones/{origen_id}/reoptimizaciones`, sesión y permiso
`rutas.reoptimizar`. Cuerpo con `version_plan` y evento persistido
(`tipo_evento`: NUEVO_PEDIDO, CANCELACION o INCIDENCIA_VALIDADA;
`evento_id`: UUID). La representación/versionado del evento debe ratificarse
con su modelo, no se supone que esas entidades ya existan.

202 con `optimizacion_id`, estado EN_PROCESO y `solicitada_en`; consultar por
el GET de US-006. Nueva ejecución conserva origen, evento y versión usada.
Validación de forma/IDs inválidos: 422 sin eco; origen inexistente: 404;
evento no elegible, sin pendientes o versión obsoleta: 409 sin datos ajenos.
Fallo posterior al 202 se refleja como FALLIDA con código seguro y sin trazas.
Se propone evitar duplicar un mismo evento sobre la misma versión del plan:
reintento equivalente recupera el ID de la ejecución existente, sin reejecutar
ni duplicar su auditoría de creación. Ratificar alcance/duración de esa
unicidad y código de replay (propuesto 200) antes de implementar.

## Datos y rendimiento previstos

Jornada sintética con 50 pendientes como máximo, paradas terminales, tiempos
de conducción ya consumidos y una avería validada. Nuevos pedidos y cancelaciones
son registros persistidos de prueba, no simulación presentada como incidente real.
RNF-002: 30 ejecuciones con P95 ≤30 s (posición 29 por rango más próximo).
Propuesta: desde aceptación de solicitud válida hasta nueva solución consultable,
incluida cola; separar tiempo de cálculo. Un 202 rápido no acredita el límite.
Conservar dataset, semilla, versión de parámetros, entorno, resultados y verificación independiente.

## Escenarios Gherkin — ruta dorada

### X01 — Avería validada con 50 pendientes

- **DADO** Operador autenticado, jornada en curso, hasta 50 pedidos pendientes y avería validada con recurso afectado.
- **CUANDO** solicita recálculo y consulta el resultado.
- **ENTONCES** obtiene nueva ejecución enlazada a origen, sin el vehículo averiado en asignaciones nuevas, terminales intactas y pendientes asignados o con causa.
- **Y** en 30 corridas P95 ≤30 s, sin exceder restricciones de US-006 ni reiniciar tiempos de conducción.

## Escenarios Gherkin — ruta feliz

### X02 — Pedido nuevo y cancelación

- **DADO** un pedido nuevo priorizado; repetir con un pendiente cancelado efectivamente.
- **CUANDO** Operador solicita recálculo con el evento persistido.
- **ENTONCES** incorpora el nuevo pedido o excluye el cancelado, respectivamente, preservando progreso y parámetros trazables.

### X03 — Tráfico validado frente a riesgo y bloqueo

- **DADO** tiempos actualizados por tráfico validado y una alerta de riesgo sin bloqueo; repetir con bloqueo administrativo.
- **CUANDO** recalcula pendientes.
- **ENTONCES** aplica tiempos/costo de riesgo sin prohibir automáticamente; con bloqueo excluye el tramo, conserva hechos ejecutados y respeta capacidad, ventanas y descanso.

## Escenarios Gherkin — ruta infeliz

### X04 — Sin alternativa factible

- **DADO** avería validada sin recurso compatible, o conducción restante insuficiente.
- **CUANDO** termina el recálculo.
- **ENTONCES** informa los pedidos afectados y motivo explícito, sin transferir carga no autorizada ni modificar lo ya realizado.

### X05 — Incidencia no validada o acceso inválido

- **DADO** incidencia PENDIENTE_VALIDACION o DESCARTADA, origen/evento ajeno a la jornada o versión obsoleta.
- **CUANDO** solicita reoptimización.
- **ENTONCES** se rechaza según contrato candidato sin cálculo ni cambio del plan.
- **DADO** ausencia de sesión o cualquiera de los cuatro roles sin permiso.
- **CUANDO** solicita recálculo con cuerpo válido.
- **ENTONCES** recibe 401 o 403, sin filtrar el origen ni datos de conductores.

## Escenarios Gherkin — ruta de borde

### X06 — Sin pendientes, descanso consumido y concurrencia

- **DADO** jornada sin pendientes.
- **CUANDO** solicita recálculo.
- **ENTONCES** recibe el conflicto propuesto sin crear ejecución vacía.
- **DADO** conducción acumulada próxima a 4/8 h y una parada que se atiende durante el cálculo.
- **CUANDO** se intenta publicar el resultado.
- **ENTONCES** no reinicia la jornada ni sobrescribe la parada; detecta conflicto y conserva el estado vigente.

### X07 — Reintento y fallo transaccional

- **DADO** un evento sobre una versión ya solicitado, con respuesta perdida; repetir con dos solicitudes concurrentes.
- **CUANDO** reenvía el mismo evento y versión.
- **ENTONCES** recupera una sola ejecución con ID estable, sin doble alta ni auditoría duplicada, conforme al mecanismo ratificado.
- **DADO** fallo de persistencia o del motor.
- **CUANDO** procesa la solicitud.
- **ENTONCES** no confirma una versión inexistente, conserva el plan anterior y comunica error seguro.

## Trazabilidad y pruebas previstas

| Escenario | RF / RN / RNF | Prueba prevista |
|---|---|---|
| X01 | RF-007; RN-003–009; RNF-002 | Motor/BD reales, 30 corridas, verificador y comparación del historial. |
| X02 | RF-007; RN-007, RN-008 | Integración de alta/cancelación persistidas, conjuntos exactos y progreso. |
| X03 | RF-007, RF-008; RN-008, RN-010 | Adaptador/motor con tráfico, riesgo y bloqueo diferenciados. |
| X04 | RF-007; RN-003–005, RN-009 | Dominio/BD: recurso, carga remanente y causa de cada pendiente. |
| X05 | RF-001, RF-007, RF-012; RN-002, RN-008, RN-019; RNF-003, RNF-004 | API cinco roles, estado de evento, pertenencia y versión. |
| X06 | RF-007; RN-005, RN-008 | Reloj fijo y carrera entre atención/cancelación y publicación. |
| X07 | RF-007; RN-015; RNF-003 | Integración concurrente y fallos transaccionales, sin efectos duplicados. |

Los flujos de UI que se implementen se incluirán en una matriz RNF-009 de
15 pruebas críticas de Chrome/Firefox con versiones fijadas; no se afirma
compatibilidad de una extensión aún no implementada.

## Cambios al contrato provisional

Posición técnica de Antony del 06/11/2026, 19:18 (America/Lima), en su
[comentario de backend](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/91#pullrequestreview-5808785030).
Es una propuesta para Julio; no ratifica decisiones ni modifica las reglas.

| Propuesta pendiente de aprobación | Motivo / impacto | Posición técnica (backend) |
|---|---|---|
| Endpoint de recálculo, evento y version_plan | ST-045 actual no define US-007. Requiere contrato/OpenAPI y fixtures propios antes de UI. | Sin propuesta específica para el endpoint de extensión; US-007 sigue pendiente de Julio. |
| Vínculo a origen y control de versión | Evita sobrescribir progreso y publicar propuestas obsoletas; requiere modelo persistente y conflicto 409. | Sin precisión específica en el comentario. |
| Permiso rutas.reoptimizar de Operador | Sigue matriz vigente; no reutiliza por suposición el permiso de optimizar del prompt. | Propone mantener la matriz vigente; no formula una ampliación para reoptimización. |
| Reintento por evento/versión | Evita dobles recálculos tras pérdida de respuesta; alcance y código deben ratificarse. | Sin precisión específica en el comentario. |
| Presupuesto P95 y recursos remanentes | RNF-002 y RN-005 se verifican sobre contexto ya ejecutado, no jornada nueva. | Sobre RN-005, propone implementar en ST-047 la distinción de conducción, servicio y espera; no concreta medición RNF-002. |

## Aprobación y entrega

Julio puede aprobar esta extensión más tarde, sin retrasar las otras tres
historias. Se registra aprobación real por documento/versión y auditoría previa
a Ready for Review; mientras siga BORRADOR no desbloquea US-007.

| Versión | Fecha | Cambio |
|---|---|---|
| 0.1.0 | 06/11/2026 | Extensión candidata, reglas y escenarios X01–X07. |
| 0.1.1 | 06/11/2026 | Incorpora la propuesta técnica de backend y navegación del Sprint 4; reglas sin cambios y aprobación de Julio pendiente. |

[Índice del Sprint 4](<../../03 Implementación/Sprint 04/README.md>) ·
[← Volver al README principal](../../../README.md)
