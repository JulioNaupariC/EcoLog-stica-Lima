#requires -Version 5.1
# Real subprocess test. Does not start the demo, bind ports or touch PostgreSQL.
param([string]$Node = 'node')
$ErrorActionPreference = 'Stop'
$lab = Split-Path $PSScriptRoot -Parent
if (-not ('EcoLogHeadlessProcess' -as [type])) { Add-Type -Path (Join-Path $lab 'diagnostico-consola.cs') }
$temporal = Join-Path ([IO.Path]::GetTempPath()) ('ECL68-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporal | Out-Null
$anterior = $env:ECL68_STDIO_TEST
$captura = $null
try {
    $env:ECL68_STDIO_TEST = 'synthetic-marker'
    $exe = (Get-Command $Node -CommandType Application -ErrorAction Stop).Source
    $argumentos = '"{0}"' -f (Join-Path $PSScriptRoot 'proceso-stdio.cjs')
    $out = Join-Path $temporal 'out.log'; $err = Join-Path $temporal 'err.log'
    $captura = New-Object EcoLogHeadlessProcess -ArgumentList @($exe, $argumentos, $PSScriptRoot, $out, $err)
    $p = $captura.Process
    if ($p.StartInfo.UseShellExecute -or (-not $p.StartInfo.CreateNoWindow)) { throw 'Flags incorrectos' }
    if (-not $p.WaitForExit(10000)) { throw 'El fixture no recibio EOF' }
    $p.WaitForExit()
    if ($captura.LogFailed) { throw 'Fallo de escritura' }
    if ($p.ExitCode -ne 7) { throw 'Codigo de salida incorrecto' }
    $stdout = Get-Content -LiteralPath $out -Raw
    $stderr = Get-Content -LiteralPath $err -Raw
    if (($stdout -notmatch 'env-ok') -or ($stdout -notmatch 'stdin-eof') -or ($stderr -notmatch 'stderr-ok')) { throw 'Redireccion o entorno incorrectos' }
    Write-Host 'OK: flags sin consola, entorno heredado, EOF, stdout/stderr y salida 7.'
}
finally {
    if ($null -ne $captura) { $captura.Dispose() }
    $env:ECL68_STDIO_TEST = $anterior
    # Only this test's generated directory.
    Remove-Item -LiteralPath $temporal -Recurse -Force
}
