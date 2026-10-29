# ECL-68 - Guía de demostración de EcoLogística Lima

> Modo vigente: ejecución sin consola (sección 14). Las pruebas de ventanas de
> las secciones 12 y 13 documentan revisiones anteriores.

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

## 13. Reinicio: separar identidad del listener y cierre de consola

Estado confirmado por Julio en Windows 11 sobre `978fe8d`: estabilidad, cierre de
la consola inicial y apagado superados. **El reinicio no está validado**: el
backend arrancó, se rechazó su identidad y el supervisor recibió señal 2.
Los tiempos 14:18:28 -05:00 y 19:18:28 Z corresponden al mismo instante.
`CTRL_CLOSE_EVENT` precedió a la salida registrada, pero no identifica al emisor.
`inJob=True` solo indica pertenencia, no la política del Job ni su responsabilidad.

Se corrigieron dos limitaciones sin cambiar el método de lanzamiento ni los
plazos de espera:

- La firma ahora admite `--app-dir "C:\EcoLog\backend"` y
  `--app-dir C:\EcoLog\backend` cuando no hay espacios. El redirector del
  entorno virtual puede reconstruir argv y eliminar comillas innecesarias.
  Con espacios sigue exigiéndose el argumento completo entre comillas.
- Un `python.exe` fuera del venv solo se acepta si tiene la firma del backend y
  pertenece a una cadena Python viva hasta el PID raíz guardado: se comprueban
  el ejecutable del venv del proyecto, la fecha de creación de la raíz, los
  argumentos, la relación padre-hijo y el orden temporal de cada enlace.
  Una raíz reutilizada, un linaje inaccesible o un Python ajeno se rechazan.

La misma regla se utiliza para arrancar y para autorizar el apagado. No se
acepta un listener solo por su puerto o por llamarse Python. La reconstrucción
de comillas es un fallo reproducido en pruebas simuladas, no una atribución
confirmada del rechazo anterior: faltaba la identidad del listener de esa prueba.

El supervisor conserva el handle del proceso desde el lanzamiento y escribe
`code=unknown` si el código no está disponible, en vez de dejarlo vacío.
Registra el PID del lanzador y su terminación cuando puede observarla.
`launcher.lifecycle.log` conserva inicio, fallo con fase y salida del lanzador;
`*.identity.jsonl` explica las decisiones de identidad sin volcar comandos ni
credenciales. El observador registra cambios del PID listener, su padre y el
motivo de aceptación, además del PID raíz que ya vigilaba.

No se ignora la señal 2 ni se reinicia silenciosamente el backend. Revisar el
código no encontró una llamada del lanzador que cierre la ventana del supervisor;
un `throw` mantiene el fallo visible y no ejecuta `taskkill` ni `CloseMainWindow`.
La causa del cierre de consola sigue sin determinarse. Si la señal persiste,
se compararán su hora, el fallo/fin del lanzador y los eventos del observador.

### A. Comprobar identidad sin cerrar ninguna consola

Actualizar la rama, ejecutar las pruebas y conservar abiertas tanto la consola
inicial como las ventanas de supervisores:

```powershell
git switch feat/ECL-68-demo-laboratorio
git pull --ff-only origin feat/ECL-68-demo-laboratorio
powershell.exe -NoProfile -File .\scripts\lab\tests\test-procesos-demo.ps1
python scripts/check_docs.py
```

Arrancar mediante el bloque seguro de la sección 4. En otra ventana PowerShell,
en la raíz del repositorio (ajustar únicamente la ruta de herramientas si difiere):

```powershell
$env:ECOLOGISTICA_DEMO_HOME = "D:\EcoLogisticaDemo"
powershell.exe -NoProfile -File .\scripts\lab\diagnosticar-identidad.ps1 -Servicio backend
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\lab\observar-demo.ps1 -Servicio backend -Segundos 90
```

Se espera `aceptado=True`, con `backend-project-venv` o
`backend-verified-descendant`. Si el listener es el hijo, su PID puede diferir
del `.pid`, pero la cadena verificada debe terminar en esa raíz. Si se rechaza,
no cerrar ventanas ni ejecutar apagados para intentar resolverlo; recoger:

```powershell
Get-Content "$env:ECOLOGISTICA_DEMO_HOME\run\backend.identity.jsonl" -Tail 20
Get-Content "$env:ECOLOGISTICA_DEMO_HOME\run\launcher.lifecycle.log" -Tail 20
Get-Content "$env:ECOLOGISTICA_DEMO_HOME\run\backend.lifecycle.log" -Tail 30
Get-Content "$env:ECOLOGISTICA_DEMO_HOME\run\backend.console.log" -Tail 10
Get-ChildItem "$env:ECOLOGISTICA_DEMO_HOME\run\backend.observer.*.jsonl" |
    Sort-Object LastWriteTime | Select-Object -Last 1 | Get-Content
```

Los registros son de campos permitidos. No publicar `DATABASE_URL`, el entorno
ni una lista de comandos completa de todos los procesos. Si el fallo ocurre antes
de poder abrir el observador, iniciar el observador primero en otra consola:
espera hasta 30 segundos a la publicación del registro. En una repetición con
registros anteriores, pasar `-SupervisorIdEsperado` con el PID nuevo; no usar un
observador conectado a un arranque anterior como evidencia del nuevo.

Comparación adicional para separar el error del cierre automático del host:
con `DATABASE_URL` configurada mediante el mismo bloque seguro de la sección 4,
sustituir solo la invocación del arranque por:

```powershell
powershell.exe -NoLogo -NoProfile -NoExit -ExecutionPolicy Bypass -File .\scripts\lab\levantar-demo.ps1
```

`-NoExit` deja visible el error y mantiene el prompt del lanzador. No elimina la
validación ni captura el fallo como éxito. No cerrar esa ventana ni el supervisor
mientras se recogen los registros. Comparar con la ejecución normal, sin lanzar
una segunda copia sobre un backend ya activo. Si la señal solo aparece al cerrar
la ventana o al terminar el host, hay correlación reproducible, todavía no una
identificación del emisor. Si ocurre con todas las ventanas abiertas, conservar
la evidencia y no atribuirla automáticamente al error del lanzador.

### B. Reproducir solo la señal de consola, sin backend ni PostgreSQL

Usar el fixture `Espera` de la sección 12, cuya ventana tiene título inequívoco:

```powershell
$env:ECOLOGISTICA_DEMO_HOME = "D:\EcoLogisticaDemo"
$lab = Join-Path (Get-Location) "scripts\lab"
$p = Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" `
    -ArgumentList @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', ('"{0}\servicio-demo.ps1"' -f $lab),
        '-Servicio', 'frontend', '-Prueba', 'Espera') -WindowStyle Normal -PassThru
& "$lab\observar-demo.ps1" -Prueba Espera -Segundos 30 -SupervisorIdEsperado $p.Id -LimpiarPrueba
```

Primera ejecución: no cerrar ninguna ventana. El fixture debe seguir vivo hasta
la limpieza registrada al final. Segunda ejecución del mismo bloque: cerrar
únicamente la ventana titulada `ECL-68 fixture Espera supervisor=...`; conservar
el observador. Comparar `frontend-prueba-Espera.console.log`, lifecycle y el
archivo observer nuevo. Se espera la señal 2 observada y luego las salidas;
no interviene la validación del puerto 8000. La falta de una escritura no descarta
la señal, porque Windows puede terminar el proceso antes de completar el registro.

### C. Repetir el reinicio completo

Una vez hecha A, usar el apagado normal ya validado de la sección 6; comprobar
que no quedan listeners web. Volver a arrancar con la sección 4 y repetir A.
No reinicializar PostgreSQL, no borrar su directorio ni archivos de contraseña.
Si el reinicio falla, conservar el motivo de identidad y la señal por separado.
Solo se considerará validado el reinicio cuando Julio lo confirme en Windows 11.

## 14. Servicios sin consola: validación pendiente de reinicio

La prueba real de `c4a9134` aceptó `backend-verified-descendant` y
`frontend-project-node`. El lanzador terminó su bloque `finally` a las
14:38:23.664 -05:00; el supervisor recibió señal 2 a las 14:38:26.938, unos
3,27 segundos después. Python salió con `0xC000013A` ocho milisegundos más tarde.
Es compatible con terminación por control de consola. `launcher-finally` no
prueba por sí solo que el proceso lanzador ya hubiese terminado, y la señal no
identifica quién cerró la consola.

La revisión actual usa `System.Diagnostics.ProcessStartInfo` con
`UseShellExecute=false` y `CreateNoWindow=true` para el supervisor y Python/Node.
No se usa `WindowStyle Hidden/Minimized`, `cmd start`, WMI ni tareas programadas.
Ocultar una ventana conserva su consola; WMI no conserva automáticamente el
entorno privado del llamante y una tarea programada añade configuración persistente.
La API de procesos de .NET funciona desde Windows PowerShell 5.1 sin administrador.

El supervisor sigue siendo propietario de las redirecciones. Un pequeño ejecutor
C# drena stdout/stderr asincrónicamente a los archivos de `run`, sin callbacks
PowerShell en hilos sin runspace ni tuberías cuyo propietario sea el lanzador.
El stdin se cierra explícitamente. Se conserva `CI=true` para Vite y la herencia
privada de `DATABASE_URL` solo hacia el backend. No se añaden credenciales a
argumentos o registros. Los fallos de escritura se informan como fallos.

No se suprimen señales: cuando no hay consola no hay handler que instalar; si
se ejecuta el supervisor manualmente con una consola, el handler anterior sigue
siendo observacional. `supervisor-start` debe indicar `hasConsole=False` con el
lanzador nuevo. El JSON incluye `SupervisorHasConsole` y `ChildCreateNoWindow`.
El último campo es la configuración del proceso creado, no una medición de todos
los descendientes del redirector Python. Comprobar también que no aparece una
ventana propia de un descendiente durante la prueba.

Esto separa la vida de los servicios de la consola original. No evade políticas
de Jobs de Windows: un Job configurado para terminar sus miembros sigue siendo
una causa distinta que habría que confirmar si persiste el fallo. No se solicita
breakaway ni se ignoran cierres. La identidad y las verificaciones HTTP permanecen.
No se modifica el arranque/cierre de PostgreSQL ni el directorio de datos.

### Prueba reproducible de Windows PowerShell 5.1

Primero actualizar y comprobar los scripts (sin iniciar servicios de prueba):

```powershell
git switch feat/ECL-68-demo-laboratorio
git pull --ff-only origin feat/ECL-68-demo-laboratorio
$env:ECOLOGISTICA_DEMO_HOME = "D:\EcoLogisticaDemo"
powershell.exe -NoProfile -File .\scripts\lab\tests\test-procesos-demo.ps1
powershell.exe -NoProfile -File .\scripts\lab\tests\test-sin-consola.ps1 -Node "$env:ECOLOGISTICA_DEMO_HOME\tools\node-v22.18.0-win-x64\node.exe"
python scripts/check_docs.py
```

`test-sin-consola.ps1` ejecuta solo un fixture de stdout/stderr, EOF, herencia de
una variable sintética y código de salida 7. No usa red, puertos o PostgreSQL.
No demuestra aún persistencia tras cerrar la consola.

1. Usar el apagado normal de la sección 6 para no conservar supervisores de una
   revisión anterior. No borrar archivos de datos ni cambiar contraseñas.
2. En una ventana A de PowerShell abierta desde Inicio, ejecutar el bloque seguro
   de la sección 4 con `powershell.exe -NoProfile ... -File levantar-demo.ps1`.
   No usar `-NoExit` en esta prueba. Debe volver al prompt con `DEMO INICIADA`.
   No deben aparecer ventanas de los supervisores o de Python/Node.
3. En otra ventana B, desde la raíz del repo, guardar los registros actuales:

```powershell
$env:ECOLOGISTICA_DEMO_HOME = "D:\EcoLogisticaDemo"
$run = Join-Path $env:ECOLOGISTICA_DEMO_HOME 'run'
$b = Get-Content "$run\backend.process.json" -Raw | ConvertFrom-Json
$f = Get-Content "$run\frontend.process.json" -Raw | ConvertFrom-Json
$b | Select-Object ProcessId, SupervisorId, SupervisorHasConsole, ChildCreateNoWindow
$f | Select-Object ProcessId, SupervisorId, SupervisorHasConsole, ChildCreateNoWindow
if (($b.SupervisorHasConsole -ne $false) -or ($f.SupervisorHasConsole -ne $false)) {
    throw 'Un supervisor tiene consola o pertenece a una revision anterior; no dar la prueba por superada.'
}
powershell.exe -NoProfile -File .\scripts\lab\diagnosticar-identidad.ps1 -Servicio backend
powershell.exe -NoProfile -File .\scripts\lab\diagnosticar-identidad.ps1 -Servicio frontend
```

4. Cerrar únicamente A. Mantener B y tomar una muestra cada 15 segundos durante
   180 segundos; cualquier error invalida esa ejecución. No se reinicia nada:

```powershell
$limite = (Get-Date).AddSeconds(180)
do {
    foreach ($e in @($b, $f)) {
        $s = Get-Process -Id $e.SupervisorId -ErrorAction Stop
        if ($s.StartTime.ToUniversalTime().Ticks -ne [long]$e.SupervisorStartTicks) {
            throw 'El PID del supervisor fue reutilizado'
        }
    }
    if ((Invoke-RestMethod http://127.0.0.1:8000/health -TimeoutSec 5).status -ne 'ok') {
        throw 'Backend sin salud'
    }
    if ((Invoke-WebRequest http://127.0.0.1:5173/ -UseBasicParsing -TimeoutSec 5).StatusCode -ne 200) {
        throw 'Frontend sin HTTP 200'
    }
    powershell.exe -NoProfile -File .\scripts\lab\diagnosticar-identidad.ps1 -Servicio backend
    if ($LASTEXITCODE -ne 0) { throw 'Identidad backend rechazada' }
    powershell.exe -NoProfile -File .\scripts\lab\diagnosticar-identidad.ps1 -Servicio frontend
    if ($LASTEXITCODE -ne 0) { throw 'Identidad frontend rechazada' }
    Write-Host "$(Get-Date -Format o) HTTP e identidades correctos"
    Start-Sleep -Seconds 15
} while ((Get-Date) -lt $limite)
```

5. Revisar los `*.lifecycle.log` actuales por PID y hora: deben continuar los
   heartbeats tras `launcher-finally` y aparecer `launcher-exited` cuando se pudo
   observar. No interpretar señales antiguas de `*.console.log` como señales del
   arranque actual. Si falla, conservar esos registros y repetir con el observador
   de la sección 13 en otra ventana; no concluir automáticamente que es un Job.
6. Ejecutar el apagado normal, comprobar los puertos libres y volver a ejecutar
   los pasos 2 a 5. Se necesitan tanto la persistencia como el segundo arranque.

La estabilidad de 180 segundos y el apagado pasaron en una ejecución anterior,
pero la nueva revisión sin consola y el reinicio completo requieren confirmación
real de Julio en Windows 11.
