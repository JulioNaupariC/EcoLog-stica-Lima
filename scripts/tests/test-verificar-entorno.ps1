#requires -Version 5.1
# Casos controlados del diagnostico; no equivalen a validar las cinco PC.
$ErrorActionPreference = 'Stop'
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'verificar_entorno.ps1')

function Assert($Condicion, [string]$Mensaje) {
    if (-not $Condicion) { throw $Mensaje }
}

$raizPrueba = Join-Path ([IO.Path]::GetTempPath()) ('ecl90-' + [guid]::NewGuid())
$null = New-Item -ItemType Directory -Path $raizPrueba
try {
    # Reserva real de un puerto efimero: no toca 8000/5173 ni servicios ajenos.
    $reserva = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $reserva.Server.ExclusiveAddressUse = $true
    $reserva.Start()
    $puertoEfimero = $reserva.LocalEndpoint.Port
    try {
        Assert (-not (Test-PuertoDisponible $puertoEfimero)) 'Puerto real ocupado aceptado.'
    }
    finally { $reserva.Stop() }
    Assert (Test-PuertoDisponible $puertoEfimero) 'Puerto liberado sigue reservado.'

    # No Docker, sin .env, puertos disponibles: detectar ambos faltantes.
    function Get-Command { return $null }
    function Test-PuertoDisponible { param([int]$Puerto) return $true }
    $informe = @(Get-InformeEntorno $raizPrueba)
    Assert (@($informe | Where-Object Estado -eq ERROR).Count -eq 2) 'Faltantes no detectados.'

    $secretoCentinela = 'VALOR_PRIVADO_QUE_NO_DEBE_APARECER'
    [IO.File]::WriteAllText((Join-Path $raizPrueba '.env'), $secretoCentinela)
    function Get-Command { return [pscustomobject]@{Source='docker-fixture'} }
    $script:motorPrueba = 'linux'
    $script:composePrueba = 'v2.39.0'
    function Invoke-DockerDiagnostico {
        param([string]$Ejecutable, [string]$Argumentos)
        switch ($Argumentos) {
            '--version' { return 'Docker version 29.9.2, build fixture' }
            'info --format "{{.OSType}}"' { return $script:motorPrueba }
            'compose version --short' { return $script:composePrueba }
            default { throw 'Comando inesperado en el diagnostico.' }
        }
    }
    $informe = @(Get-InformeEntorno $raizPrueba)
    Assert ($informe.Count -eq 6) 'Faltan comprobaciones.'
    Assert (@($informe | Where-Object Estado -eq ERROR).Count -eq 0) 'Entorno valido rechazado.'
    Assert (($informe | Out-String) -notmatch $secretoCentinela) '.env expuesto.'

    $script:motorPrueba = $null
    $informe = @(Get-InformeEntorno $raizPrueba)
    Assert (($informe | Where-Object Comprobacion -eq 'Motor Docker Linux').Estado -eq 'ERROR') 'Motor detenido aceptado.'
    $script:motorPrueba = 'windows'
    $informe = @(Get-InformeEntorno $raizPrueba)
    Assert (($informe | Where-Object Comprobacion -eq 'Motor Docker Linux').Estado -eq 'ERROR') 'Motor Windows aceptado.'
    $script:motorPrueba = 'linux'
    $script:composePrueba = '1.29.2'
    $informe = @(Get-InformeEntorno $raizPrueba)
    Assert (($informe | Where-Object Comprobacion -eq 'Docker Compose').Estado -eq 'ERROR') 'Compose v1 aceptado.'
    $script:composePrueba = 'v2.39.0'
    function Test-PuertoDisponible { param([int]$Puerto) return $Puerto -ne 8000 }
    $informe = @(Get-InformeEntorno $raizPrueba)
    Assert (($informe | Where-Object Comprobacion -eq 'Puerto 8000').Estado -eq 'ERROR') 'Puerto ocupado aceptado.'
    Assert (($informe | Where-Object Comprobacion -eq 'Puerto 5173').Estado -eq 'OK') 'Puerto libre rechazado.'
}
finally {
    # Solo los dos archivos temporales creados arriba; no hay borrado recursivo.
    $archivo = Join-Path $raizPrueba '.env'
    if (Test-Path -LiteralPath $archivo) { Remove-Item -LiteralPath $archivo }
    Remove-Item -LiteralPath $raizPrueba
}
Write-Output 'OK: faltantes, motor detenido/Windows, Compose v1, puertos y privacidad.'
