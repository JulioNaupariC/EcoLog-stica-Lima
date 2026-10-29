
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

function Es-ProcesoDelProyecto($Proceso, [string]$Servicio) {
    if (-not $Proceso) { return $false }
    $comando = [string]$Proceso.CommandLine
    $ejecutable = [string]$Proceso.ExecutablePath
    $python = Join-Path $repo "backend\.venv\Scripts\python.exe"
    $node = Join-Path $base "tools\node-v22.18.0-win-x64\node.exe"
    $vite = Join-Path $repo "frontend\node_modules\vite\bin\vite.js"
    $cmd = Join-Path $env:SystemRoot "System32\cmd.exe"

    if ($Servicio -eq "backend") {
        $patron = '\s-m\s+uvicorn\s+app\.main:create_app(?:\s|$)'
        $rutaServicio = $python
        $binario = $python
    }
    else {
        $patron = [regex]::Escape('"' + $vite + '"') + '\s+--host\s+127\.0\.0\.1\s+--port\s+5173(?:\s|$)'
        $rutaServicio = $vite
        $binario = $node
    }

    # Paréntesis explícitos: rechazar si falta la firma O si no es el binario
    # esperado NI el cmd que contiene la ruta absoluta del servicio del repo.
    if (
        ($comando -notmatch $patron) -or
        (($ejecutable -ine $binario) -and
         (($ejecutable -ine $cmd) -or
          ($comando -notmatch [regex]::Escape('"' + $rutaServicio + '"'))))
    ) { return $false }
    return $true
}

function Detener-Arbol([int]$IdProceso, [string]$Servicio) {
    $proceso = Get-CimInstance Win32_Process -Filter "ProcessId = $IdProceso" -ErrorAction SilentlyContinue
    if (-not $proceso) { return $true }
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
    # Primero el cmd raíz guardado, incluso si el servicio aún no abrió su puerto.
    if (Test-Path -LiteralPath $archivoPid) {
        $idGuardado = 0
        $contenido = ([string](Get-Content -LiteralPath $archivoPid -Raw)).Trim()
        if (([int]::TryParse($contenido, [ref]$idGuardado)) -and ($idGuardado -gt 0)) {
            if (Detener-Arbol $idGuardado $Servicio) {
                Remove-Item -LiteralPath $archivoPid
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
    if ($conexiones.Count -eq 0) {
        Write-Host "[DETENIDO] Puerto $Puerto libre."
    }
}

Write-Host ""
Write-Host "========================================"
Write-Host "  DETENIENDO ECOLOGISTICA LIMA"
Write-Host "========================================"

Write-Host "[1/3] Deteniendo frontend..."
Detener-ServicioWeb -Puerto 5173 -Servicio "frontend"

Write-Host "[2/3] Deteniendo backend..."
Detener-ServicioWeb -Puerto 8000 -Servicio "backend"

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
