#requires -Version 5.1
param(
    [string]$RaizRepositorio = (Split-Path $PSScriptRoot -Parent)
)

# ECL-90: diagnostico previo al arranque. No lee .env ni cambia servicios.
function Invoke-DockerDiagnostico {
    param([string]$Ejecutable, [string]$Argumentos)
    $proceso = New-Object System.Diagnostics.Process
    $proceso.StartInfo.FileName = $Ejecutable
    $proceso.StartInfo.Arguments = $Argumentos
    $proceso.StartInfo.UseShellExecute = $false
    $proceso.StartInfo.CreateNoWindow = $true
    $proceso.StartInfo.RedirectStandardOutput = $true
    $proceso.StartInfo.RedirectStandardError = $true
    try {
        if (-not $proceso.Start()) { return $null }
        $salida = $proceso.StandardOutput.ReadToEndAsync()
        $errores = $proceso.StandardError.ReadToEndAsync()
        if (-not $proceso.WaitForExit(20000)) {
            $proceso.Kill()
            $proceso.WaitForExit()
            return $null
        }
        # Se descarta stderr: un diagnostico no debe publicar configuracion privada.
        $null = $errores.GetAwaiter().GetResult()
        if ($proceso.ExitCode -ne 0) { return $null }
        return $salida.GetAwaiter().GetResult().Trim()
    }
    catch { return $null }
    finally { $proceso.Dispose() }
}

function Test-PuertoDisponible {
    param([int]$Puerto)
    $escucha = [System.Net.Sockets.TcpListener]::new(
        [System.Net.IPAddress]::Loopback, $Puerto
    )
    try {
        $escucha.Server.ExclusiveAddressUse = $true
        $escucha.Start()
        return $true
    }
    catch { return $false }
    finally { $escucha.Stop() }
}

function Get-InformeEntorno {
    param([string]$Raiz)
    $docker = Get-Command docker -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $docker) {
        [pscustomobject]@{Comprobacion='Docker CLI'; Estado='ERROR'; Detalle='No instalado o fuera de PATH.'}
    }
    else {
        $version = Invoke-DockerDiagnostico $docker.Source '--version'
        $cliDisponible = $version -match '^Docker version [0-9]'
        [pscustomobject]@{
            Comprobacion='Docker CLI'
            Estado=$(if ($cliDisponible) {'OK'} else {'ERROR'})
            Detalle=$(if ($cliDisponible) {'Disponible.'} else {'No responde; revisar instalacion y PATH.'})
        }
        $motor = Invoke-DockerDiagnostico $docker.Source 'info --format "{{.OSType}}"'
        [pscustomobject]@{
            Comprobacion='Motor Docker Linux'
            Estado=$(if ($motor -eq 'linux') {'OK'} else {'ERROR'})
            Detalle=$(if ($motor -eq 'linux') {'Activo y accesible.'} else {'Motor Linux no disponible; revisar Docker Desktop, contexto y WSL.'})
        }
        $compose = Invoke-DockerDiagnostico $docker.Source 'compose version --short'
        $composeDisponible = $compose -match '^v?(\d+)\.'
        if ($composeDisponible) { $composeDisponible = [int]$Matches[1] -ge 2 }
        [pscustomobject]@{
            Comprobacion='Docker Compose'
            Estado=$(if ($composeDisponible) {'OK'} else {'ERROR'})
            Detalle=$(if ($composeDisponible) {'Compose v2 o superior disponible.'} else {'Falta Docker Compose v2 o superior.'})
        }
    }
    $archivoEnv = Join-Path $Raiz '.env'
    $existe = Test-Path -LiteralPath $archivoEnv -PathType Leaf
    [pscustomobject]@{
        Comprobacion='.env de la raiz'
        Estado=$(if ($existe) {'OK'} else {'ERROR'})
        Detalle=$(if ($existe) {'Existe; contenido y valores no inspeccionados.'} else {'Falta; copiar .env.example solo si no existe y completar privadamente.'})
    }
    foreach ($puerto in @(8000, 5173)) {
        $disponible = Test-PuertoDisponible $puerto
        [pscustomobject]@{
            Comprobacion="Puerto $puerto"
            Estado=$(if ($disponible) {'OK'} else {'ERROR'})
            Detalle=$(if ($disponible) {'Disponible en 127.0.0.1.'} else {'No se puede reservar: ocupado, reservado o sin permiso. Identificar al propietario.'})
        }
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    $informe = @(Get-InformeEntorno -Raiz $RaizRepositorio)
    $informe | Format-Table -AutoSize -Wrap
    Write-Output 'Solo preflight: no acredita login, configuracion de .env ni pruebas de integracion.'
    if (@($informe | Where-Object Estado -eq 'ERROR').Count -gt 0) { exit 1 }
    exit 0
}
