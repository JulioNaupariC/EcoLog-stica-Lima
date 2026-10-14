# Evidencias ECL-25 / EN-007 — Inicio con indicadores agregados

Mediciones reales del 13/10/2026 (hora de Lima) sobre datos ficticios: 50 vehículos,
200 conductores y 30 días × 1 000 pedidos (30 000), generados con
[`indicadores_dataset.py`](../../scripts/indicadores_dataset.py) en la base
`ecologistica_ecl25_test` (PostgreSQL 16.15 + PostGIS 3.6.2, Python 3.12.10).
Consultar el [informe ST-037](<../../../docs/03 Implementación/Sprint 2/informes/INFORME_ST037.md>)
y la [validación ST-038](<../../../docs/03 Implementación/Sprint 2/validaciones/VALIDACION_ST038.md>).

| Archivo | Contenido |
|---|---|
| [medicion-antes.json](medicion-antes.json) | Inicio anterior: `GET /vehiculos` y `GET /conductores?page=1&page_size=100`, con las cifras que mostraba |
| [medicion-despues-sin-indice.json](medicion-despues-sin-indice.json) | `GET /indicadores/operacion` y planes de las tres consultas agregadas, antes de la migración 0011 |
| [medicion-despues.json](medicion-despues.json) | Lo mismo con la migración 0011 aplicada y `VACUUM ANALYZE pedido` |

Cada JSON registra estado HTTP, bytes UTF-8 del cuerpo, sentencias SQL por petición,
`Cache-Control`, mediana de 20 tiempos y, en la fase «después», el
`EXPLAIN (ANALYZE, BUFFERS)` de cada consulta (mediana de 5 ejecuciones y plan
completo de la última). La cuenta de medición usa una contraseña aleatoria que no se
imprime ni se guarda.

## Reproducción

Requiere las dependencias del backend y una base nueva llamada
`ecologistica_ecl25_test` con PostGIS. `DATABASE_URL` se configura de forma privada
para esa base; el instrumento rechaza cualquier otra. Desde `backend`:

```bash
export PYTHONPATH="$(pwd)"
python scripts/measure_home_payload.py --fase antes --seed --output evidencias/ECL-25-repeticion
python scripts/measure_home_payload.py --fase despues --output evidencias/ECL-25-repeticion
```

`--seed` aplica las migraciones y siembra el dataset sobre tablas vacías. Para medir
el estado sin índice, ejecutar antes `alembic downgrade 0010_extend_driver_audit_events`.
La regresión de CI está en
[`test_indicadores_operacion.py`](../../tests/integration/test_indicadores_operacion.py).

[← Volver al README principal](../../../README.md)
