# Evidencia ECL-54 / ST-028

Consultar [VALIDACION_ST028.md](../../VALIDACION_ST028.md).

api-tests.xml contiene 8 pruebas reales de HTTP integrado y PostgreSQL.
unit-tests.xml contiene 56 pruebas de preferencias.
resultados.json consolida resultados observados, trazabilidad y hashes.
Las credenciales y URLs privadas no se publican.

## Repetición desde backend

Configurar TEST_DATABASE_URL de una base de pruebas NUEVA y vacía con nombre
terminado en _test, separada de desarrollo. Nunca usar producción.
Las fixtures validan el destino, migran y revierten el esquema de esa base.

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m pytest tests/integration/test_preferencias_bdd.py tests/integration/test_preferencias_http_e2e.py -q
python -m pytest tests/unit/test_preferencias_api.py tests/unit/test_preferencias_schemas.py tests/unit/test_preferencias_service.py --cov=app.api.preferencias --cov=app.schemas.preferencias --cov=app.services.preferencias --cov-fail-under=80 -q
```

Para interfaz y regresión, ver
[la evidencia frontend](../../../frontend/evidencias/ECL-54/README.md).
P8 tiene una brecha documentada; aprobar pruebas de API no implica aprobar
el flujo de propuesta en el formulario ni el borrador BDD.
