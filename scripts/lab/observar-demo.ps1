#requires -Version 5.1
# Ejecutar desde OTRA consola. Observa handles; nunca reinicia servicios.
param(
    [ValidateSet('backend', 'frontend')][string]$Servicio = 'frontend',
    [ValidateSet('Ninguna', 'Normal', 'FalloSupervisor', 'Espera')][string]$Prueba = 'Ninguna',
    [ValidateRange(10, 3600)][int]$Segundos = 180,
    [switch]$ForzarArbolPrueba,
    [switch]$LimpiarPrueba,
    [int]$SupervisorIdEsperado = 0
)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Este observador requiere Windows para handles y fechas nativas fiables.' }
if (($ForzarArbolPrueba -or $LimpiarPrueba) -and ($Prueba -eq 'Ninguna')) {
    throw 'Las acciones destructivas solo se permiten para el fixture aislado.'
}
if (($Prueba -ne 'Ninguna') -and ($Servicio -ne 'frontend')) { throw 'Prueba solo de frontend' }
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$base = $env:ECOLOGISTICA_DEMO_HOME
if (-not $base) { $base = Join-Path $env:LOCALAPPDATA 'EcoLogisticaDemo' }
$run = Join-Path $base 'run'
$registro = $Servicio
if ($Prueba -ne 'Ninguna') { $registro = "frontend-prueba-$Prueba" }
$archivo = Join-Path $run "$registro.process.json"
$limite = (Get-Date).AddSeconds(30)
$estado = $null
do {
    if (Test-Path -LiteralPath $archivo) {
        try {
            $leido = Get-Content -LiteralPath $archivo -Raw | ConvertFrom-Json
            if (($SupervisorIdEsperado -eq 0) -or ($leido.SupervisorId -eq $SupervisorIdEsperado)) { $estado = $leido }
        }
        catch { }
    }
    if ($null -eq $estado) {
        if ((Get-Date) -gt $limite) { throw "No se publico un registro actual en $archivo" }
        Start-Sleep -Milliseconds 200
    }
} while ($null -eq $estado)
if ($estado.Trial -ne $Prueba) { throw 'El registro no corresponde a esta prueba; iniciar la version actual.' }
$procesos = @{}
foreach ($item in @(@('child', $estado.ProcessId, $estado.StartTicks),
                    @('supervisor', $estado.SupervisorId, $estado.SupervisorStartTicks))) {
    $p = Get-Process -Id $item[1] -ErrorAction Stop
    $null = $p.Handle # Mantener handle abierto para conservar ExitCode tras la muerte.
    if ($p.StartTime.ToUniversalTime().Ticks -ne [long]$item[2]) { throw "PID reutilizado: $($item[0])" }
    $procesos[$item[0]] = $p
}
$salida = Join-Path $run ("{0}.observer.{1}.jsonl" -f $registro, (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
function Registrar($Datos) {
    $Datos['utc'] = [datetime]::UtcNow.ToString('o')
    $Datos | ConvertTo-Json -Compress | Add-Content -LiteralPath $salida -Encoding ASCII
}
function Identidad-Prueba([string]$Tipo) {
    $p = $procesos[$Tipo]; $p.Refresh()
    if ($p.HasExited) { return $false }
    $ticks = $estado.StartTicks
    if ($Tipo -eq 'supervisor') { $ticks = $estado.SupervisorStartTicks }
    if ($p.StartTime.ToUniversalTime().Ticks -ne [long]$ticks) { return $false }
    $cim = Get-CimInstance Win32_Process -Filter "ProcessId = $($p.Id)" -ErrorAction Stop
    if ($Tipo -eq 'child') {
        $node = Join-Path $base 'tools\node-v22.18.0-win-x64\node.exe'
        $fixture = [regex]::Escape('"' + (Join-Path $PSScriptRoot 'tests\proceso-fixture.cjs') + '"')
        return (($cim.ExecutablePath -ieq $node) -and ($cim.CommandLine -match ($fixture + '\s+' + $Prueba + '(?:\s|$)')))
    }
    $powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $script = [regex]::Escape('"' + (Join-Path $PSScriptRoot 'servicio-demo.ps1') + '"')
    return (($cim.ExecutablePath -ieq $powershell) -and
        ($cim.CommandLine -match ('-File\s+' + $script + '\s+-Servicio\s+frontend\s+-Prueba\s+' + $Prueba + '(?:\s|$)')))
}
Registrar @{event='observer-start'; child=$estado.ProcessId; supervisor=$estado.SupervisorId; trial=$Prueba}
Write-Host "Observando desde PID $PID. No cerrar esta consola. Registro: $salida"
$inicio = Get-Date
$forzado = $false
$vistos = @{}
try {
    do {
        foreach ($tipo in @('child', 'supervisor')) {
            $p = $procesos[$tipo]; $p.Refresh()
            if ($p.HasExited -and (-not $vistos.ContainsKey($tipo))) {
                $codigo = $p.ExitCode
                $hex = $null
                if ($null -ne $codigo) {
                    $hex = [BitConverter]::ToUInt32([BitConverter]::GetBytes([int]$codigo), 0).ToString('X8')
                }
                Registrar @{event='process-exit'; role=$tipo; pid=$p.Id; code=$codigo; hex=$hex}
                $vistos[$tipo] = $true
                Write-Host "$tipo PID=$($p.Id) termino: code=$codigo hex=$hex"
            }
        }
        Registrar @{event='sample'; childAlive=(-not $procesos['child'].HasExited); supervisorAlive=(-not $procesos['supervisor'].HasExited)}
        if ($ForzarArbolPrueba -and (-not $forzado) -and (((Get-Date) - $inicio).TotalSeconds -ge 8)) {
            if (-not ((Identidad-Prueba 'supervisor') -and (Identidad-Prueba 'child'))) {
                throw 'No se valida el arbol de prueba: no se termina ningun proceso.'
            }
            Registrar @{event='controlled-taskkill'; pid=$estado.SupervisorId}
            & "$env:SystemRoot\System32\taskkill.exe" /PID $estado.SupervisorId /T /F | Out-Host
            if ($LASTEXITCODE -ne 0) { throw 'Fallo taskkill del fixture' }
            $forzado = $true
        }
        Start-Sleep -Seconds 1
    } while (((Get-Date) - $inicio).TotalSeconds -lt $Segundos)
    Registrar @{event='observer-finished'; exits=$vistos.Count}
}
finally {
    # Solo el fixture exacto con fecha/ejecutable/firma coincidentes. Nunca PG/servicios.
    if ($LimpiarPrueba) {
        foreach ($tipo in @('child', 'supervisor')) {
            if (Identidad-Prueba $tipo) {
                Registrar @{event='fixture-cleanup'; role=$tipo; pid=$procesos[$tipo].Id}
                Stop-Process -Id $procesos[$tipo].Id -ErrorAction Stop
            }
        }
    }
    foreach ($p in $procesos.Values) { $p.Dispose() }
}
