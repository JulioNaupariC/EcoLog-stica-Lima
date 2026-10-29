#requires -Version 5.1
# Funciones compartidas: no iniciar ni detener procesos al importar este archivo.
function Es-ProcesoDelProyecto($Proceso, [string]$Servicio) {
    if (-not $Proceso) { return $false }
    $comando = [string]$Proceso.CommandLine
    $ejecutable = [string]$Proceso.ExecutablePath
    if ($Servicio -eq 'backend') {
        $python = Join-Path $repo 'backend\.venv\Scripts\python.exe'
        $appDir = [regex]::Escape('"' + (Join-Path $repo 'backend') + '"')
        $firma = ($comando -match '\s-m\s+uvicorn\s+app\.main:create_app(?:\s|$)')
        # El redirector del venv puede tener un python.exe hijo fuera del repo.
        # En ese caso exigir --app-dir absoluto del proyecto y el puerto de demo.
        $binarioValido = (($ejecutable -ieq $python) -or ($ejecutable -match '(?i)\\python\.exe$'))
        $proyectoValido = (($comando -match ('\s--app-dir\s+' + $appDir + '(?:\s|$)')) -and
            ($comando -match '\s--port\s+8000(?:\s|$)'))
        return ($firma -and $binarioValido -and $proyectoValido)
    }
    if ($Servicio -eq 'frontend') {
        $node = Join-Path $base 'tools\node-v22.18.0-win-x64\node.exe'
        $vite = [regex]::Escape('"' + (Join-Path $repo 'frontend\node_modules\vite\bin\vite.js') + '"')
        return (($ejecutable -ieq $node) -and
            ($comando -match ($vite + '\s+--host\s+127\.0\.0\.1\s+--port\s+5173(?:\s|$)')))
    }
    return $false
}

function Verificar-PuertoDelProyecto([int]$Puerto, [string]$Servicio) {
    $conexiones = @(Get-NetTCPConnection -LocalPort $Puerto -State Listen -ErrorAction SilentlyContinue)
    if ($conexiones.Count -eq 0) { return $false }
    foreach ($idProceso in @($conexiones | Select-Object -ExpandProperty OwningProcess -Unique)) {
        $proceso = Get-CimInstance Win32_Process -Filter "ProcessId = $idProceso" -ErrorAction SilentlyContinue
        if (-not (Es-ProcesoDelProyecto $proceso $Servicio)) { return $false }
    }
    return $true
}
