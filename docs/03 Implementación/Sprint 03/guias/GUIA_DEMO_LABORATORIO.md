# ECL-68 - Guía de demostración de EcoLogística Lima

> Modo vigente: ejecución de servicios sin ventanas de consola. El historial y
> las investigaciones anteriores están en [Diagnóstico técnico](DIAGNOSTICO_ECL68.md).

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

El arranque crea un supervisor por servicio y ejecuta Python/Node sin ventana
visible de consola. Guarda los PID de servicios y supervisores, además de los
logs de ejecución, en `run` dentro de `ECOLOGISTICA_DEMO_HOME`.
Espera hasta 60 segundos por los servicios y comprueba el puerto, la identidad
y las respuestas HTTP; `/health` debe devolver `status: ok`.
El detalle técnico y las investigaciones anteriores están en
[DIAGNOSTICO_ECL68.md](DIAGNOSTICO_ECL68.md).

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

Validado en Windows 11, en la laptop de desarrollo, sobre el commit `85dd92b` (29/10/2026): arranque con los puertos 5173, 8000 y 55432 activos y `/health` correcto; servicios activos tras 180 s y tras cerrar la consola inicial; inicio de sesión y panel; apagado con los puertos libres y los datos conservados; reinicio con identidad de procesos verificada.

Pendientes:

- Preparación automática de herramientas en una PC nueva.
- Validación en una PC del laboratorio sin administrador (Sprint 4).
- Riesgo para el Sprint 4: `scripts/lab/diagnostico-consola.cs` se compila con `Add-Type` y es necesario para lanzar los servicios sin consola; en una PC con políticas restringidas podría no compilar.

No se afirma haber realizado pruebas en otra computadora.

## 9. Plan para la Review del 30/10/2026

Julio presentará la demostración desde su laptop conectada por HDMI.
El video de la sección 7 estará disponible como respaldo si falla la ejecución
en vivo o la conexión de presentación. La validación en una PC del laboratorio
queda pendiente para Sprint 4.

## 10. Seguridad

No subir a GitHub contraseñas, archivos de base de datos,
tokens ni archivos privados de configuración.

Detalle técnico del diagnóstico: [DIAGNOSTICO_ECL68.md](DIAGNOSTICO_ECL68.md)

[Volver al README principal](../../../../README.md)
