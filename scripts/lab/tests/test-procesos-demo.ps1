#requires -Version 5.1
# Pruebas sin servicios reales ni taskkill. No equivalen a una prueba Windows.
$ErrorActionPreference = 'Stop'
$raiz = Split-Path $PSScriptRoot -Parent
$funciones = @{}
foreach ($archivo in @('levantar-demo.ps1', 'detener-demo.ps1', 'procesos-demo.ps1', 'servicio-demo.ps1', 'observar-demo.ps1')) {
    $tokens = $null; $errores = $null
    $ast = [Management.Automation.Language.Parser]::ParseFile((Join-Path $raiz $archivo), [ref]$tokens, [ref]$errores)
    if ($errores.Count) { throw ($errores | Out-String) }
    foreach ($fn in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]}, $false)) {
        $funciones[$fn.Name] = $fn.Extent.Text
    }
}
foreach ($nombre in @('Es-ProcesoDelProyecto', 'Verificar-PuertoDelProyecto', 'Detener-Arbol', 'Detener-ServicioWeb', 'Esperar-HTTP')) {
    Invoke-Expression $funciones[$nombre]
}
function Assert($Condicion, [string]$Mensaje) { if (-not $Condicion) { throw $Mensaje } }
function Join-Path($Path, $ChildPath) { return "$Path\$ChildPath" }
$repo = 'C:\Users\Julio Demo\EcoLog-stica-Lima'
$base = 'D:\Eco Demo'
$run = "$base\run"
$env:SystemRoot = 'C:\Windows'
$python = "$repo\backend\.venv\Scripts\python.exe"
$node = "$base\tools\node-v22.18.0-win-x64\node.exe"
$vite = "$repo\frontend\node_modules\vite\bin\vite.js"
$backendCmd = '"{0}" -m uvicorn app.main:create_app --factory --app-dir "{1}\backend" --host 127.0.0.1 --port 8000' -f $python, $repo
$frontendCmd = '"{0}" "{1}" --host 127.0.0.1 --port 5173 --strictPort' -f $node, $vite
$casos = @(
    @($python, $backendCmd, 'backend', $true),
    @('C:\Python\python.exe', $backendCmd, 'backend', $true),
    @($node, $frontendCmd, 'frontend', $true),
    @('C:\Windows\System32\cmd.exe', 'cmd /c pg_ctl start', 'backend', $false),
    @('C:\Windows\System32\cmd.exe', ('cmd /c ' + $backendCmd), 'backend', $false),
    @('C:\Otro\python.exe', $backendCmd.Replace($repo, 'C:\Otro'), 'backend', $false),
    @($node, $frontendCmd.Replace($repo, 'C:\Otro'), 'frontend', $false),
    @('C:\Otro\node.exe', $frontendCmd, 'frontend', $false),
    @($python, ('"{0}" -m uvicorn app.main:create_app --port 8000' -f $python), 'backend', $false),
    @($python, 'python otro.py', 'backend', $false),
    @('', '', 'backend', $false)
)
foreach ($caso in $casos) {
    $p = [pscustomobject]@{ExecutablePath=$caso[0]; CommandLine=$caso[1]}
    Assert ((Es-ProcesoDelProyecto $p $caso[2]) -eq $caso[3]) "Identidad incorrecta: $($caso[0])"
}
# Verificar PID reutilizado sin invocar taskkill (la rama debe retornar antes).
function Get-CimInstance { return [pscustomobject]@{ExecutablePath=$python;CommandLine=$backendCmd} }
function Test-Path { return $true }
function Get-Content { return '{"ProcessId":13824,"StartTicks":1}' }
function Get-Process { return [pscustomobject]@{StartTime=[datetime]'2026-10-29T12:00:00Z'} }
Assert (-not (Detener-Arbol 13824 backend -Guardado)) 'Se acepto un PID reutilizado'
function Get-Content { return 'corrupt-json' }
Assert (-not (Detener-Arbol 13824 backend -Guardado)) 'Se acepto metadata corrupta'
function Get-CimInstance { return $null }
Assert (Detener-Arbol 13824 backend -Guardado) 'PID desaparecido no reconocido'
# Orquestacion: PID primero, respaldo por puerto y aviso si persiste un ajeno.
$script:eventos = [Collections.Generic.List[string]]::new()
function Get-Content { return '13824' }
function Remove-Item { $script:eventos.Add('remove') }
function Detener-Arbol([int]$IdProceso, [string]$Servicio, [switch]$Guardado) {
    $script:eventos.Add("stop:$IdProceso"); return $true
}
function Get-NetTCPConnection { $script:eventos.Add('port'); return [pscustomobject]@{OwningProcess=17520} }
Assert (-not (Detener-ServicioWeb 8000 backend)) 'Se anuncio cierre con puerto ocupado'
Assert (($script:eventos -join ',') -eq 'stop:13824,remove,port,stop:17520,port') 'Orden PID/puerto incorrecto'
$script:eventos.Clear()
function Get-Content { return 'invalid-pid' }
$null = Detener-ServicioWeb 8000 backend
Assert (($script:eventos -join ',') -eq 'port,stop:17520,port') 'PID invalido no controlado'
function Invoke-WebRequest { return [pscustomobject]@{StatusCode=200;Content='{"status":"ok"}'} }
Assert (Esperar-HTTP 'http://test/health' -Backend) 'HTTP backend correcto rechazado'
Assert (Esperar-HTTP 'http://test/') 'HTTP frontend correcto rechazado'
function Start-Sleep { }
function Invoke-WebRequest { return [pscustomobject]@{StatusCode=200;Content='{"status":"wrong"}'} }
Assert (-not (Esperar-HTTP 'http://test/health' -Backend -segundos 0)) 'Health incorrecto aceptado'
function Invoke-WebRequest { throw 'Offline' }
Assert (-not (Esperar-HTTP 'http://test/' -segundos 0)) 'Error HTTP aceptado'
# El observador debe rechazar acciones destructivas para los servicios reales.
$osAnterior = $env:OS
try {
    $env:OS = 'Windows_NT'
    foreach ($accion in @('ForzarArbolPrueba', 'LimpiarPrueba')) {
        $rechazado = $false
        try {
            $opciones = @{}; $opciones[$accion] = $true
            & "$raiz/observar-demo.ps1" @opciones
        }
        catch { $rechazado = ($_.Exception.Message -match 'solo se permiten para el fixture') }
        Assert $rechazado "Observador permitio $accion sobre servicio real"
    }
}
finally { $env:OS = $osAnterior }
Write-Host 'OK: sintaxis (5 scripts), identidad (11 casos), PID obsoleto/corrupto/ausente, orden PID-puerto, HTTP.'
