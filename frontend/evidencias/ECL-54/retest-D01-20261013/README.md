# Reprueba de D-01 — ECL-54 / ST-028 — 13/10/2026

Ejecución real del 13/10/2026 con datos sintéticos, API FastAPI y PostgreSQL
locales aislados. Chrome 155.0.8059.40 (Administrador) y Firefox 146.0.1,
compilación de Playwright 1.58.2 (Operador). Node 22.18.0.

Esta carpeta no sustituye la evidencia del 09/10/2026 de la carpeta superior,
que registra la brecha D-01 y se conserva sin cambios.

| Observable | Chrome | Firefox |
|---|---|---|
| Cliente sin preferencias (P1) | [captura](chrome-01-sin-preferencias.png) | [captura](firefox-01-sin-preferencias.png) |
| Persistencia de preferencias válidas | [captura](chrome-02-guardado.png) | [captura](firefox-02-guardado.png) |
| Consulta posterior de valores guardados | [captura](chrome-03-recuperado.png) | [captura](firefox-03-recuperado.png) |
| Longitud inválida sin cambios persistidos | [captura](chrome-04-validacion.png) | [captura](firefox-04-validacion.png) |
| Ancho 360 px y navegación con Tab | [captura](chrome-05-movil-360.png) | [captura](firefox-05-movil-360.png) |
| Aviso y conservación de edición; error simulado solo en PATCH | [captura](chrome-06-error-503.png) | [captura](firefox-06-error-503.png) |
| Buscador sin opciones para un ID inexistente; API 404 | [captura](chrome-07-cliente-inexistente.png) | [captura](firefox-07-cliente-inexistente.png) |
| Conductor sin acceso a preferencias | [captura](chrome-08-acceso-denegado.png) | [captura](firefox-08-acceso-denegado.png) |
| P8: preferencias propuestas como contexto, sin copiar | [captura](chrome-09-P8-propuesta-disponible.png) | [captura](firefox-09-P8-propuesta-disponible.png) |
| P8: referencia copiada solo tras la acción explícita | [captura](chrome-10-P8-referencia-copiada.png) | [captura](firefox-10-P8-referencia-copiada.png) |

[resultados.json](resultados.json) registra `P8OrderProposalAvailable: true`,
`P8ExplicitReferenceCopy`, `P8WindowsUnchanged` y `P8ClientUnchanged`.

Análisis y matriz: [VALIDACION_ST028.md](<../../../../docs/03 Implementación/Sprint 2/validaciones/VALIDACION_ST028.md>).

[← Volver al README principal](../../../../README.md)
