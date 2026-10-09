# Evidencias ECL-57 / ST-031

Fecha de ejecución: 08/10/2026 (America/Lima).

## Resultado automatizado

El script `frontend/scripts/verify-st031-accessibility.mjs` ejecutó la vista del
conductor en navegadores headless reales. La respuesta de autenticación fue
simulada con un usuario ficticio de rol `CONDUCTOR`; no se utilizaron ni
almacenaron credenciales reales.

| Verificación | Chrome 155.0.8059.40 | Firefox 157.0 |
|---|---:|---:|
| Sin desplazamiento horizontal a 320 px | Aprobado | Aprobado |
| Sin desplazamiento horizontal a 360 px | Aprobado | Aprobado |
| Sin desplazamiento horizontal a 768 y 1280 px | Aprobado | Aprobado |
| Enlace para saltar al contenido | Aprobado | Aprobado |
| Foco visible y navegación mediante `Tab` | Aprobado | Aprobado |
| Controles sin nombre accesible | 0 | 0 |
| Contraste de muestras críticas ≥ 4.5:1 | Aprobado | Aprobado |
| Errores JavaScript de página | 0 | 0 |

Ratios medidos en ambos navegadores:

- etiqueta de ruta: 6.07:1;
- aviso de demostración: 6.70:1;
- alerta operativa: 6.47:1;
- botón principal: 7.13:1.

El detalle estructurado está en [resultados.json](resultados.json).

## Capturas a 360 px

- [Chrome](chrome-itinerario-360.png)
- [Firefox](firefox-itinerario-360.png)

## Límites de la evidencia

La automatización acredita únicamente los recorridos y muestras descritos. No
reemplaza una auditoría WCAG 2.1 AA completa, pruebas con lector de pantalla,
usuarios reales o dispositivos móviles físicos. El itinerario continúa
claramente rotulado como demostración porque el backend no expone aún el
contrato de rutas asignadas.
