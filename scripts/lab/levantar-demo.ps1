
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

function Esperar-Puerto([int]$puerto, [int]$segundos = 60) {
    for ($i = 0; $i -lt $segundos; $i++) {
        if (Puerto-Activo $puerto) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Esperar-HTTP([string]$uri, [switch]$Backend, [int]$segundos = 60) {
    $limite = (Get-Date).AddSeconds($segundos)
    do {
        try {
            $restante = [Math]::Max(1, [Math]::Min(5, [int]($limite - (Get-Date)).TotalSeconds))
            $respuesta = Invoke-WebRequest -Uri $uri -UseBasicParsing -TimeoutSec $restante
            if ($respuesta.StatusCode -eq 200) {
                if (-not $Backend) { return $true }
                $salud = $respuesta.Content | ConvertFrom-Json
                if ($salud.status -eq "ok") { return $true }
            }
        }
        catch { }
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $limite)
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
if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
    throw "Define DATABASE_URL en el entorno antes de iniciar (ver la guía)."
}

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
        -t 60 -w start

    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo iniciar PostgreSQL."
    }
}

& "$pg\bin\pg_isready.exe" -h 127.0.0.1 -p 55432 -t 3

if ($LASTEXITCODE -ne 0) {
    throw "PostgreSQL no responde en el puerto 55432."
}

Write-Host "[OK] PostgreSQL disponible."

# Guardar y restaurar el entorno de la consola. Solo FastAPI hereda DATABASE_URL.
$variablesDemo = @('DATABASE_URL', 'APP_ENV', 'CORS_ALLOWED_ORIGINS', 'PATH', 'VITE_API_BASE_URL', 'npm_config_cache')
$entornoAnterior = @{}
foreach ($nombre in $variablesDemo) {
    $entornoAnterior[$nombre] = [Environment]::GetEnvironmentVariable($nombre, 'Process')
}

try {
    $env:APP_ENV = "development"
    $env:CORS_ALLOWED_ORIGINS = '["http://127.0.0.1:5173"]'

    # 2. FastAPI
    Write-Host "[2/3] Comprobando FastAPI..."

    if (-not (Puerto-Activo 8000)) {
        # cmd conserva el árbol y la redirección sin depender de la consola llamante.
        # Las credenciales solo se heredan por entorno; nunca van en argumentos.
        $comandoBackend = '""{0}\.venv\Scripts\python.exe" -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 1>"{1}\backend.out.log" 2>"{1}\backend.err.log""' -f $backend, $run
        $procesoBackend = Start-Process `
            -FilePath "$env:SystemRoot\System32\cmd.exe" `
            -ArgumentList @('/d', '/s', '/c', $comandoBackend) `
            -WorkingDirectory $backend `
            -WindowStyle Minimized `
            -PassThru
        Set-Content "$run\backend.pid" $procesoBackend.Id
    }
    else {
        Write-Host "[EXISTE] Puerto 8000 ocupado; se verificara FastAPI."
    }

    if (-not (Esperar-Puerto 8000 60)) {
        throw "FastAPI no inicio. Revisar $run\backend.err.log"
    }

    if (-not (Esperar-HTTP "http://127.0.0.1:8000/health" -Backend)) {
        throw "FastAPI no responde correctamente en /health. Revisar $run\backend.err.log"
    }

    Write-Host "[OK] FastAPI disponible."

    Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue

    # 3. Frontend React
    Write-Host "[3/3] Comprobando React..."

    $env:PATH = "$node;$env:PATH"
    $env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
    $env:npm_config_cache = "$base\cache\npm"

    if (-not (Puerto-Activo 5173)) {
        $comandoFrontend = '""{0}\node.exe" "{1}\node_modules\vite\bin\vite.js" --host 127.0.0.1 --port 5173 --strictPort 1>"{2}\frontend.out.log" 2>"{2}\frontend.err.log""' -f $node, $frontend, $run
        $procesoFrontend = Start-Process `
            -FilePath "$env:SystemRoot\System32\cmd.exe" `
            -ArgumentList @('/d', '/s', '/c', $comandoFrontend) `
            -WorkingDirectory $frontend `
            -WindowStyle Minimized `
            -PassThru
        Set-Content "$run\frontend.pid" $procesoFrontend.Id
    }
    else {
        Write-Host "[EXISTE] Puerto 5173 ocupado."
    }

    if (-not (Esperar-Puerto 5173 60)) {
        throw "React no inicio. Revisar $run\frontend.err.log"
    }

    if (-not (Esperar-HTTP "http://127.0.0.1:5173/")) {
        throw "React no responde por HTTP. Revisar $run\frontend.err.log"
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
    foreach ($nombre in $variablesDemo) {
        [Environment]::SetEnvironmentVariable($nombre, $entornoAnterior[$nombre], 'Process')
    }
}
