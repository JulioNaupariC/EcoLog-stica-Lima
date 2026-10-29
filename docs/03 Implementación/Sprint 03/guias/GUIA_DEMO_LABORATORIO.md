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

El inicio lanza FastAPI y React mediante procesos independientes de `cmd.exe`,
con ventanas minimizadas, PID en `run/backend.pid` y `run/frontend.pid`, y logs
`backend.out.log`, `backend.err.log`, `frontend.out.log` y `frontend.err.log`
en `run`, dentro de `ECOLOGISTICA_DEMO_HOME`. Espera hasta 60 segundos por
comprobación de puerto y por comprobación HTTP: `/health` debe responder
con `status: ok` y React debe devolver HTTP 200.

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
`taskkill /PID ... /T /F`. Comprueba el ejecutable y la firma del comando del
proyecto antes de detenerlos. Si falta el PID o está obsoleto, busca por puerto
y aplica la misma validación; deja intactos los procesos que no puede identificar.
Un proceso iniciado manualmente debe usar las rutas absolutas de las herramientas
y de `vite.js` para que pueda identificarse con seguridad.
El apagado conserva la información de PostgreSQL.

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
