# Evidencias ECL-74 — formulario de incidencias

Ejecución real del navegador: 26/10/2026 (America/Lima). Solo datos sintéticos;
la sesión de prueba es una pista local de UI y la API HTTP local es un fixture,
sin credenciales ni autorización real. No sustituye la prueba con Docker/API/BD.

[Resultados estructurados](browser-results.json) registra la fecha UTC real,
versiones, foco en el primer faltante, selección de severidad con teclado,
GPS rechazado, alternativa por parada, recarga offline, ausencia de desborde
horizontal y una sola operación/POST por combinación.

| Navegador y tema, 360 px | Faltantes | Formulario | Recarga offline | Confirmación |
|---|---|---|---|---|
| Chrome claro | [Captura](chrome-light-360-faltantes.png) | [Captura](chrome-light-360-formulario.png) | [Captura](chrome-light-360-offline-recarga.png) | [Captura](chrome-light-360-confirmada.png) |
| Chrome oscuro | [Captura](chrome-dark-360-faltantes.png) | [Captura](chrome-dark-360-formulario.png) | [Captura](chrome-dark-360-offline-recarga.png) | [Captura](chrome-dark-360-confirmada.png) |
| Firefox claro | [Captura](firefox-light-360-faltantes.png) | [Captura](firefox-light-360-formulario.png) | [Captura](firefox-light-360-offline-recarga.png) | [Captura](firefox-light-360-confirmada.png) |
| Firefox oscuro | [Captura](firefox-dark-360-faltantes.png) | [Captura](firefox-dark-360-formulario.png) | [Captura](firefox-dark-360-offline-recarga.png) | [Captura](firefox-dark-360-confirmada.png) |

## Reproducción

Instalar `playwright-core` en una ruta de herramientas externa o ignorada y
tener Chrome y el Firefox compatible de Playwright. No se añadió dependencia
al proyecto ni se cambió el lockfile. Desde `frontend/`:

```powershell
$env:VITE_API_BASE_URL='http://127.0.0.1:8000'
npm run build
npm run preview -- --host 127.0.0.1 --port 5173 --strictPort
```

En otra terminal, también en `frontend/`, con el puerto 8000 libre:

```powershell
$env:CAPTURE_PLAYWRIGHT_MODULE='RUTA_ABSOLUTA_A_PLAYWRIGHT_CORE/index.mjs'
node scripts/capture-incidents.mjs
```

El script abre y cierra su API sintética en `127.0.0.1:8000` y lanza navegadores
headless. `CHROME_PATH` permite indicar otra instalación de Chrome. Para nuevas
ejecuciones, usar una carpeta de salida distinta: los archivos versionados de
evidencias no se deben sobrescribir. El script acepta `ECL74_OUTPUT` para ello.

No se certifica una auditoría WCAG completa ni la campaña de ECL-76 por estas
cuatro ejecuciones.

[↑ Validación ST-041](<../../VALIDACION_ST041.md>)

[↑ Índice del Sprint 3](<../../../README.md>)

[← Volver al README principal](<../../../../../../README.md>)
