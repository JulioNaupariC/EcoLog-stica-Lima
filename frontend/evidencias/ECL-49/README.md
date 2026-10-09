# Evidencias ECL-49 / ST-023

Formulario y listado de conductores. Trazabilidad: ECL-49 → ECL-9 / US-003.
Ver [validación técnica](../../VALIDACION_ST023.md) y [resultados](resultados.json).

Chrome 154.0.8037.98 con ADMINISTRADOR y Firefox 157.0 con OPERADOR.
Verificación registrada el 9 de octubre de 2026, 07:20:18 UTC.
Las cuentas y perfiles son sintéticos, en una base local de desarrollo separada.
No se incluyen contraseñas ni sesiones en estas evidencias.

| Estado | Chrome | Firefox |
|---|---|---|
| Carga del listado | [Chrome](chrome-01-carga.png) | [Firefox](firefox-01-carga.png) |
| Listado inicial | [Chrome](chrome-02-listado-inicial.png) | [Firefox](firefox-02-listado-inicial.png) |
| Formulario de registro | [Chrome](chrome-03-registro.png) | [Firefox](firefox-03-registro.png) |
| Validación de campos | [Chrome](chrome-04-validacion.png) | [Firefox](firefox-04-validacion.png) |
| Registro confirmado | [Chrome](chrome-05-registro-confirmado.png) | [Firefox](firefox-05-registro-confirmado.png) |
| DNI duplicado rechazado | [Chrome](chrome-06-duplicado.png) | [Firefox](firefox-06-duplicado.png) |
| Consulta del perfil | [Chrome](chrome-07-perfil.png) | [Firefox](firefox-07-perfil.png) |
| Edición confirmada | [Chrome](chrome-08-edicion-confirmada.png) | [Firefox](firefox-08-edicion-confirmada.png) |
| Listado móvil | [Chrome](chrome-09-listado-360.png) | [Firefox](firefox-09-listado-360.png) |
| Perfil móvil | [Chrome](chrome-10-perfil-360.png) | [Firefox](firefox-10-perfil-360.png) |
| Error y reintento móvil | [Chrome](chrome-11-error-360.png) | [Firefox](firefox-11-error-360.png) |
| Acceso denegado al conductor | [Chrome](chrome-12-conductor-denegado.png) | [Firefox](firefox-12-conductor-denegado.png) |

Las capturas 09, 10, 11 y 12 usan un viewport de 360 px; los demás estados se capturan
en escritorio de 1280 px. Son capturas funcionales del frontend, no exportaciones de Figma.
Se comprobó ausencia de desbordamiento horizontal en los estados capturados.

Login, registro, consulta, actualización, conflicto por DNI y denegación de permisos
usan el backend HTTP real. La carga añade una demora controlada y la captura de error
simula un GET 503; el reintento posterior consulta la API real.

El recorrido comprueba que editar el teléfono conserva la disponibilidad original y
que retirar disponibilidad envía ambos extremos como null. El alta de Firefox utiliza
licencia vencida y verifica que no habilita la asignación.

Para reproducir: `scripts/verify-drivers.mjs`, con la configuración privada y el
entorno descritos en la validación técnica. El script genera perfiles sintéticos
persistentes; no ejecutar sobre datos reales.
