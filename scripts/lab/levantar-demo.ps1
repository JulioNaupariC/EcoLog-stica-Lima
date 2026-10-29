#requires -Version 5.1

# ECL-68 - Inicio de la demostracion local
# No necesita Docker ni permisos de administrador.

$ErrorActionPreference = "Stop"

$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent

if ($env:ECOLOGISTICA_DEMO_HOME) {
    $base = $env:ECOLOGISTICA_DEMO_HOME
} else {
    $base = Join-Path $env:LOCALAPPDATA "EcoLogisticaDemo"
}

$base = [IO.Path]::GetFullPath($base)

$pg = Join-Path $base "tools\postgresql-16\pgsql"
$node = Join-Path $base "tools\node-v22.18.0-win-x64"
$datos = Join-Path $base "pgdata"
$run = Join-Path $base "run"
$backend = Join-Path $repo "backend"
$frontend = Join-Path $repo "frontend"

. (Join-Path $PSScriptRoot "procesos-demo.ps1")

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

function Esperar-Puerto([int]$puerto, [int]$segundos = 60, $Proceso = $null, [string]$Servicio = "servicio") {
    for ($i = 0; $i -lt $segundos; $i++) {
        Confirmar-Proceso $Proceso $Servicio
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

function Iniciar-Servicio([string]$Servicio) {
    # CREATE_NO_WINDOW mediante .NET: ocultar/minimizar una ventana no la separa.
    $inicio = New-Object System.Diagnostics.ProcessStartInfo
    $inicio.FileName = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $inicio.Arguments = '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -Servicio {1}' -f (Join-Path $PSScriptRoot 'servicio-demo.ps1'), $Servicio
    $inicio.WorkingDirectory = $repo
    $inicio.UseShellExecute = $false
    $inicio.CreateNoWindow = $true
    $inicio.RedirectStandardInput = $true
    $supervisor = [System.Diagnostics.Process]::Start($inicio)
    $supervisor.StandardInput.Close()
    # El supervisor publica el PID REAL antes de que el llamante compruebe HTTP.
    $limite = (Get-Date).AddSeconds(60)
    do {
        $supervisor.Refresh()
        if ($supervisor.HasExited) {
            throw "El supervisor de $Servicio termino. Revisar $run\$Servicio.lifecycle.log"
        }
        $archivo = Join-Path $run "$Servicio.process.json"
        if (Test-Path -LiteralPath $archivo) {
            try {
                $estado = Get-Content -LiteralPath $archivo -Raw | ConvertFrom-Json
                if ($estado.SupervisorId -eq $supervisor.Id) {
                    $proceso = Get-Process -Id $estado.ProcessId -ErrorAction Stop
                    $null = $proceso.Handle
                    if ($proceso.StartTime.ToUniversalTime().Ticks -eq [long]$estado.StartTicks) {
                        Write-Host "[PID] $Servicio servicio=$($proceso.Id), supervisor=$($supervisor.Id)"
                        return $proceso
                    }
                }
            }
            catch { }
        }
        Start-Sleep -Milliseconds 200
    } while ((Get-Date) -lt $limite)
    throw "No se publico un PID valido para $Servicio. Revisar $run\$Servicio.lifecycle.log"
}

function Confirmar-Proceso($Proceso, [string]$Servicio) {
    if ($null -ne $Proceso) {
        $Proceso.Refresh()
        if ($Proceso.HasExited) {
            throw "$Servicio termino (codigo $($Proceso.ExitCode)). Revisar $run\$Servicio.lifecycle.log y $run\$Servicio.err.log"
        }
    }
}

Write-Host ""
Write-Host "========================================"
Write-Host "  ECOLOGISTICA LIMA - DEMO LOCAL"
Write-Host "========================================"
Write-Host "Repositorio: $repo"
Write-Host "Herramientas: $base"
Write-Host ""

# Verificar herramientas previamente instaladas.
Verificar-Archivo (Join-Path $PSScriptRoot "servicio-demo.ps1")
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
$variablesDemo = @('ECOLOGISTICA_DEMO_HOME', 'DATABASE_URL', 'APP_ENV', 'CORS_ALLOWED_ORIGINS', 'PATH', 'VITE_API_BASE_URL', 'npm_config_cache')
$entornoAnterior = @{}
foreach ($nombre in $variablesDemo) {
    $entornoAnterior[$nombre] = [Environment]::GetEnvironmentVariable($nombre, 'Process')
}

$fase = 'environment'
Add-Content -LiteralPath "$run\launcher.lifecycle.log" -Value "$(Get-Date -Format o) launcher-start pid=$PID" -Encoding ASCII
try {
    $env:ECOLOGISTICA_DEMO_HOME = $base
    $env:APP_ENV = "development"
    $env:CORS_ALLOWED_ORIGINS = '["http://127.0.0.1:5173"]'

    $procesoBackend = $null
    $procesoFrontend = $null

    $fase = 'backend-start'
    # 2. FastAPI
    Write-Host "[2/3] Comprobando FastAPI..."

    if (-not (Puerto-Activo 8000)) {
        $procesoBackend = Iniciar-Servicio "backend"
    }
    else {
        Write-Host "[EXISTE] Puerto 8000 ocupado; se verificara FastAPI."
    }

    if (-not (Esperar-Puerto 8000 60 $procesoBackend "backend")) {
        Confirmar-Proceso $procesoBackend "backend"
        throw "FastAPI no inicio. Revisar $run\backend.err.log"
    }

    $fase = 'backend-identity'
    if (-not (Verificar-PuertoDelProyecto 8000 "backend")) {
        throw "Puerto 8000 ocupado por un proceso no identificado como backend del proyecto."
    }
    $fase = 'backend-http'
    if (-not (Esperar-HTTP "http://127.0.0.1:8000/health" -Backend)) {
        throw "FastAPI no responde correctamente en /health. Revisar $run\backend.err.log"
    }

    Confirmar-Proceso $procesoBackend "backend"
    Write-Host "[OK] FastAPI disponible."

    Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue

    $fase = 'frontend-start'
    # 3. Frontend React
    Write-Host "[3/3] Comprobando React..."

    $env:PATH = "$node;$env:PATH"
    $env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
    $env:npm_config_cache = "$base\cache\npm"

    if (-not (Puerto-Activo 5173)) {
        $procesoFrontend = Iniciar-Servicio "frontend"
    }
    else {
        Write-Host "[EXISTE] Puerto 5173 ocupado."
    }

    if (-not (Esperar-Puerto 5173 60 $procesoFrontend "frontend")) {
        Confirmar-Proceso $procesoFrontend "frontend"
        throw "React no inicio. Revisar $run\frontend.err.log"
    }

    $fase = 'frontend-identity'
    if (-not (Verificar-PuertoDelProyecto 5173 "frontend")) {
        throw "Puerto 5173 ocupado por un proceso no identificado como frontend del proyecto."
    }
    if (-not (Esperar-HTTP "http://127.0.0.1:5173/")) {
        throw "React no responde por HTTP. Revisar $run\frontend.err.log"
    }

    Confirmar-Proceso $procesoFrontend "frontend"
    # Detectar una salida inmediatamente posterior al primer HTTP correcto.
    Start-Sleep -Seconds 2
    Confirmar-Proceso $procesoBackend "backend"
    Confirmar-Proceso $procesoFrontend "frontend"
    if ((-not (Puerto-Activo 8000)) -or (-not (Puerto-Activo 5173))) {
        throw "Un servicio dejo de escuchar tras el inicio. Revisar los logs en $run"
    }
    Write-Host "[OK] Frontend disponible."

    Write-Host ""
    Write-Host "========================================"
    $fase = 'ready'
    Add-Content -LiteralPath "$run\launcher.lifecycle.log" -Value "$(Get-Date -Format o) launcher-ready pid=$PID" -Encoding ASCII
    Write-Host "  DEMO INICIADA"
    Write-Host "========================================"
    Write-Host "Aplicacion: http://127.0.0.1:5173"
    Write-Host "API:        http://127.0.0.1:8000/health"
    Write-Host ""
}
catch {
    Add-Content -LiteralPath "$run\launcher.lifecycle.log" -Value "$(Get-Date -Format o) launcher-failed pid=$PID stage=$fase type=$($_.Exception.GetType().Name)" -Encoding ASCII -ErrorAction Continue
    throw # Conservar el fallo: no cerrar ventanas ni terminar el arbol.
}
finally {
    Add-Content -LiteralPath "$run\launcher.lifecycle.log" -Value "$(Get-Date -Format o) launcher-finally pid=$PID stage=$fase" -Encoding ASCII -ErrorAction Continue
    foreach ($nombre in $variablesDemo) {
        [Environment]::SetEnvironmentVariable($nombre, $entornoAnterior[$nombre], 'Process')
    }
}
