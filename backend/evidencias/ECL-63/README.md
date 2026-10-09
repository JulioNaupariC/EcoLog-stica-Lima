# Evidencias ECL-63 / ST-037

Mediciones reales sobre datos sintéticos del 09/10/2026.
Consultar [el informe](../../INFORME_ST037.md) para resultados y límites.

Los tres planes JSON contienen SQL, origen y cinco ejecuciones completas.
resultados.json conserva versiones, índices, distribución y medianas.
fuentes.json registra base Git y SHA-256 de fuentes examinadas.
Dashboard y rutas no se registran como cero bytes o aprobados: siguen pendientes.

## Reproducción

Requiere dependencias backend y PostgreSQL/PostGIS de pruebas.
Crear una base NUEVA exclusiva llamada ecologistica_ecl63_queries_test y
configurar DATABASE_URL de forma privada para esa base, nunca producción.
Desde backend:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m alembic upgrade head
python scripts/measure_critical_queries.py --seed --output evidencias/ECL-63-repeticion
```

La siembra rechaza tablas cliente/pedido con registros. Para repetir los
SELECT sobre el dataset preparado, omitir --seed y usar otra carpeta de salida.
La herramienta no crea/elimina bases y rechaza otro nombre de base.
ANALYZE se ejecuta solo durante la siembra explícita; la medición es de
solo lectura. No se modifican índices. No publicar DATABASE_URL ni secretos.

La candidata no acredita un endpoint de listado, rutas ni dashboard.
No mide latencia HTTP o concurrencia. UUID y textos son sintéticos.
