# Capturas ECL-54 / ST-028

Ejecución real del 09/10/2026 con datos sintéticos y API/PostgreSQL aislados.
Chrome 154.0.8037.98 (Administrador) y Firefox 157.0 (Operador).
Se comprobó además Conductor en ambos navegadores.

| Captura por navegador | Observable |
|---|---|
| 01-sin-preferencias | Cliente sin preferencias |
| 02-guardado | Persistencia de preferencias válidas |
| 03-recuperado | Consulta posterior de valores guardados |
| 04-validacion | Longitud inválida sin cambios persistidos |
| 05-movil-360 | Ancho móvil y navegación con Tab |
| 06-error-503 | Aviso y conservación de edición; error simulado en PATCH |
| 07-cliente-inexistente | 404 real |
| 08-acceso-denegado | Conductor sin acceso a la proyección |
| 09-P8-propuesta-ausente | Brecha: formulario de pedidos sin propuesta de preferencias |

[resultados.json](resultados.json) indica el alcance de las comprobaciones
aprobadas y P8OrderProposalAvailable false. No expresa que todos los BDD aprobaron.
Ver [la matriz y registro D-01](../../../backend/VALIDACION_ST028.md).

## Reproducción

Requiere API/frontend locales, Playwright, Chrome y Firefox.
Preparar una base desechable exclusiva ecologistica_ecl54_preview_test,
migrada a head, con dos clientes y cuentas sintéticas ADMINISTRADOR, OPERADOR
y CONDUCTOR. El script modifica preferencias SOLO de esos dos clientes.
No usar datos reales ni una base compartida.

Configurar un archivo privado ignorado .env.ecl54-preview en la raíz con:
DATABASE_URL de esa base, ECL54_ORIGIN y ECL54_API locales, ECL54_CLIENT_A/B,
ECL54_ADMIN_EMAIL/PASSWORD, ECL54_OPERATOR_EMAIL/PASSWORD y
ECL54_DRIVER_EMAIL/PASSWORD. Usar CORS_ALLOWED_ORIGINS que autorice el origen.
No publicar ese archivo. El instrumento usa los prefijos ADMIN y OPERATOR
respectivamente en Chrome y Firefox.

Desde frontend, configurar ECL54_PLAYWRIGHT_MODULE con la ruta al index.mjs
de Playwright y PLAYWRIGHT_BROWSERS_PATH donde esté Firefox si corresponde.
ECL54_PREVIEW_SETTINGS permite elegir la ruta del archivo privado.

```powershell
node scripts/verify-preferences-bdd.mjs
npm run test:coverage
npm run lint
```

La repetición sobrescribe capturas ECL-54; preservar la evidencia existente
antes de repetir. Solo PATCH 503 se intercepta; login, GET/PATCH, 404 y denegación
usan la API real. Ancho y teclado no equivalen a una auditoría WCAG completa.
