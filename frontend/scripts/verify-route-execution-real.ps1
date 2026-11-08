# ECL-120: disposable real API test. Never resets the user's demo database.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$dockerPath = Join-Path $env:LOCALAPPDATA 'Programs/DockerDesktop/resources/bin/docker.exe'
$nodePath = 'C:/Program Files/nodejs/node.exe'
$database = 'ecologistica_ecl120_' + (Get-Date -Format 'yyyyMMddHHmmss') + '_demo'
$container = 'ecologistica-ecl120-api-' + (Get-Date -Format 'yyyyMMddHHmmss')
$created = $false
$started = $false
$values = @{}
$saved = @{}
$keys = @('DATABASE_URL','APP_ENV','CORS_ALLOWED_ORIGINS','ECL120_TEST_PASSWORD','ECL120_ISOLATED_DATABASE',
  'SEED_DEMO_PASSWORD_ADMINISTRADOR','SEED_DEMO_PASSWORD_OPERADOR','SEED_DEMO_PASSWORD_CONDUCTOR','SEED_DEMO_PASSWORD_ANALISTA','SEED_DEMO_PASSWORD_AUDITOR')
function Invoke-TestDocker([string[]] $Arguments) {
  & $dockerPath @Arguments
  if ($LASTEXITCODE -ne 0) { throw 'Docker test step failed; stop without continuing.' }
}
Push-Location $repo
try {
  foreach ($key in $keys) { $saved[$key] = [Environment]::GetEnvironmentVariable($key, 'Process') }
  if (Get-NetTCPConnection -State Listen -LocalPort 8001 -ErrorAction SilentlyContinue) { throw 'Test port 8001 is occupied; no process was stopped.' }
  Get-Content .env | ForEach-Object { if ($_ -match '^(POSTGRES_USER|DATABASE_URL)=(.*)$') { $values[$matches[1]] = $matches[2] } }
  if ($values.DATABASE_URL -notmatch '^postgresql\+psycopg://[^/]+@db:5432/[^/]+$') { throw 'This test requires the local Compose database URL.' }
  $alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  $random = [Security.Cryptography.RandomNumberGenerator]::Create()
  $byte = New-Object byte[] 1
  $password = ''
  while ($password.Length -lt 24) { $random.GetBytes($byte); if ($byte[0] -lt 248) { $password += $alphabet[$byte[0] % 62] } }
  $random.Dispose()
  $env:ECL120_TEST_PASSWORD = $password
  foreach ($role in @('ADMINISTRADOR','OPERADOR','CONDUCTOR','ANALISTA','AUDITOR')) { [Environment]::SetEnvironmentVariable("SEED_DEMO_PASSWORD_$role", $password, 'Process') }
  $password = $null
  $env:DATABASE_URL = $values.DATABASE_URL -replace '/[^/]+$', ('/' + $database)
  $env:APP_ENV = 'development'
  $env:CORS_ALLOWED_ORIGINS = '["http://127.0.0.1:5184"]'
  $env:ECL120_ISOLATED_DATABASE = $database
  Invoke-TestDocker -Arguments @('compose','--env-file','.env','exec','-T','db','createdb','-U',$values.POSTGRES_USER,$database)
  $created = $true
  Invoke-TestDocker -Arguments @('compose','--env-file','.env','exec','-T','db','psql','-U',$values.POSTGRES_USER,'-d',$database,'-v','ON_ERROR_STOP=1','-c','CREATE EXTENSION postgis;')
  $network = 'ecologistica-lima-ecl29_default'
  $image = 'ecologistica-lima-ecl29-backend'
  Invoke-TestDocker -Arguments @('run','--rm','--network',$network,'-e','DATABASE_URL','-e','APP_ENV',$image,'python','-m','alembic','upgrade','head')
  Invoke-TestDocker -Arguments @('run','--rm','--network',$network,'-e','DATABASE_URL','-e','APP_ENV',
    '-e','SEED_DEMO_PASSWORD_ADMINISTRADOR','-e','SEED_DEMO_PASSWORD_OPERADOR','-e','SEED_DEMO_PASSWORD_CONDUCTOR','-e','SEED_DEMO_PASSWORD_ANALISTA','-e','SEED_DEMO_PASSWORD_AUDITOR',
    '-v',"${repo}/backend/scripts:/app/scripts:ro",$image,'python','-m','scripts.seed_demo')
  Invoke-TestDocker -Arguments @('run','--rm','-d','--name',$container,'--network',$network,'-p','127.0.0.1:8001:8000',
    '-e','DATABASE_URL','-e','APP_ENV','-e','CORS_ALLOWED_ORIGINS',$image)
  $started = $true
  $ready = $false
  for ($attempt = 0; $attempt -lt 20; $attempt++) {
    try { $ready = (Invoke-WebRequest 'http://127.0.0.1:8001/health/ready' -UseBasicParsing).StatusCode -eq 200 } catch { $ready = $false }
    if ($ready) { break }
    Start-Sleep -Seconds 1
  }
  if (-not $ready) { throw 'Isolated API did not become healthy.' }
  & $nodePath frontend/scripts/verify-route-execution-real.mjs
  if ($LASTEXITCODE -ne 0) { throw 'Real API browser verification failed.' }
  $audit = & $dockerPath compose --env-file .env exec -T db psql -U $values.POSTGRES_USER -d $database -Atc "SELECT count(*) FROM auditoria WHERE accion='RUTA_CERRADA'"
  if ($LASTEXITCODE -ne 0 -or $audit.Trim() -ne '1') { throw 'Expected one route closure audit, including after repeated close.' }
  Write-Output 'Real API verification passed; one RUTA_CERRADA event.'
} finally {
  if ($started) { & $dockerPath stop $container | Out-Null }
  if ($created -and $database -match '^ecologistica_ecl120_\d+_demo$') {
    & $dockerPath compose --env-file .env exec -T db dropdb -U $values.POSTGRES_USER --force $database
  }
  foreach ($key in $keys) { [Environment]::SetEnvironmentVariable($key, $saved[$key], 'Process') }
  $values.Clear(); $saved.Clear(); $password = $null
  Pop-Location
}
