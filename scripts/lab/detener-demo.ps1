
# ECL-68 - Detener la demostracion local
# Sin Docker ni permisos de administrador.

$ErrorActionPreference = "Stop"

$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent

if ($env:ECOLOGISTICA_DEMO_HOME) {
    $base = $env:ECOLOGISTICA_DEMO_HOME
} else {
    $base = Join-Path $env:LOCALAPPDATA "EcoLogisticaDemo"
}

$pg = Join-Path $base "tools\postgresql-16\pgsql"
$datos = Join-Path $base "pgdata"
$run = Join-Path $base "run"

function Detener-ServicioWeb {
    param(
        [int]$Puerto,
        [string]$Nombre,
        [string]$Patron
    )

    $conexiones = @(
        Get-NetTCPConnection -LocalPort $Puerto -State Listen `
            -ErrorAction SilentlyContinue
    )

    if ($conexiones.Count -eq 0) {
        Write-Host "[DETENIDO] $Nombre no esta activo."
        return
    }

    $ids = @($conexiones | Select-Object -ExpandProperty OwningProcess -Unique)

    foreach ($idProceso in $ids) {
        $proceso = Get-CimInstance Win32_Process `
            -Filter "ProcessId = $idProceso" `
            -ErrorAction SilentlyContinue

        if (-not $proceso) {
            continue
        }

        $comando = [string]$proceso.CommandLine
        $ejecutable = [string]$proceso.ExecutablePath

        # No detener servicios ajenos al proyecto.
        if (
            $comando -notmatch $Patron -or
            $ejecutable -notlike "$base\*" -and
            $ejecutable -notlike "$repo\*"
        ) {
            Write-Host "[AVISO] Puerto $Puerto pertenece a otro proceso. No se detiene."
            continue
        }

        Stop-Process -Id $idProceso -ErrorAction Stop
        Write-Host "[OK] $Nombre detenido (PID $idProceso)."
    }
}

Write-Host ""
Write-Host "========================================"
Write-Host "  DETENIENDO ECOLOGISTICA LIMA"
Write-Host "========================================"

Write-Host "[1/3] Deteniendo frontend..."
Detener-ServicioWeb `
    -Puerto 5173 `
    -Nombre "React" `
    -Patron "vite"

Write-Host "[2/3] Deteniendo backend..."
Detener-ServicioWeb `
    -Puerto 8000 `
    -Nombre "FastAPI" `
    -Patron "uvicorn"

Write-Host "[3/3] Deteniendo PostgreSQL..."

if (Test-Path "$pg\bin\pg_ctl.exe") {
    & "$pg\bin\pg_ctl.exe" -D "$datos" status *> $null

    if ($LASTEXITCODE -eq 0) {
        & "$pg\bin\pg_ctl.exe" -D "$datos" -m fast -w stop

        if ($LASTEXITCODE -ne 0) {
            throw "No se pudo detener PostgreSQL."
        }

        Write-Host "[OK] PostgreSQL detenido."
    }
    else {
        Write-Host "[DETENIDO] PostgreSQL no estaba activo."
    }
}
else {
    Write-Host "[AVISO] No se encontro pg_ctl.exe."
}

Write-Host ""
Write-Host "Demostracion detenida."
Write-Host "Los datos de PostgreSQL se conservan."
