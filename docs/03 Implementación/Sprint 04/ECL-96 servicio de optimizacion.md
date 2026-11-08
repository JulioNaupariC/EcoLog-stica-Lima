# ECL-96 (ST-047) — Servicio de optimización y endpoints de rutas

Alcance de esta entrega (PR 1 de 2): `POST /optimizaciones`,
`GET /optimizaciones` y `GET /optimizaciones/{optimizacion_id}` dejan de usar
datos simulados y resuelven con el motor VRPTW de ST-044 sobre los pedidos y
vehículos guardados. El contrato publicado en ST-045 (ECL-94) no cambia de
forma; solo cambian el código de estado del `POST` (201) y `simulado: false`.
Fuente de reglas: [BDD US-006 v1.0.0](<../../02 Planificación/BDD/ECL-12-US-006-rutas-optimizadas.md>).

`GET /indicadores/sostenibilidad` sigue simulado (US-009) y conserva la cabecera
`X-Datos-Simulados: true`.

## Contrato

| Endpoint | Permiso (matriz RBAC sin cambios) | Respuestas |
|---|---|---|
| `POST /optimizaciones` | `optimizaciones.ejecutar` (Operador) | 201, 401, 403, 422, 503 |
| `GET /optimizaciones` | `optimizaciones.consultar` general | 200, 401, 403, 422, 503 |
| `GET /optimizaciones/{id}` | `rutas.consultar` general | 200, 401, 403, 404, 422, 503 |

- **201** solo cuando la corrida quedó `COMPLETADA` y guardada con todas sus
  rutas, paradas y pedidos no asignados en una sola transacción. Nunca se
  anuncia éxito antes de persistir.
- **422** por selección no utilizable: `{"detail": {"campo", "motivo"}}`, sin
  repetir identificadores ni valores enviados. No se crea corrida.
- **503** con `{"detail": {"optimizacion_id", "estado": "FALLIDA", "motivo"}}`
  si el cálculo falló: la corrida queda `FALLIDA` con el mensaje seguro
  «No se pudo calcular la solución de rutas» y puede consultarse. Una caída del
  almacenamiento responde `{"detail": "Servicio no disponible"}`.
- El actor sale de la sesión; nunca del cuerpo.
- Fechas y horas en `America/Lima` con desfase; listado por `solicitada_en`
  descendente con desempate por ID, `page_size` 1–100 (20 por defecto, BDD).

## Selección (decisión 3 del BDD)

| Caso | Resultado |
|---|---|
| `pedido_ids` omitido o `null` | Pedidos `PENDIENTE` cuya ventana empieza en la fecha (medianoche a medianoche de Lima) |
| `vehiculo_ids` omitido o `null` | Vehículos `ACTIVO` |
| Lista vacía, repetidos o campos extra | 422 del esquema |
| ID inexistente, de otra fecha, no `PENDIENTE` o vehículo no `ACTIVO` | 422 `pedido_ids` / `vehiculo_ids` |
| Selección automática sin pedidos o sin vehículos | 422 |
| Más de 150 pedidos o 15 vehículos en la selección automática | 422; nunca se trunca en silencio |
| Sin versión de parámetros vigente (EN-008) | 422 `parametros` |

Los estados de los pedidos no se modifican: el despacho es un paso posterior.

## Cálculo

1. Las ventanas se convierten a minutos desde la medianoche de Lima de la
   fecha; el depósito y el límite de búsqueda salen de la configuración
   (`DEPOSITO_LATITUD`, `DEPOSITO_LONGITUD`, `OPTIMIZACION_TIEMPO_LIMITE_S`,
   valores por defecto en `backend/.env.example`).
2. El motor devuelve rutas y no asignados con motivo (RN-009). Si no encuentra
   asignación (`SIN_SOLUCION`) o falla, la corrida es `FALLIDA`: el límite de
   tiempo no prueba que un pedido sea inviable.
3. Costo por ruta con la versión vigente de parámetros: litros → galones con
   `LITROS_POR_GALON`, por `PRECIO_COMBUSTIBLE_GALON`, más km por
   `COSTO_MANTENIMIENTO_KM`. El costo secuencial usa la misma versión, y la
   corrida guarda `parametros_version`.
4. Ahorros exactos, con signo, `null` cuando la base secuencial es 0; ningún
   redondeo intermedio.
5. Conductores (ECL-79): en orden de salida, cada ruta toma el primer conductor
   `ACTIVO` con cuenta `CONDUCTOR` activa, licencia vigente en la fecha y
   disponibilidad que cubre la ruta completa; cada conductor maneja una sola
   ruta por corrida. Sin candidato: `SIN_CONDUCTOR_ELEGIBLE`.
6. `cumplimiento_ventanas_pct`: paradas con ETA dentro de su ventana sobre las
   asignadas (0 sin asignados).
7. `instantanea`: depósito, configuración, método de distancias, valores de
   parámetros, pedidos y datos técnicos de vehículos usados. No guarda datos
   personales.

### Limitación declarada del trazado

El trazado GeoJSON une depósito → paradas → depósito con segmentos rectos para
mostrar el orden de visita. No sigue la red vial; las distancias provienen de la
matriz del motor (Haversine × factor de desvío 1,35 a velocidad constante).

## Verificación

- Unitarias: `tests/unit/test_optimizaciones_service.py`,
  `tests/unit/test_optimizacion_repository.py`, `tests/unit/test_rutas_api.py`.
- Integración PostGIS: `tests/integration/test_optimizaciones.py`, incluye el
  escenario dorado de 150 pedidos y 15 vehículos de extremo a extremo con
  límite de búsqueda de 5 s y verificación de ventanas y capacidad.
- La campaña de 30 corridas para P95 de RNF-001 corresponde a EN-003; este
  ticket no la reporta como cumplida.

## Pendiente para el PR 2 de ST-047

- Cierre de ruta (`rutas.actualizar_estado`).
- Indicadores reales de sostenibilidad (US-009) sobre rutas cerradas.
- Distinción de conducción, servicio y espera de RN-005 y motivo
  `JORNADA_INVIABLE` cuando su causa esté verificada (requiere actualizar el
  enum del contrato y avisar a frontend).

[Índice del Sprint 4](README.md)

[← Volver al README principal](../../../README.md)
