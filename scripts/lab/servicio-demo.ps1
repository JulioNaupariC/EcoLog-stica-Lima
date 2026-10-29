#requires -Version 5.1
# Supervisor con consola propia. No ejecutar directamente: usar levantar-demo.ps1.
param([Parameter(Mandatory = $true)][ValidateSet('backend', 'frontend')][string]$Servicio)
$ErrorActionPreference = 'Stop'
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$base = $env:ECOLOGISTICA_DEMO_HOME
if (-not $base) { $base = Join-Path $env:LOCALAPPDATA 'EcoLogisticaDemo' }
$run = Join-Path $base 'run'
New-Item -ItemType Directory -Force -Path $run | Out-Null
$archivoPid = Join-Path $run "$Servicio.pid"
$archivoEstado = Join-Path $run "$Servicio.process.json"
$log = Join-Path $run "$Servicio.lifecycle.log"
$bloqueo = $null
$proceso = $null
try {
    # Evitar dos lanzamientos simultaneos, incluso antes de abrir el puerto.
    $bloqueo = [IO.File]::Open((Join-Path $run "$Servicio.lock"), 'OpenOrCreate', 'ReadWrite', 'None')
    if ($Servicio -eq 'backend') {
        if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) { throw 'Entorno incompleto' }
        $directorio = Join-Path $repo 'backend'
        $ejecutable = Join-Path $directorio '.venv\Scripts\python.exe'
        $argumentos = '-m uvicorn app.main:create_app --factory --app-dir "{0}" --host 127.0.0.1 --port 8000' -f $directorio
    }
    else {
        Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
        $directorio = Join-Path $repo 'frontend'
        $ejecutable = Join-Path $base 'tools\node-v22.18.0-win-x64\node.exe'
        $argumentos = '"{0}" --host 127.0.0.1 --port 5173 --strictPort' -f (Join-Path $directorio 'node_modules\vite\bin\vite.js')
    }
    # Sin cmd /c ni start: no hay una segunda capa de expansion/comillas.
    # NoNewWindow comparte SOLO la consola independiente del supervisor.
    # La redireccion nativa evita tratar stderr de Uvicorn como error PowerShell 5.1.
    $proceso = Start-Process -FilePath $ejecutable -ArgumentList $argumentos `
        -WorkingDirectory $directorio -NoNewWindow `
        -RedirectStandardOutput (Join-Path $run "$Servicio.out.log") `
        -RedirectStandardError (Join-Path $run "$Servicio.err.log") -PassThru
    Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
    $inicio = $proceso.StartTime.ToUniversalTime().Ticks
    $estado = [ordered]@{ ProcessId = $proceso.Id; StartTicks = $inicio; SupervisorId = $PID }
    $temporal = "$archivoEstado.$PID.tmp"
    $estado | ConvertTo-Json | Set-Content -LiteralPath $temporal -Encoding ASCII
    Move-Item -LiteralPath $temporal -Destination $archivoEstado -Force
    Set-Content -LiteralPath $archivoPid -Value $proceso.Id -Encoding ASCII
    Add-Content -LiteralPath $log -Value "$(Get-Date -Format o) started pid=$($proceso.Id) supervisor=$PID" -Encoding ASCII
    # Mantener vivo al propietario de las tuberias y esperar al servicio real.
    $proceso.WaitForExit()
    Add-Content -LiteralPath $log -Value "$(Get-Date -Format o) exited pid=$($proceso.Id) code=$($proceso.ExitCode)" -Encoding ASCII
}
catch {
    # No imprimir la excepcion: puede incluir datos del entorno o argumentos.
    Add-Content -LiteralPath $log -Value "$(Get-Date -Format o) supervisor-failed type=$($_.Exception.GetType().Name)" -Encoding ASCII
    exit 1
}
finally {
    Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
    if ($null -ne $proceso) {
        $proceso.Refresh()
        if ($proceso.HasExited) {
            # No borrar el registro de un arranque posterior.
            if ((Test-Path -LiteralPath $archivoPid) -and
                (([string](Get-Content -LiteralPath $archivoPid -Raw)).Trim() -eq [string]$proceso.Id)) {
                Remove-Item -LiteralPath $archivoPid -ErrorAction SilentlyContinue
            }
        }
    }
    if ($null -ne $bloqueo) { $bloqueo.Dispose() }
}
