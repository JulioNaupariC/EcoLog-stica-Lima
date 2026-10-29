# ECL-68 - Guia de demostracion de EcoLogistica Lima

## 1. Objetivo

Facilitar la ejecucion local de EcoLogistica Lima en Windows,
sin utilizar Docker ni requerir permisos de administrador.

## 2. Componentes

- PostgreSQL 16 y PostGIS 3.5: puerto 55432.
- Backend Python y FastAPI: puerto 8000.
- Frontend React y Vite: puerto 5173.

## 3. Requisitos previos

Actualmente los scripts requieren que PostgreSQL, PostGIS,
Python, Node.js y las dependencias del proyecto esten preparados.

La preparacion automatica desde cero en otra computadora
todavia esta pendiente.

## 4. Iniciar la demostracion

Abrir PowerShell en la carpeta principal del proyecto.

Si se utiliza la instalacion local del disco D:

```powershell
$env:ECOLOGISTICA_DEMO_HOME = "D:\EcoLogisticaDemo"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\lab\levantar-demo.ps1"
```

Los servicios se utilizan mediante:

- Aplicacion: http://127.0.0.1:5173
- Verificacion del backend: http://127.0.0.1:8000/health

El script de inicio se encuentra en proceso de mejora porque
FastAPI y React no siempre permanecen activos al iniciarse
automaticamente. En esas situaciones se utiliza el arranque manual.

## 5. Verificacion funcional

Se comprobo en una computadora de desarrollo:

- Inicio de sesion como administrador de demostracion.
- Visualizacion de 5 vehiculos.
- Visualizacion de 4 conductores.
- Visualizacion de 20 pedidos.
- Funcionamiento del backend y frontend.
- Apagado de servicios mediante el script correspondiente.

## 6. Detener la demostracion

```powershell
$env:ECOLOGISTICA_DEMO_HOME = "D:\EcoLogisticaDemo"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\lab\detener-demo.ps1"
```

El apagado conserva la informacion de PostgreSQL.

## 7. Evidencia en video

Demostracion grabada:

https://drive.google.com/file/d/1sx-a97hDRjneDUoZ5CvitxmUftrTEZIK/view?usp=sharing

## 8. Estado y pendientes

La demostracion fue ejecutada en la computadora de desarrollo.

Pendientes:
- Estabilizar el arranque automatico del backend y frontend.
- Preparar automaticamente las herramientas en una PC nueva.
- Validar la ejecucion en una PC de laboratorio sin administrador.

No se afirma haber realizado pruebas en otra computadora.

## 9. Seguridad

No subir a GitHub contrasenas, archivos de base de datos,
tokens ni archivos privados de configuracion.

[Volver al README principal](../../../../README.md)
