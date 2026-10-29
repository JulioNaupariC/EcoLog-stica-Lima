# ECL-68 - Guía de demostración de EcoLogística Lima

## 1. Objetivo

Facilitar la ejecución local de EcoLogística Lima en Windows,
sin utilizar Docker ni requerir permisos de administrador.

## 2. Componentes

- PostgreSQL 16 y PostGIS 3.5: puerto 55432.
- Backend Python y FastAPI: puerto 8000.
- Frontend React y Vite: puerto 5173.

## 3. Requisitos previos

Actualmente los scripts requieren que PostgreSQL, PostGIS,
Python, Node.js y las dependencias del proyecto estén preparados.

La preparación automática desde cero en otra computadora
todavía está pendiente.

## 4. Iniciar la demostración

Abrir PowerShell en la carpeta principal del proyecto.

Las herramientas y la base deben estar preparadas previamente. Configurar
`DATABASE_URL` en el entorno de la consola; no escribir la contraseña en el
script, en argumentos, en logs ni en archivos del repositorio. El script ya no
lee `run/postgres-password.txt`. Para la instalación local del disco D,
introducir la contraseña de la base mediante un diálogo seguro:

```powershell
$env:ECOLOGISTICA_DEMO_HOME = "D:\EcoLogisticaDemo"
$credencial = Get-Credential -UserName "demo_admin" -Message "Contraseña local de PostgreSQL"
$claveURL = [Uri]::EscapeDataString($credencial.GetNetworkCredential().Password)
$env:DATABASE_URL = "postgresql+psycopg://demo_admin:$claveURL@127.0.0.1:55432/ecologistica_demo"
Remove-Variable credencial, claveURL
try {
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\lab\levantar-demo.ps1"
}
finally {
    Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
}
```

Los servicios se utilizan mediante:

- Aplicación: http://127.0.0.1:5173
- Verificación del backend: http://127.0.0.1:8000/health

El inicio crea un supervisor Windows PowerShell 5.1 independiente y minimizado
por servicio (`scripts/lab/servicio-demo.ps1`). Cada supervisor inicia directamente
Python o Node con `Start-Process -NoNewWindow`, redirige stdout/stderr a archivos
y permanece esperando al proceso real. No se usa `cmd /c` ni `start`: se evita
confundir el PID de un intermediario con el del servicio y se mantienen vivos
los propietarios de las redirecciones aunque termine la consola de inicio.

En `run`, dentro de `ECOLOGISTICA_DEMO_HOME`, se guardan:

- `backend.pid` y `frontend.pid`: PID real de Python o Node, no de `cmd.exe`.
- `*.process.json`: PID, fecha de creación y PID del supervisor, sin credenciales.
- `*.out.log` y `*.err.log`: salida del arranque actual.
- `*.lifecycle.log`: inicio y salida con PID, hora y código de salida.
- `*.lock`: bloqueo exclusivo mientras vive el supervisor; no borrarlo durante la ejecución.

Se espera hasta 60 segundos por publicación del PID, por comprobación de puerto
y por comprobación HTTP. `/health` debe devolver `status: ok` y React HTTP 200.
También se comprueba que el propietario del puerto pertenece al proyecto.
El backend recibe `DATABASE_URL` solo por herencia del entorno; el supervisor la
retira tras crear Python. React no la hereda. No se escribe en argumentos ni
registros de diagnóstico del supervisor.

Estos cambios requieren una prueba personal en la laptop Windows de Julio.
No se declara superada esa prueba.

## 5. Verificación funcional

Evidencia previa a estas correcciones, registrada en una computadora de desarrollo:

- Inicio de sesión como administrador de demostración.
- Visualización de 5 vehículos.
- Visualización de 4 conductores.
- Visualización de 20 pedidos.
- Funcionamiento del backend y frontend.
- Apagado de servicios mediante el script correspondiente.

## 6. Detener la demostración

```powershell
$env:ECOLOGISTICA_DEMO_HOME = "D:\EcoLogisticaDemo"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\lab\detener-demo.ps1"
```

El apagado prioriza los PID guardados y detiene sus árboles mediante
`taskkill /PID ... /T /F`. Comprueba el ejecutable, la firma del comando del
proyecto y la fecha de creación del PID guardado antes de detenerlos. Si falta el PID o está obsoleto, busca por puerto
y aplica la misma validación; deja intactos los procesos que no puede identificar.
Un proceso iniciado manualmente debe usar las rutas absolutas de las herramientas
y de `vite.js` para que pueda identificarse con seguridad. El backend debe incluir
`--app-dir` con la ruta absoluta de `backend` y `--port 8000`.
El apagado conserva la información de PostgreSQL. Su arranque y cierre siguen
usando `pg_ctl -D` con el directorio de datos existente; no se ejecutan migraciones,
reinicializaciones ni borrados de datos.

## 7. Evidencia en video

Demostración grabada:

https://drive.google.com/file/d/1sx-a97hDRjneDUoZ5CvitxmUftrTEZIK/view?usp=sharing

## 8. Estado y pendientes

La demostración fue ejecutada en la computadora de desarrollo.

Pendientes:

- Validar personalmente en la laptop Windows el arranque, HTTP, cierre y nuevo arranque tras estas correcciones.
- Preparar automáticamente las herramientas en una PC nueva.
- Validar la ejecución en una PC de laboratorio sin administrador: pendiente para Sprint 4.

No se afirma haber realizado pruebas en otra computadora.

## 9. Plan para la Review del 30/10/2026

Julio presentará la demostración desde su laptop conectada por HDMI.
El video de la sección 7 estará disponible como respaldo si falla la ejecución
en vivo o la conexión de presentación. Antes de la Review se probarán en la
laptop el inicio, acceso web, cierre y nuevo arranque.
La validación en una PC del laboratorio queda pendiente para Sprint 4.

## 10. Seguridad

No subir a GitHub contraseñas, archivos de base de datos,
tokens ni archivos privados de configuración.

[Volver al README principal](../../../../README.md)

## 11. Diagnóstico de la prueba de Windows pendiente

El reporte de Windows 11 indica que PostgreSQL respondió en 55432, pero Uvicorn
arrancó y después desapareció; el PID 13824 ya no existía. El `cmd.exe` 17520
correspondía a PostgreSQL y no debe tratarse como backend o frontend.
El log disponible no permite atribuir con certeza la salida a una causa concreta.
La revisión anterior guardaba el PID del `cmd /c` y no registraba la salida del
servicio. Además, React no llegaba a lanzarse si fallaba antes FastAPI.

Para repetir la prueba: iniciar con el bloque de la sección 4, cerrar la consola
que inició la demo y abrir otra PowerShell. Esperar al menos 60 segundos y ejecutar:

```powershell
$env:ECOLOGISTICA_DEMO_HOME = "D:\EcoLogisticaDemo"
Invoke-RestMethod http://127.0.0.1:8000/health
(Invoke-WebRequest http://127.0.0.1:5173/ -UseBasicParsing).StatusCode
Get-NetTCPConnection -LocalPort 55432,8000,5173 -State Listen |
    Select-Object LocalPort, OwningProcess
Get-Content "$env:ECOLOGISTICA_DEMO_HOME\run\backend.process.json"
Get-Content "$env:ECOLOGISTICA_DEMO_HOME\run\frontend.process.json"
```

Comprobar el login, detener con la sección 6 y repetir el arranque. Si falla,
conservar `*.lifecycle.log` y revisar localmente `*.err.log`; no publicar el
entorno ni registros sin comprobar antes que no contienen datos privados.
La sintaxis y las pruebas simuladas pueden ejecutarse sin iniciar servicios:

```powershell
powershell.exe -NoProfile -File .\scripts\lab\tests\test-procesos-demo.ps1
python scripts/check_docs.py
```

Estas verificaciones no declaran superada la prueba real de Windows 11.

## 12. Desaparición de React y del supervisor: investigación pendiente

La prueba real de Windows 11 del commit `5cb1d3b` llegó a `DEMO INICIADA`.
Aproximadamente 60 segundos después, React y su supervisor habían desaparecido,
sin `exited`, con stderr vacío; FastAPI y PostgreSQL seguían activos.
Esto no demuestra una salida normal ni identifica quién terminó los procesos.
La prueba anterior de Linux no validaba el cierre de consola o los Jobs de Windows.

Se conserva el lanzamiento actual para medir su comportamiento. Una ventana
minimizada no garantiza separación de un Job del lanzador. `-NoNewWindow` hace
que Node comparta la consola del supervisor: cerrarla puede afectar a ambos.
Un cierre forzado puede omitir `catch`, `finally` y cualquier registro de salida.

En Vite 8.3.0, `setupSIGTERMListener` registra `process.stdin.on("end", ...)`
cuando `CI` no es `true`; ese callback cierra el servidor y sale del proceso.
Ahora el supervisor del frontend establece `CI=true`, sin modificar el entorno
de la consola llamante. Evita ese mecanismo concreto, pero NO demuestra que
fuera la causa del fallo reportado: por sí solo no explica la desaparición
sin `exited` del supervisor.

La instrumentación nueva añade:

- `heartbeat` cada cinco segundos mientras vive el supervisor.
- `supervisor-failed stage=...` y `supervisor-finally` para fallos capturados.
- `*.console.log`: señales de consola observadas por un callback C# nativo
  (0 Ctrl+C, 1 Ctrl+Break, 2 cierre de ventana, 5 logoff, 6 apagado).
- `consolePids` e `inJob` en lifecycle. `inJob=True` no revela las políticas del
  Job ni demuestra que este haya terminado el árbol.
- Un observador **en otra consola**, que abre handles de ambos procesos antes
  de su muerte y conserva el código de salida decimal y hexadecimal. No registra
  comandos, variables de entorno ni contraseñas. No reinicia servicios.

El callback es observacional: devuelve el control a Windows y no bloquea las
señales. La ausencia de `console-control` NO excluye cierre externo, fallo nativo,
terminación de un Job, pérdida del almacenamiento o terminación forzada.
Tampoco un código cero demuestra, por sí solo, salida voluntaria.

### Prueba controlada, sin tocar los servicios ni PostgreSQL

Abrir Windows PowerShell 5.1 desde Inicio, fuera de VS Code, en la raíz del repo.
Usar la ruta de herramientas ya preparada. No se solicita ni se cambia contraseña.
Los fixtures solo mantienen un temporizador Node, sin puertos, red ni base de datos;
sus archivos usan el prefijo `frontend-prueba-`, separado del servicio real.

```powershell
$env:ECOLOGISTICA_DEMO_HOME = "D:\EcoLogisticaDemo"
$lab = Join-Path (Get-Location) "scripts\lab"
function Iniciar-Prueba([string]$Caso) {
    Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" `
        -ArgumentList @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', ('"{0}\servicio-demo.ps1"' -f $lab),
            '-Servicio', 'frontend', '-Prueba', $Caso) `
        -WindowStyle Normal -PassThru
}

# 1. Node termina voluntariamente con cero tras ocho segundos.
$p = Iniciar-Prueba Normal
& "$lab\observar-demo.ps1" -Prueba Normal -Segundos 20 -SupervisorIdEsperado $p.Id

# 2. El supervisor lanza una excepcion capturada; Node sigue vivo hasta la limpieza.
$p = Iniciar-Prueba FalloSupervisor
& "$lab\observar-demo.ps1" -Prueba FalloSupervisor -Segundos 20 -SupervisorIdEsperado $p.Id -LimpiarPrueba

# 3. El observador termina solo el arbol del fixture validado, tras ocho segundos.
$p = Iniciar-Prueba Espera
& "$lab\observar-demo.ps1" -Prueba Espera -Segundos 20 -SupervisorIdEsperado $p.Id -ForzarArbolPrueba -LimpiarPrueba

# 4. Cerrar MANUALMENTE la ventana titulada "ECL-68 fixture Espera supervisor=...".
# Mantener abierta la consola del observador durante los 90 segundos.
$p = Iniciar-Prueba Espera
& "$lab\observar-demo.ps1" -Prueba Espera -Segundos 90 -SupervisorIdEsperado $p.Id -LimpiarPrueba
```

`-LimpiarPrueba` y `-ForzarArbolPrueba` se rechazan para servicios reales. Antes
de terminar un fixture comprueban PID, fecha de creación, ejecutable y firma del
comando. Si la identidad no coincide, no terminan ese proceso. No se usan
búsquedas amplias por nombre ni se toca PostgreSQL.

| Caso | Evidencia esperada |
|---|---|
| Normal | lifecycle `exited code=0` y `supervisor-finally`; observador ve salir ambos. |
| FalloSupervisor | `supervisor-failed stage=controlled-failure`, `supervisor-finally`, supervisor código 1; Node sigue vivo hasta `fixture-cleanup`. |
| Forzado | observador registra `controlled-taskkill` y luego ambas salidas; normalmente no hay `exited` ni `supervisor-finally`. |
| Cierre de consola | puede registrar `console-control signal=2`; observador conserva las salidas aunque no exista registro final. |
| Fallo real sin marcador | clasificar como terminación abrupta de origen no determinado; no atribuir automáticamente a consola, antivirus o Job. |

### Persistencia del frontend real: observar durante 180 segundos

Consola A: arrancar con el bloque seguro de la sección 4. No cambiar PostgreSQL,
los datos ni las contraseñas. Conservar las ventanas minimizadas de los supervisores.

Consola B: abrir otra ventana Windows PowerShell desde Inicio (no una pestaña
de la ventana A), en la raíz del repo:

```powershell
$env:ECOLOGISTICA_DEMO_HOME = "D:\EcoLogisticaDemo"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\lab\observar-demo.ps1 -Servicio frontend -Segundos 180
```

Cuando B muestre `Observando`, cerrar SOLO la consola A; no cerrar B ni las
ventanas de los supervisores. Al terminar la observación:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
(Invoke-WebRequest http://127.0.0.1:5173/ -UseBasicParsing).StatusCode
Get-NetTCPConnection -LocalPort 55432,8000,5173 -State Listen |
    Select-Object LocalPort, OwningProcess
Get-Content "$env:ECOLOGISTICA_DEMO_HOME\run\frontend.lifecycle.log" -Tail 60
Get-Content "$env:ECOLOGISTICA_DEMO_HOME\run\frontend.console.log" -ErrorAction SilentlyContinue
Get-ChildItem "$env:ECOLOGISTICA_DEMO_HOME\run\frontend.observer.*.jsonl" |
    Sort-Object LastWriteTime | Select-Object -Last 1 | Get-Content
```

Repetir una vez sin cerrar A para comparar. Si ambos desaparecen sin marcador,
el observador acota el momento y el código, pero no identifica al autor de un
`TerminateProcess`. Revisar localmente el Visor de eventos (Aplicación: errores
1000/1001 en esa hora) puede aportar evidencia de un fallo nativo; su ausencia
no prueba cierre externo. No habilitar auditorías que requieran administrador.

La prueba real de Windows 11 queda pendiente de confirmación de Julio.

Verificaciones de esta revisión en Linux: sintaxis PowerShell 7 (no un host 5.1),
compilación del callback C#, pruebas simuladas de identidad y barreras de seguridad,
y fixtures reales con salida normal, excepción de supervisor y SIGKILL del árbol.
Un observador Python independiente distinguió las salidas 0, 1 y señal 9.
El observador PowerShell de handles y el callback de consola requieren validación
en Windows; no se ejecutaron sus llamadas nativas en Linux.
También se reprodujo con Vite 8.3.0 y un servidor aislado que stdin EOF cierra el
proceso sin `CI=true`, y que con `CI=true` permanece activo. Esto verifica el
mecanismo de stdin, no la causa del incidente de Windows 11.
