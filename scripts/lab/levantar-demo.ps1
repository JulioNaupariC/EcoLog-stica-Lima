
# ECL-68 - Inicio de la demostracion local
# No necesita Docker ni permisos de administrador.

$ErrorActionPreference = "Stop"

$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent

if ($env:ECOLOGISTICA_DEMO_HOME) {
    $base = $env:ECOLOGISTICA_DEMO_HOME
} else {
    $base = Join-Path $env:LOCALAPPDATA "EcoLogisticaDemo"
}

$pg = Join-Path $base "tools\postgresql-16\pgsql"
$node = Join-Path $base "tools\node-v22.18.0-win-x64"
$datos = Join-Path $base "pgdata"
$run = Join-Path $base "run"
$backend = Join-Path $repo "backend"
$frontend = Join-Path $repo "frontend"

New-Item -ItemType Directory -Force -Path $run | Out-Null

function Verificar-Archivo($ruta) {
    if (-not (Test-Path -LiteralPath $ruta -PathType Leaf)) {
        throw "Falta archivo requerido: $ruta"
    }
}

function Puerto-Activo([int]$puerto) {
    try {
        $cliente = New-Object System.Net.Sockets.TcpClient
        try {
            $resultado = $cliente.BeginConnect("127.0.0.1", $puerto, $null, $null)

            if (-not $resultado.AsyncWaitHandle.WaitOne(1500)) {
                return $false
            }

            $cliente.EndConnect($resultado)
            return $true
        }
        finally {
            $cliente.Close()
        }
    }
    catch {
        return $false
    }
}

function Esperar-Puerto([int]$puerto, [int]$segundos = 30) {
    for ($i = 0; $i -lt $segundos; $i++) {
        if (Puerto-Activo $puerto) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

Write-Host ""
Write-Host "========================================"
Write-Host "  ECOLOGISTICA LIMA - DEMO LOCAL"
Write-Host "========================================"
Write-Host "Repositorio: $repo"
Write-Host "Herramientas: $base"
Write-Host ""

# Verificar herramientas previamente instaladas.
Verificar-Archivo "$pg\bin\pg_ctl.exe"
Verificar-Archivo "$pg\bin\pg_isready.exe"
Verificar-Archivo "$node\node.exe"
Verificar-Archivo "$backend\.venv\Scripts\python.exe"
Verificar-Archivo "$frontend\node_modules\vite\bin\vite.js"
Verificar-Archivo "$run\postgres-password.txt"

if (-not (Test-Path "$datos\PG_VERSION")) {
    throw "PostgreSQL no esta inicializado en $datos"
}

# 1. PostgreSQL
Write-Host "[1/3] Comprobando PostgreSQL..."

& "$pg\bin\pg_ctl.exe" -D "$datos" status *> $null

if ($LASTEXITCODE -ne 0) {
    if (Puerto-Activo 55432) {
        throw "El puerto 55432 esta ocupado por otro proceso."
    }

    & "$pg\bin\pg_ctl.exe" `
        -D "$datos" `
        -l "$run\postgres.log" `
        -o "-h 127.0.0.1 -p 55432" `
        -w start

    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo iniciar PostgreSQL."
    }
}

& "$pg\bin\pg_isready.exe" -h 127.0.0.1 -p 55432 -t 3

if ($LASTEXITCODE -ne 0) {
    throw "PostgreSQL no responde en el puerto 55432."
}

Write-Host "[OK] PostgreSQL disponible."

# Preparar la conexion del backend.
$clave = [System.IO.File]::ReadAllText(
    "$run\postgres-password.txt"
).Trim()

$claveURL = [Uri]::EscapeDataString($clave)

$env:DATABASE_URL = "postgresql+psycopg://demo_admin:$claveURL@127.0.0.1:55432/ecologistica_demo"
$env:APP_ENV = "development"
$env:CORS_ALLOWED_ORIGINS = '["http://127.0.0.1:5173"]'

Remove-Variable clave, claveURL

try {
    # 2. FastAPI
    Write-Host "[2/3] Comprobando FastAPI..."

    if (-not (Puerto-Activo 8000)) {
        $procesoBackend = Start-Process `
            -FilePath "$backend\.venv\Scripts\python.exe" `
            -ArgumentList @(
                "-m", "uvicorn",
                "app.main:create_app",
                "--factory",
                "--host", "127.0.0.1",
                "--port", "8000"
            ) `
            -WorkingDirectory $backend `
            -RedirectStandardOutput "$run\backend.out.log" `
            -RedirectStandardError "$run\backend.err.log" `
            -PassThru

        Set-Content "$run\backend.pid" $procesoBackend.Id
    }
    else {
        Write-Host "[EXISTE] Puerto 8000 ocupado; se verificara FastAPI."
    }

    if (-not (Esperar-Puerto 8000 30)) {
        throw "FastAPI no inicio. Revisar $run\backend.err.log"
    }

    try {
        $salud = Invoke-RestMethod `
            -Uri "http://127.0.0.1:8000/health" `
            -TimeoutSec 5

        if ($salud.status -ne "ok") {
            throw "Respuesta inesperada del backend."
        }
    }
    catch {
        throw "FastAPI no responde correctamente en /health."
    }

    Write-Host "[OK] FastAPI disponible."

    # 3. Frontend React
    Write-Host "[3/3] Comprobando React..."

    $env:PATH = "$node;$env:PATH"
    $env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
    $env:npm_config_cache = "$base\cache\npm"

    if (-not (Puerto-Activo 5173)) {
        $procesoFrontend = Start-Process `
            -FilePath "$node\node.exe" `
            -ArgumentList @(
                "node_modules/vite/bin/vite.js",
                "--host", "127.0.0.1",
                "--port", "5173",
                "--strictPort"
            ) `
            -WorkingDirectory $frontend `
            -RedirectStandardOutput "$run\frontend.out.log" `
            -RedirectStandardError "$run\frontend.err.log" `
            -PassThru

        Set-Content "$run\frontend.pid" $procesoFrontend.Id
    }
    else {
        Write-Host "[EXISTE] Puerto 5173 ocupado."
    }

    if (-not (Esperar-Puerto 5173 30)) {
        throw "React no inicio. Revisar $run\frontend.err.log"
    }

    Write-Host "[OK] Frontend disponible."

    Write-Host ""
    Write-Host "========================================"
    Write-Host "  DEMO INICIADA"
    Write-Host "========================================"
    Write-Host "Aplicacion: http://127.0.0.1:5173"
    Write-Host "API:        http://127.0.0.1:8000/health"
    Write-Host ""
}
finally {
    Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:\VITE_API_BASE_URL -ErrorAction SilentlyContinue
}
