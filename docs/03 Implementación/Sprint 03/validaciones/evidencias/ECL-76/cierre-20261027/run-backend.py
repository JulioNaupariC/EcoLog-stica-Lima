import os
import subprocess
import sys
from sqlalchemy.engine import make_url

url = make_url(os.environ['DATABASE_URL'])
assert url.database == 'ecologistica_ecl76_demo'
os.environ['TEST_DATABASE_URL'] = url.set(database='ecologistica_ecl76_test').render_as_string(hide_password=False)
commands = [
    ['python', '--version'],
    ['python', '-m', 'pip', 'check'],
    ['python', '-m', 'ruff', 'check', '.'],
    ['python', '-m', 'ruff', 'format', '--check', '.'],
    ['python', '-m', 'pytest', 'tests/unit', '-q', '-p', 'no:cacheprovider', '--cov=app', '--cov-fail-under=80', '--junitxml=/evidence/backend-unit.xml'],
    ['python', '-m', 'pytest', 'tests/integration', '-q', '-p', 'no:cacheprovider', '--junitxml=/evidence/backend-integration.xml'],
]
os.environ['COVERAGE_FILE'] = '/tmp/ecl76.coverage'
os.environ['RUFF_CACHE_DIR'] = '/tmp/ecl76-ruff'
for command in commands:
    print('RUN:', ' '.join(command), flush=True)
    result = subprocess.run(command)
    if result.returncode:
        sys.exit(result.returncode)
