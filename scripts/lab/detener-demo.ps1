#requires -Version 5.1

# ECL-68 - Detener la demostracion local
# Sin Docker ni permisos de administrador.

$ErrorActionPreference = "Stop"

$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent

if ($env:ECOLOGISTICA_DEMO_HOME) {
    $base = $env:ECOLOGISTICA_DEMO_HOME
} else {
    $base = Join-Path $env:LOCALAPPDATA "EcoLogisticaDemo"
}

$base = [IO.Path]::GetFullPath($base)

$pg = Join-Path $base "tools\postgresql-16\pgsql"
$datos = Join-Path $base "pgdata"
$run = Join-Path $base "run"

. (Join-Path $PSScriptRoot "procesos-demo.ps1")

function Detener-Arbol([int]$IdProceso, [string]$Servicio, [switch]$Guardado) {
    $proceso = Get-CimInstance Win32_Process -Filter "ProcessId = $IdProceso" -ErrorAction SilentlyContinue
    if (-not $proceso) { return $true }
    if ($Guardado) {
        # Un PID puede reutilizarse. El registro nuevo debe coincidir en ID y fecha.
        $archivoEstado = Join-Path $run "$Servicio.process.json"
        if (Test-Path -LiteralPath $archivoEstado) {
            try {
                $estado = Get-Content -LiteralPath $archivoEstado -Raw | ConvertFrom-Json
                $actual = Get-Process -Id $IdProceso -ErrorAction Stop
                if (($estado.ProcessId -ne $IdProceso) -or
                    ([long]$estado.StartTicks -ne $actual.StartTime.ToUniversalTime().Ticks)) {
                    Write-Host "[AVISO] PID $IdProceso obsoleto o reutilizado; se comprobara el puerto."
                    return $false
                }
            }
            catch {
                Write-Host "[AVISO] No se pudo validar la fecha del PID $IdProceso; se comprobara el puerto."
                return $false
            }
        }
        else {
            # PID de la version antigua: no confiar en un cmd intermediario.
            Write-Host "[AVISO] PID sin registro de identidad; se comprobara el puerto."
            return $false
        }
    }
    if (-not (Es-ProcesoDelProyecto $proceso $Servicio)) {
        Write-Host "[AVISO] PID $IdProceso no identificado como $Servicio del proyecto; no se detiene."
        return $false
    }
    & "$env:SystemRoot\System32\taskkill.exe" /PID $IdProceso /T /F | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo detener el árbol de $Servicio (PID $IdProceso)."
    }
    Write-Host "[OK] $Servicio detenido (PID $IdProceso y descendientes)."
    return $true
}

function Detener-ServicioWeb([int]$Puerto, [string]$Servicio) {
    $archivoPid = Join-Path $run "$Servicio.pid"
    # Primero el PID real guardado, incluso si aun no abrio su puerto.
    if (Test-Path -LiteralPath $archivoPid) {
        $idGuardado = 0
        $contenido = ([string](Get-Content -LiteralPath $archivoPid -Raw)).Trim()
        if (([int]::TryParse($contenido, [ref]$idGuardado)) -and ($idGuardado -gt 0)) {
            if (Detener-Arbol $idGuardado $Servicio -Guardado) {
                Remove-Item -LiteralPath $archivoPid -ErrorAction SilentlyContinue
            }
        }
        else {
            Write-Host "[AVISO] PID inválido en $archivoPid; se comprobará el puerto."
        }
    }

    # Respaldo para PID ausente, obsoleto o servicio iniciado manualmente.
    $conexiones = @(Get-NetTCPConnection -LocalPort $Puerto -State Listen -ErrorAction SilentlyContinue)
    foreach ($idProceso in @($conexiones | Select-Object -ExpandProperty OwningProcess -Unique)) {
        $null = Detener-Arbol $idProceso $Servicio
    }
    $restantes = @(Get-NetTCPConnection -LocalPort $Puerto -State Listen -ErrorAction SilentlyContinue)
    if ($restantes.Count -eq 0) {
        Write-Host "[DETENIDO] Puerto $Puerto libre."
        return $true
    }
    Write-Host "[AVISO] El puerto $Puerto sigue ocupado; no se confirma el cierre de $Servicio."
    return $false
}

Write-Host ""
Write-Host "========================================"
Write-Host "  DETENIENDO ECOLOGISTICA LIMA"
Write-Host "========================================"

Write-Host "[1/3] Deteniendo frontend..."
$frontendDetenido = Detener-ServicioWeb -Puerto 5173 -Servicio "frontend"

Write-Host "[2/3] Deteniendo backend..."
$backendDetenido = Detener-ServicioWeb -Puerto 8000 -Servicio "backend"

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
if ($frontendDetenido -and $backendDetenido) {
    Write-Host "Demostracion detenida."
}
else {
    Write-Host "[AVISO] Cierre incompleto. Se conservaron los procesos no identificados."
}
Write-Host "Los datos de PostgreSQL se conservan."
