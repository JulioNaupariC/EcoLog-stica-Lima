#requires -Version 5.1
# Supervisor con consola propia. No ejecutar directamente: usar levantar-demo.ps1.
param(
    [Parameter(Mandatory = $true)][ValidateSet('backend', 'frontend')][string]$Servicio,
    [ValidateSet('Ninguna', 'Normal', 'FalloSupervisor', 'Espera')][string]$Prueba = 'Ninguna'
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$base = $env:ECOLOGISTICA_DEMO_HOME
if (-not $base) { $base = Join-Path $env:LOCALAPPDATA 'EcoLogisticaDemo' }
$run = Join-Path $base 'run'
New-Item -ItemType Directory -Force -Path $run | Out-Null
if (($Prueba -ne 'Ninguna') -and ($Servicio -ne 'frontend')) { throw 'Prueba solo de frontend' }
if ($Prueba -eq 'Ninguna') { $Host.UI.RawUI.WindowTitle = "ECL-68 $Servicio supervisor=$PID" }
if ($Prueba -ne 'Ninguna') { $Host.UI.RawUI.WindowTitle = "ECL-68 fixture $Prueba supervisor=$PID" }
$registro = $Servicio
if ($Prueba -ne 'Ninguna') { $registro = "frontend-prueba-$Prueba" }
$archivoPid = Join-Path $run "$registro.pid"
$archivoEstado = Join-Path $run "$registro.process.json"
$log = Join-Path $run "$registro.lifecycle.log"
$bloqueo = $null
$proceso = $null
$etapa = 'lock'
try {
    # Evitar dos lanzamientos simultaneos, incluso antes de abrir el puerto.
    $bloqueo = [IO.File]::Open((Join-Path $run "$registro.lock"), 'OpenOrCreate', 'ReadWrite', 'None')
    $etapa = 'console-hooks'
    if ($env:OS -eq 'Windows_NT') {
        if (-not ('EcoLogConsoleEvidence' -as [type])) {
            Add-Type -Path (Join-Path $PSScriptRoot 'diagnostico-consola.cs')
        }
        [EcoLogConsoleEvidence]::Install((Join-Path $run "$registro.console.log"), $PID)
        Add-Content -LiteralPath $log -Value "$(Get-Date -Format o) supervisor-start pid=$PID $([EcoLogConsoleEvidence]::Snapshot())" -Encoding ASCII
    }
    if ($Servicio -eq 'backend') {
        if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) { throw 'Entorno incompleto' }
        $directorio = Join-Path $repo 'backend'
        $ejecutable = Join-Path $directorio '.venv\Scripts\python.exe'
        $argumentos = '-m uvicorn app.main:create_app --factory --app-dir "{0}" --host 127.0.0.1 --port 8000' -f $directorio
    }
    else {
        Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
        $env:CI = 'true' # Vite: no cerrar el servidor por stdin/end ni atajos interactivos.
        $directorio = Join-Path $repo 'frontend'
        $ejecutable = Join-Path $base 'tools\node-v22.18.0-win-x64\node.exe'
        $argumentos = '"{0}" --host 127.0.0.1 --port 5173 --strictPort' -f (Join-Path $directorio 'node_modules\vite\bin\vite.js')
    }
    if ($Prueba -ne 'Ninguna') {
        $argumentos = '"{0}" {1}' -f (Join-Path $PSScriptRoot 'tests\proceso-fixture.cjs'), $Prueba
    }
    # Sin cmd /c ni start: no hay una segunda capa de expansion/comillas.
    # NoNewWindow comparte SOLO la consola independiente del supervisor.
    # La redireccion nativa evita tratar stderr de Uvicorn como error PowerShell 5.1.
    $etapa = 'launch-child'
    $proceso = Start-Process -FilePath $ejecutable -ArgumentList $argumentos `
        -WorkingDirectory $directorio -NoNewWindow `
        -RedirectStandardOutput (Join-Path $run "$registro.out.log") `
        -RedirectStandardError (Join-Path $run "$registro.err.log") -PassThru
    # Abrir y conservar el handle antes de que el redirector termine (PS 5.1).
    $null = $proceso.Handle
    Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
    $etapa = 'publish-state'
    $inicio = $proceso.StartTime.ToUniversalTime().Ticks
    $lanzadorId = 0
    $lanzador = $null
    if ($env:OS -eq 'Windows_NT') {
        $yo = Get-CimInstance Win32_Process -Filter "ProcessId = $PID" -ErrorAction Stop
        $lanzadorId = $yo.ParentProcessId
        $lanzador = Get-Process -Id $lanzadorId -ErrorAction SilentlyContinue
        if ($null -ne $lanzador) { $null = $lanzador.Handle }
        Add-Content -LiteralPath $log -Value "$(Get-Date -Format o) launcher-parent pid=$lanzadorId" -Encoding ASCII
    }
    $estado = [ordered]@{ ProcessId = $proceso.Id; StartTicks = $inicio; SupervisorId = $PID; SupervisorStartTicks = (Get-Process -Id $PID).StartTime.ToUniversalTime().Ticks; Trial = $Prueba; LauncherId = $lanzadorId }
    $temporal = "$archivoEstado.$PID.tmp"
    $estado | ConvertTo-Json | Set-Content -LiteralPath $temporal -Encoding ASCII
    Move-Item -LiteralPath $temporal -Destination $archivoEstado -Force
    Set-Content -LiteralPath $archivoPid -Value $proceso.Id -Encoding ASCII
    if ($env:OS -eq 'Windows_NT') {
        Add-Content -LiteralPath $log -Value "$(Get-Date -Format o) child-console $([EcoLogConsoleEvidence]::Snapshot())" -Encoding ASCII
    }
    Add-Content -LiteralPath $log -Value "$(Get-Date -Format o) started pid=$($proceso.Id) supervisor=$PID" -Encoding ASCII
    # Mantener vivo al propietario de las tuberias y esperar al servicio real.
    $etapa = 'monitor'
    $contador = 0
    $lanzadorTermino = $false
    while (-not $proceso.WaitForExit(1000)) {
        $contador++
        if (($null -ne $lanzador) -and (-not $lanzadorTermino)) {
            $lanzador.Refresh()
            if ($lanzador.HasExited) {
                Add-Content -LiteralPath $log -Value "$(Get-Date -Format o) launcher-exited pid=$lanzadorId" -Encoding ASCII
                $lanzadorTermino = $true
            }
        }
        # Diario pequeno: no registrar argumentos, rutas privadas ni entorno.
        if (($contador % 5) -eq 0) {
            Add-Content -LiteralPath $log -Value "$(Get-Date -Format o) heartbeat pid=$($proceso.Id) supervisor=$PID" -Encoding ASCII
        }
        if (($Prueba -eq 'FalloSupervisor') -and ($contador -ge 8)) {
            $etapa = 'controlled-failure'
            throw 'Fallo controlado de prueba'
        }
    }
    $proceso.WaitForExit() # Drenar las redirecciones asincronas antes de registrar salida.
    $codigo = $proceso.ExitCode
    $codigoTexto = 'unknown'
    if ($null -ne $codigo) { $codigoTexto = [string]$codigo }
    Add-Content -LiteralPath $log -Value "$(Get-Date -Format o) exited pid=$($proceso.Id) code=$codigoTexto" -Encoding ASCII
}
catch {
    # No imprimir la excepcion: puede incluir datos del entorno o argumentos.
    Add-Content -LiteralPath $log -Value "$(Get-Date -Format o) supervisor-failed stage=$etapa type=$($_.Exception.GetType().Name)" -Encoding ASCII
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
    Add-Content -LiteralPath $log -Value "$(Get-Date -Format o) supervisor-finally pid=$PID" -Encoding ASCII
}
