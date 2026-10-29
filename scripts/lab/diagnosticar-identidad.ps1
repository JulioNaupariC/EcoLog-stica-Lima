#requires -Version 5.1
# Solo consultas de procesos/puertos y registro con campos permitidos. No detener nada.
param([ValidateSet('backend', 'frontend')][string]$Servicio = 'backend')
$ErrorActionPreference = 'Stop'
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$base = $env:ECOLOGISTICA_DEMO_HOME
if (-not $base) { $base = Join-Path $env:LOCALAPPDATA 'EcoLogisticaDemo' }
$base = [IO.Path]::GetFullPath($base)
$run = Join-Path $base 'run'
. (Join-Path $PSScriptRoot 'procesos-demo.ps1')
$puerto = 8000
if ($Servicio -eq 'frontend') { $puerto = 5173 }
$aceptado = Verificar-PuertoDelProyecto $puerto $Servicio
Write-Host "Validacion de $Servicio en $puerto = $aceptado"
if (-not $aceptado) { exit 1 }
