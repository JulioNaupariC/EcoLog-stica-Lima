import json
import os
from pathlib import Path

from sqlalchemy import create_engine, text

results = json.loads(Path('/validation/browser-results.json').read_text())
assert results['passed'] is True
operations = []
for browser in results['browsers']:
    operations.append(browser['online']['operationId'])
    operations.extend(row['operationId'] for row in browser['rounds'])
assert len(operations) == len(set(operations)) == 22
engine = create_engine(os.environ['DATABASE_URL'])
checks = []
with engine.connect() as connection:
    connection.execute(text('SET TRANSACTION READ ONLY'))
    postgres = connection.scalar(text('SHOW server_version'))
    postgis = connection.scalar(text('SELECT PostGIS_Version()'))
    for operation in operations:
        rows = connection.execute(text('SELECT incidencia_id FROM incidencia WHERE operation_id = CAST(:operation AS uuid)'), {'operation': operation}).scalars().all()
        assert len(rows) == 1
        audits = connection.scalar(text("SELECT count(*) FROM auditoria WHERE entidad_id = :id AND accion = 'INCIDENCIA_REGISTRADA'"), {'id': str(rows[0])})
        assert audits == 1
        checks.append({'operationId': operation, 'incidenceId': str(rows[0]), 'incidences': 1, 'creationAudits': 1})
payload = {'passed': True, 'postgresql': postgres, 'postgis': postgis, 'operations': checks, 'total': len(checks)}
Path('/evidence/persistence.json').write_text(json.dumps(payload, indent=2) + '\n')
print('ECL-76: 22 operaciones únicas; una incidencia y una auditoría de alta por operación.')
engine.dispose()
