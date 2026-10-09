# EcoLogística Lima — ST-027 — Guía para José

Ticket: [ECL-53](https://continental-team-il84x39k.atlassian.net/browse/ECL-53).
Rama creada: `feat/ECL-53-st027-formulario-preferencias`.
Entrega: formulario conectado a la API ST-026, pruebas y capturas Chrome/Firefox.
Los archivos ya están en el repositorio; no hace falta copiar un paquete.

## 1. Probar localmente

Desde la raíz, verificar `git status` y `git branch --show-current`.
La API necesita un Cliente existente y una cuenta autorizada de Administrador u
Operador. Configurar `VITE_API_BASE_URL` y el origen CORS como explica el README.
Los clientes sintéticos de las capturas pertenecían a una base temporal que ya
se detuvo; sus IDs no deben utilizarse como datos de producción.

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run test:coverage -- --reporter=default --reporter=junit --outputFile.junit=test-results/frontend.xml
npm.cmd run build
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Ejecutar cada comando y corregir cualquier fallo antes de seguir. El último
mantiene el servidor Vite activo; detenerlo con Ctrl+C al terminar.

## 2. Verificar el formulario

1. Iniciar sesión como Administrador u Operador.
2. Abrir **Preferencias de entrega** desde la navegación.
3. Ingresar el ID de un cliente existente y consultar.
4. Si un campo está sin definir, desmarcar su casilla “Sin…” para escribirlo.
5. Editar horario, referencia y restricciones; guardar y esperar la confirmación.
6. Pulsar **Consultar de nuevo u otro cliente** y consultar el mismo ID para
   recuperar lo guardado desde la API.
7. Limpiar solo una preferencia mediante su casilla y guardar; las demás se
   conservan. Cancelar cambios restaura los datos consultados.
8. Probar texto demasiado largo, ID inválido, cliente inexistente, pérdida de
   conexión y sesión vencida. No deben mostrarse datos de otro cliente ni éxitos
   cuando no se ha confirmado el guardado.
9. Revisar teclado y ancho de 360 px. Conductor, Auditor y Analista no tienen
   acceso a esta vista.

Las capturas realizadas están en
[frontend/evidencias/ECL-53](frontend/evidencias/ECL-53/README.md), con el
[reporte de validación](frontend/VALIDACION_ST027.md).

## 3. Repetir las capturas automatizadas

Esta sección es opcional. La comprobación ya se ejecutó y su evidencia quedó
guardada. El script escribe preferencias y solo debe usarse con clientes y
cuentas sintéticos en un entorno local desechable.

Playwright se instala de forma aislada, sin cambiar package.json ni su lock:

```powershell
Set-Location frontend
npm.cmd install --prefix node_modules/.st027-browser-check --cache .npm-cache --no-package-lock --no-audit --no-fund playwright@1.64.0
node node_modules/.st027-browser-check/node_modules/playwright/cli.js install firefox
Set-Location ..
```

Requiere Chrome instalado y Firefox de Playwright. Preparar un entorno local con
API, PostgreSQL/PostGIS, frontend y dos clientes existentes sintéticos. Crear
privadamente `.env.st027-preview` en la raíz con estas claves:

```text
ECL53_ORIGIN=http://127.0.0.1:5153
ECL53_API=http://127.0.0.1:8053
ECL53_ADMIN_EMAIL=<correo de prueba>
ECL53_ADMIN_PASSWORD=<contraseña de prueba>
ECL53_OPERATOR_EMAIL=<correo de prueba>
ECL53_OPERATOR_PASSWORD=<contraseña de prueba>
ECL53_DRIVER_EMAIL=<correo de prueba>
ECL53_DRIVER_PASSWORD=<contraseña de prueba>
ECL53_CLIENT_A=<UUID del cliente sintético A>
ECL53_CLIENT_B=<UUID del cliente sintético B>
```

Reemplazar todos los marcadores con datos del entorno sintético. No publicar el
archivo: `.env.*` está ignorado por Git. Ambos orígenes deben utilizar
`127.0.0.1`, con CORS habilitado solo para el frontend. El script limpia las tres
preferencias de esos dos clientes al comenzar cada navegador y luego comprueba
guardado, recuperación y aislamiento. No apuntarlo a una base compartida.

Con los servicios activos, ejecutar desde la raíz:

```powershell
node frontend/scripts/verify-preferences.mjs
```

Opcionalmente `ECL53_PREVIEW_SETTINGS` permite indicar otro archivo privado y
`ECL53_PLAYWRIGHT_MODULE` otro módulo Playwright. Los resultados y capturas se
escriben en `frontend/evidencias/ECL-53`; revisar la evidencia antes de subirla.

## 4. Subir a GitHub

Desde la raíz, después de revisar los cambios:

```powershell
git status
git branch --show-current
git diff --check
git add .gitignore GUIA_JOSE_ST027.md frontend/README.md frontend/VALIDACION_ST027.md frontend/src/components/FormField.tsx frontend/src/components/DeliveryPreferencesForm.tsx frontend/src/domain/deliveryPreferencesForm.ts frontend/src/domain/deliveryPreferencesForm.test.ts frontend/src/services/deliveryPreferences.ts frontend/src/services/deliveryPreferences.test.ts frontend/src/pages/DeliveryPreferencesPage.tsx frontend/src/pages/DeliveryPreferencesPage.css frontend/src/pages/DeliveryPreferencesPage.test.tsx frontend/src/pages/OrderCreatePage.tsx frontend/src/app/App.tsx frontend/src/app/App.preferences.test.tsx frontend/scripts/verify-preferences.mjs frontend/evidencias/ECL-53
git diff --cached --stat
git diff --cached --check
git commit -m "feat(ECL-53): implementar formulario de preferencias de entrega"
git push -u origin feat/ECL-53-st027-formulario-preferencias
```

## 5. Crear Pull Request

Abrir el [PR de ST-027 hacia main](https://github.com/JulioNaupariC/EcoLog-stica-Lima/compare/main...feat/ECL-53-st027-formulario-preferencias?expand=1).
Base: `main`. Compare: `feat/ECL-53-st027-formulario-preferencias`.

Título:

```text
feat(ECL-53): implementar formulario de preferencias de entrega — ST-027
```

Descripción para copiar:

```markdown
## Descripción
Permite a Administrador y Operador consultar y actualizar las preferencias de
entrega de un cliente existente desde /clientes/preferencias, usando la API ST-026.

Jira: https://continental-team-il84x39k.atlassian.net/browse/ECL-53

## Cambios
- Formulario de horario preferido, referencia y restricciones de acceso.
- Limpieza explícita con null, PATCH solo de cambios y validación por campo.
- Manejo de carga, guardado, sesión vencida, permisos y errores comprensibles.
- Reutilización de FormField y estilos existentes; regresión de pedidos verificada.
- 62 casos nuevos, script de navegador y 16 capturas de Chrome/Firefox.

## Validación local
- 431 pruebas frontend aprobadas en 25 archivos.
- Typecheck, lint y build aprobados.
- Módulos nuevos con cobertura superior al 80 % en las cuatro métricas.
- Chrome/Administrador y Firefox/Operador: login, GET/PATCH y persistencia reales.
- Formulario a 360 px sin desbordamiento horizontal; Conductor denegado.
- PATCH 503 simulado únicamente para validar el aviso y conservar edición.

## Evidencia
- frontend/VALIDACION_ST027.md
- frontend/evidencias/ECL-53/README.md
- frontend/evidencias/ECL-53/resultados.json
- frontend/evidencias/ECL-53/frontend-tests.xml

## Límites
Consulta mediante UUID: la API actual no proporciona listado de clientes.
El horario es descriptivo; esta entrega no copia preferencias ni modifica pedidos.

## Antes de integrar
- [ ] Verificar GitHub Actions y los controles SAST del PR.
- [ ] Adjuntar el enlace de la ejecución CI al ticket.
- [ ] Obtener revisión y aprobación de un compañero.
```

Seleccionar un compañero en **Reviewers**. Adjuntar el PR y las capturas en Jira.
La ejecución remota de CI solo se puede dar por aprobada después de observar
su resultado en GitHub Actions.
