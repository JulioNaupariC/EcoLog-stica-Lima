# Evidencias de interfaz — ECL-56 / ST-030

Capturas de la aplicación React en ejecución, con viewport móvil de 360 × 800 px
y escritorio de 1280 × 900 px. Las imágenes son de página completa: su altura
puede superar la altura del viewport. Los datos y alertas son de demostración.

Se comprobó login real de conductor contra el backend de desarrollo. La denegación
al Auditor usa una respuesta de login simulada; no acredita la autorización del
backend para ese rol. Las capturas de login anónimo se toman con campos vacíos.

| Caso | Chrome | Firefox |
|---|---|---|
| Itinerario, siguiente parada y alerta | [Imagen](chrome-01-itinerario-360.png) | [Imagen](firefox-01-itinerario-360.png) |
| Detalle y alerta de la parada | [Imagen](chrome-02-detalle-360.png) | [Imagen](firefox-02-detalle-360.png) |
| Filtro y siguiente parada independiente | [Imagen](chrome-03-filtro-360.png) | [Imagen](firefox-03-filtro-360.png) |
| Estado sin asignación | [Imagen](chrome-04-sin-asignacion-360.png) | [Imagen](firefox-04-sin-asignacion-360.png) |
| Escritorio | [Imagen](chrome-05-escritorio.png) | [Imagen](firefox-05-escritorio.png) |
| Ruta sin sesión: login | [Imagen](chrome-06-sin-sesion-360.png) | [Imagen](firefox-06-sin-sesion-360.png) |
| Auditor: acceso denegado, login simulado | [Imagen](chrome-07-auditor-denegado-360.png) | [Imagen](firefox-07-auditor-denegado-360.png) |

Versiones y resultado automatizado en [resultados.json](resultados.json).
Chrome usa el navegador instalado en el equipo; Firefox usa la distribución
de prueba de Playwright. Son pruebas headless de escritorio con viewport móvil,
no pruebas en un teléfono físico ni una auditoría completa WCAG.

La aprobación humana del incremento y la conexión con datos reales siguen pendientes.
