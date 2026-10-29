#requires -Version 5.1
# Funciones compartidas: importar no inicia ni detiene procesos.
function Patron-ArgumentoLiteral([string]$Valor) {
    $literal = [regex]::Escape($Valor)
    # Python reconstruye argv: conserva comillas solo si son necesarias.
    if ($Valor -match '\s') { return ('"' + $literal + '"') }
    return ('(?:"' + $literal + '"|' + $literal + ')')
}

function Es-FirmaBackend([string]$Comando) {
    $appDir = Patron-ArgumentoLiteral (Join-Path $repo 'backend')
    return (($Comando -match '\s-m\s+uvicorn\s+app\.main:create_app(?:\s|$)') -and
        ($Comando -match ('\s--app-dir\s+' + $appDir + '(?:\s|$)')) -and
        ($Comando -match '\s--port\s+8000(?:\s|$)'))
}

function Es-DescendienteBackend($Proceso) {
    # Nunca fiarse solo del numero ParentProcessId: puede estar reutilizado.
    try {
        $estado = Get-Content -LiteralPath (Join-Path $run 'backend.process.json') -Raw | ConvertFrom-Json
        if ($estado.Trial -ne 'Ninguna') { return $false }
        $raiz = Get-CimInstance Win32_Process -Filter "ProcessId = $($estado.ProcessId)" -ErrorAction Stop
        $actualRaiz = Get-Process -Id $estado.ProcessId -ErrorAction Stop
        if (($actualRaiz.StartTime.ToUniversalTime().Ticks -ne [long]$estado.StartTicks) -or
            ($raiz.ExecutablePath -ine (Join-Path $repo 'backend\.venv\Scripts\python.exe')) -or
            (-not (Es-FirmaBackend ([string]$raiz.CommandLine)))) { return $false }
        $actual = $Proceso
        $visitados = @{}
        for ($nivel = 0; $nivel -lt 8; $nivel++) {
            if ($visitados.ContainsKey([int]$actual.ProcessId)) { return $false }
            $visitados[[int]$actual.ProcessId] = $true
            if (($actual.ExecutablePath -notmatch '(?i)\\python\.exe$') -or
                (-not (Es-FirmaBackend ([string]$actual.CommandLine)))) { return $false }
            $hijo = Get-Process -Id $actual.ProcessId -ErrorAction Stop
            if ($actual.ProcessId -eq $estado.ProcessId) {
                return ($hijo.StartTime.ToUniversalTime().Ticks -eq [long]$estado.StartTicks)
            }
            $padre = Get-CimInstance Win32_Process -Filter "ProcessId = $($actual.ParentProcessId)" -ErrorAction Stop
            if (-not $padre) { return $false }
            $padreVivo = Get-Process -Id $padre.ProcessId -ErrorAction Stop
            if ($hijo.StartTime.ToUniversalTime().Ticks -lt $padreVivo.StartTime.ToUniversalTime().Ticks) { return $false }
            $actual = $padre
        }
    }
    catch { return $false }
    return $false
}

function Obtener-IdentidadProceso($Proceso, [string]$Servicio) {
    $motivo = 'missing-process'
    $aceptado = $false
    if ($Proceso) {
        $comando = [string]$Proceso.CommandLine
        $ejecutable = [string]$Proceso.ExecutablePath
        $motivo = 'missing-command-or-executable'
        if ($comando -and $ejecutable) {
            $motivo = 'signature-mismatch'
            if (($Servicio -eq 'backend') -and (Es-FirmaBackend $comando)) {
                if ($ejecutable -ieq (Join-Path $repo 'backend\.venv\Scripts\python.exe')) {
                    $aceptado = $true; $motivo = 'backend-project-venv'
                }
                elseif (Es-DescendienteBackend $Proceso) {
                    $aceptado = $true; $motivo = 'backend-verified-descendant'
                }
                else { $motivo = 'backend-unverified-lineage' }
            }
            if ($Servicio -eq 'frontend') {
                $node = Join-Path $base 'tools\node-v22.18.0-win-x64\node.exe'
                $vite = Patron-ArgumentoLiteral (Join-Path $repo 'frontend\node_modules\vite\bin\vite.js')
                if (($ejecutable -ieq $node) -and
                    ($comando -match ($vite + '\s+--host\s+127\.0\.0\.1\s+--port\s+5173(?:\s|$)'))) {
                    $aceptado = $true; $motivo = 'frontend-project-node'
                }
            }
        }
    }
    return [pscustomobject]@{ Aceptado=$aceptado; Motivo=$motivo }
}

function Es-ProcesoDelProyecto($Proceso, [string]$Servicio) {
    return (Obtener-IdentidadProceso $Proceso $Servicio).Aceptado
}

function Verificar-PuertoDelProyecto([int]$Puerto, [string]$Servicio) {
    $conexiones = @(Get-NetTCPConnection -LocalPort $Puerto -State Listen -ErrorAction SilentlyContinue)
    if ($conexiones.Count -eq 0) { return $false }
    foreach ($idProceso in @($conexiones | Select-Object -ExpandProperty OwningProcess -Unique)) {
        $proceso = Get-CimInstance Win32_Process -Filter "ProcessId = $idProceso" -ErrorAction SilentlyContinue
        $identidad = Obtener-IdentidadProceso $proceso $Servicio
        # Campos permitidos; nunca volcar CommandLine ni el entorno.
        $registro = [ordered]@{ utc=[datetime]::UtcNow.ToString('o'); event='port-identity';
            port=$Puerto; pid=$idProceso; parentId=$proceso.ParentProcessId;
            accepted=$identidad.Aceptado; reason=$identidad.Motivo }
        $registro | ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $run "$Servicio.identity.jsonl") -Encoding ASCII
        Write-Host "[IDENTIDAD] puerto=$Puerto PID=$idProceso padre=$($proceso.ParentProcessId) aceptado=$($identidad.Aceptado) motivo=$($identidad.Motivo)"
        if (-not $identidad.Aceptado) { return $false }
    }
    return $true
}
