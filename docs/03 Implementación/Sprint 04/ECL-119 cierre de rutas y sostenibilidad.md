# ECL-119 — Cierre de rutas y agregado real de sostenibilidad (US-009)

Backend que faltaba para que el dashboard de US-009 (frontend en #116, ECL-15)
muestre datos reales. Fuente de reglas:
[BDD US-009 v1.0.0](<../../02 Planificación/BDD/ECL-15-US-009-dashboard.md>),
ratificada por Julio el 07/11/2026.

## Decisión de alcance

El Operador registra el resultado de cada parada y cierra la ruta. La app del
conductor reporta entregas en `driver_stop_assignment`, pero hoy nada vincula
esas paradas con las rutas optimizadas (no existe el despacho ruta → conductor).
Conectar ambos flujos queda como **pendiente declarado**; no se infiere ningún
resultado a partir de la ETA.

## Endpoints

| Endpoint | Permiso | Respuestas |
|---|---|---|
| `PATCH /rutas/{ruta_id}/paradas/{parada_id}` | `rutas.actualizar_estado`, solo Operador | 200, 401, 403, 404, 409, 422, 503 |
| `POST /rutas/{ruta_id}/cierre` | `rutas.actualizar_estado`, solo Operador | 200, 401, 403, 404, 409, 503 |
| `GET /indicadores/sostenibilidad?desde&hasta` | `indicadores.consultar` general | 200, 401, 403, 422, 503 |

**Resultado de parada:**
- `{"estado": "ATENDIDA", "atendida_en": "<instante con zona>"}` o `{"estado": "NO_ATENDIDA"}`.
- ATENDIDA exige la hora real. No puede ser futura ni anterior a las 00:00 de
  Lima del día de la ruta: 422 con `{campo, motivo}`, sin eco.
- Un resultado final no se sobrescribe (409); repetir el mismo responde 200.
- El primer resultado pasa la ruta de PLANIFICADA a EN_CURSO. Una ruta cerrada
  no admite cambios (409).

**Cierre:**
- Exige todas las paradas en ATENDIDA o NO_ATENDIDA. Con pendientes responde
  409 «Faltan N paradas por registrar».
- Registra `cerrada_en` y audita `RUTA_CERRADA` con los conteos de paradas, sin
  datos personales, en la misma transacción.
- Repetir el cierre devuelve el ya guardado: no duplica la ruta ni la auditoría.
- La fila de la ruta se bloquea (`FOR UPDATE`) durante el registro y el cierre.
- Una optimización COMPLETADA o una ETA alcanzada no cierran la ruta.

## Agregado de sostenibilidad

- Solo rutas CERRADA con `cerrada_en` en [00:00 de `desde`, 00:00 del día
  siguiente a `hasta`) de Lima.
- Sumas de distancia, CO₂, combustible y costo de las rutas incluidas.
- **Referencia secuencial por ruta:** cada ruta guarda la práctica manual
  (pedidos en orden de registro, mismo vehículo) sobre exactamente sus pedidos.
  Así el ahorro compara la misma cobertura aunque solo se cierren algunas rutas
  de una optimización. El costo secuencial usa la misma versión de parámetros.
- Ahorro por magnitud = suma secuencial − suma optimizada, con signo.
  `pct` = ahorro de distancia sobre la suma secuencial; `null` con base 0.
- Cumplimiento = paradas ATENDIDA con `atendida_en` dentro de su ventana /
  todas las paradas terminales. NO_ATENDIDA cuenta como incumplida. Nunca usa ETA.
- `parametros_versiones`: versiones distintas usadas, ordenadas.
- Sin rutas cerradas: `con_datos: false` e indicadores `null`, nunca ceros.
- Si una ruta cerrada no tuviera los datos necesarios, responde 503 y no
  publica sumas parciales.
- `simulado: false`; ya no se envía `X-Datos-Simulados`. El aviso «Datos de
  prueba» del frontend desaparece solo.

## Base de datos

Migración `0018_cierre_rutas`:
- Columnas `ruta.secuencial_*`, nulas solo en rutas guardadas antes de 0018.
  Esas rutas no se pueden cerrar (409); hay que volver a optimizar la jornada.
- Índice parcial `ix_ruta_cerrada_en` sobre las rutas CERRADA.
- Acción de auditoría `RUTA_CERRADA`.
- El downgrade se niega si hay rutas cerradas o referencias guardadas.

Detalle en el [documento 11 v1.4.0](<../../01 Inicio/11. Base de datos V_1_4_0.md>).

## Verificación

- Unitarias: servicio y repositorio de cierre, API (roles, errores, validación
  sin eco) y referencia secuencial por ruta del motor.
- Integración PostGIS (`tests/integration/test_cierre_rutas.py`):
  - flujo completo optimizar → registrar → cerrar → dashboard;
  - cierre con pendientes rechazado (D05);
  - reintento sin duplicar la auditoría;
  - atención tardía cuenta como incumplida;
  - límites del periodo con cierres a las 00:00, al último instante del día y
    a las 00:00 del siguiente (D07);
  - rutas anteriores a 0018 y downgrade bloqueado.
- El caso de referencia D01 (150 km, ahorro 25 %, cumplimiento 75 %) se
  comprueba en las pruebas unitarias del servicio.

## Fuera de alcance

- **Equivalente ambiental:** pendiente de la decisión de Julio en la BDD. El
  frontend muestra «No disponible».
- **Pantalla del Operador para registrar resultados y cerrar rutas:** no
  existe en el frontend; hoy se usa la API (Swagger).
- **Vínculo con los reportes del conductor:** requiere el despacho ruta →
  conductor.
- **RNF-012 (≤ 250 000 bytes) y EXPLAIN con un dataset representativo (D08):**
  el agregado es un único objeto sin geometrías, pero la medición formal queda
  para la campaña de rendimiento.

[Índice del Sprint 4](README.md)

[← Volver al README principal](../../../README.md)
