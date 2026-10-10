# Evidencia ST-032

Campaña final: 2026-10-10 04:53 UTC; diez ciclos en Chrome 155.0.8059.40 y
Firefox 157.0. FastAPI y PostgreSQL/PostGIS reales en ambiente aislado, con
usuarios, pedidos y direcciones sintéticos.

- `resultados.json`: recarga offline, sincronización, reenvío del mismo UUID,
  cache público y aislamiento tras logout en cada navegador.
- `persistencia.json`: consulta SQL final, 20 asignaciones vinculadas a pedidos,
  20 reportes, versiones, migración y casos negativos 404/403.
- Ocho PNG: pendiente offline, confirmado tras reconexión, API no disponible
  y cuenta diferente sin datos de la anterior, en ambos navegadores.
- `api.log`, `browser.log`, `build.log`: registros de la ejecución final.
- `frontend-tests.xml`: 471 pruebas; `backend-tests.xml`: 560 pruebas.
- `backend-coverage.xml`: cobertura backend 93.17%; `frontend-coverage.json`:
  resumen de cobertura Vitest (líneas 97.23%).
- `integration-tests.xml`, `integration.log`: 2 pruebas sobre base nueva.
- `SHA256SUMS.txt`: inventario para comprobar integridad de los archivos.

El primer ciclo deja persistir el reporte y corta su respuesta. El reintento
conserva el UUID y recibe el mismo ACK. En el segundo se bloquea temporalmente
GET itinerario; la cola se recupera por temporizador sin otra señal online.
Cada operación se reenvía después para comprobar idempotencia. Los 20 UUID
coinciden exactamente con los de la consulta SQL final.

Las pruebas unitarias usan mocks; el E2E no sustituye respuestas API por datos
inventados. Playwright provoca las interrupciones de red/ACK. Algunos XML pueden
contener nombres de fixtures negativos, incluido un hash deliberadamente mal
formado; no son credenciales operativas. No se exportan contraseñas, cookies
ni tokens.

Incidencias del arnés resueltas antes de la ejecución final: pipes heredados de
`pg_ctl` en Windows, arranque Uvicorn como factory y permisos del temporal pytest
de otro usuario. Se corrigieron usando salida separada, factory correcta y
temporal propio. No se modificaron bases ajenas.

Reproducción y límites: [VALIDACION_ST032.md](../../VALIDACION_ST032.md).
La campaña local no acredita un SLA de producción.
