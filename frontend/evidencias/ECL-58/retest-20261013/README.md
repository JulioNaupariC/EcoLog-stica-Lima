# Reprueba ECL-58 / ST-032 con el rediseño ECL-22 — 13/10/2026

Ejecución de `backend/scripts/verify_driver_offline.py --pg-port 15432` (clúster
PostgreSQL 16.15 desechable en el puerto 15432, fuera de los rangos reservados por
Windows en esta máquina) con Playwright 1.64.0: Chrome 155.0.8059.40 y Firefox 157.0,
la misma versión de Firefox que la ejecución del 09/10/2026.

Resultado: 10 rondas por navegador de reporte sin conexión, recarga, reconexión,
ACK perdido y API no disponible; 20 reportes persistidos una sola vez; casos
negativos reales (otra cuenta 404, operador 403); migración en
`0010_extend_driver_audit_events`.

| Observable | Chrome | Firefox |
|---|---|---|
| Reporte pendiente sin conexión | [captura](chrome-01-pendiente-offline.png) | [captura](firefox-01-pendiente-offline.png) |
| Confirmado tras reconexión | [captura](chrome-02-confirmado-reconexion.png) | [captura](firefox-02-confirmado-reconexion.png) |
| API no disponible y reintento | [captura](chrome-03-api-no-disponible.png) | [captura](firefox-03-api-no-disponible.png) |
| Otra cuenta sin paradas en caché | [captura](chrome-04-otra-cuenta.png) | [captura](firefox-04-otra-cuenta.png) |

Registros: [resultados.json](resultados.json), [persistencia.json](persistencia.json),
[browser.log](browser.log), [api.log](api.log) y [build.log](build.log).

Antes de esta ejecución, la reprueba con el rediseño fallaba de forma intermitente en
Firefox (1 de 5 pasaba): el navegador recuperaba `navigator.onLine` sin emitir el
evento `online`, de modo que la sincronización automática no se reactivaba. Con la
interfaz anterior (`83b28bd`) la misma prueba pasó en la única ejecución realizada.
`useOnlineStatus` y `useReportSynchronization` ahora vuelven a comprobar la
conexión cada 5 s mientras el dispositivo está sin conexión; desde ese cambio, 3 de 3
ejecuciones completas pasaron (esta es la tercera).

La evidencia del 09/10/2026 en la carpeta superior no se modifica.

[← Volver al README principal](../../../../README.md)
