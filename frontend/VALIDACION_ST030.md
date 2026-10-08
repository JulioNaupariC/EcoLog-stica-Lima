# Validación local — ECL-56 / ST-030

Fecha: 08/10/2026, America/Lima.
Trazabilidad: **ECL-56 / ST-030 → ECL-22 / EN-004**.
Rama existente del [PR #24](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/24):
`feature/st-030-itinerario-movil`. Se conserva para actualizar el mismo PR;
la documentación y los nuevos mensajes de commit utilizan el ticket ECL-56.

## Diseño de referencia

ECL-55/ST-029, aprobado según la confirmación de Giancarlo en esta conversación.
Esta referencia no sustituye el registro de aprobación del equipo en Jira/Figma.

- [Mi itinerario](https://www.figma.com/design/VhDMfCVBzDfpJWWhbOCbWh/?node-id=5-125).
- [Detalle de parada](https://www.figma.com/design/VhDMfCVBzDfpJWWhbOCbWh/?node-id=5-163).
- [Sin itinerario](https://www.figma.com/design/VhDMfCVBzDfpJWWhbOCbWh/?node-id=5-194).
- [Guía visual](https://www.figma.com/design/VhDMfCVBzDfpJWWhbOCbWh/?node-id=5-21).

## Incremento corregido

- Cuatro paradas ficticias con estados, numeración original y filtro.
- Siguiente parada explícita: primera no completada por secuencia, independiente
  del filtro y de la selección de detalle.
- Alertas operativas ficticias en el itinerario y alertas aplicables en el detalle.
- Información de entrega, indicaciones, regreso al itinerario y estado sin asignación.
- Identificación visible de datos de demostración en todas las vistas.
- Tipografía, colores, tarjetas, botones de 48 px y foco según la guía visual.
- Navegación por teclado con foco en el título tras cambiar de vista.
- Acceso existente limitado a CONDUCTOR; no se cambia la autenticación.

La selección de una tarjeta ya no se presenta como sustituto de la siguiente
parada; el aviso de demostración y las indicaciones tampoco sustituyen las alertas.

## Resultados técnicos

| Comprobación | Resultado |
|---|---|
| `npm run typecheck` | Aprobado |
| `npm run lint` | Aprobado |
| `npm run test:coverage` | 264 pruebas aprobadas en 10 archivos |
| Pantalla, dominio y datos demo | 100% en líneas, sentencias, funciones y ramas |
| Cobertura global | Líneas 99.37%, sentencias 99.07%, funciones 100%, ramas 98.43% |
| `npm run build` | Aprobado |

Las pruebas cubren orden y ausencia de siguiente parada, asociación de alertas,
filtros sin alterar secuencia, detalle/regreso, foco y teclado, estado sin asignación,
filtro vacío y ruta completada. Las pruebas existentes de acceso por rol permanecen.

## Navegadores y capturas

Chrome **154.0.8037.98** instalado y Firefox **157.0**, distribución de prueba de
Playwright 1.64.0, ejecutados en modo headless con contextos nuevos.

En ambos: login real de conductor, apertura de itinerario, siguiente parada y
alertas, detalle y regreso por teclado, cuatro filtros, estado sin asignación,
regreso al ejemplo y escritorio. Se verificó acceso anónimo y denegación al
Auditor con login simulado. No hubo errores de ejecución de página ni
desbordamiento horizontal en las vistas comprobadas.

[Capturas de interfaz y resultados](evidencias/ECL-56/README.md).
Esto acredita estos recorridos en las versiones registradas, no una auditoría
completa WCAG, validación con participantes o funcionamiento en móviles físicos.

## Integración y dependencia de backend

El backend local disponible expone salud, login/logout, pedidos y vehículos.
No expone endpoints para consultar itinerarios asignados ni alertas operativas.
Por ello, la autenticación se integra realmente y el itinerario usa una muestra
aislada, rotulada como ficticia. No se inventó una API ni se presentan los datos
como asignaciones reales. El modelo `DemoItinerary` no es un contrato de backend.

La conexión a rutas reales requiere acordar contrato, autorización por conductor
y asignación, y manejo de estados de carga/error. Sigue pendiente antes de aceptar
esa integración. No se implementa ST-023 ni se cambia el backend para ampliar alcance.
GPS y sincronización offline no están incluidos; ST-032/ECL-58 aborda sincronización.

## Repetir la comprobación local de navegadores

Requiere API y Vite activos en `127.0.0.1:8000` y `127.0.0.1:5173`, Chrome instalado
y la cuenta ficticia de desarrollo en `.env.st030`, ignorado por Git. El script
lee `ST030_DRIVER_EMAIL` y `ST030_DRIVER_PASSWORD` sin imprimirlos. No adjuntar
ese archivo, credenciales o cookies a evidencias.

Desde `frontend/`, instalar la herramienta de prueba en una subcarpeta ignorada:

```powershell
npm install --prefix node_modules/.ecl56-browser-check --no-audit --no-fund --ignore-scripts playwright@1.64.0
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) 'node_modules/.ecl56-browser-check/browsers'
node node_modules/.ecl56-browser-check/node_modules/playwright/cli.js install firefox
node scripts/verify-driver-itinerary.mjs
```

No cambia `package.json` ni `package-lock.json` del proyecto. La herramienta
regenera las capturas y `resultados.json` de esta verificación local.

El entorno exclusivo de demostración conserva la base existente del proyecto:

```powershell
docker compose -p ecologistica-lima-st030-giancarlo --env-file .env.st030 up -d --wait db backend
```

Se comprobó PostgreSQL 16/PostGIS y revisión Alembic `0006_create_cliente_pedido`
al preparar este entorno; esa comprobación inicial no se repitió en esta corrección.

## Estado de aceptación

La interfaz de demostración y sus recorridos están implementados y comprobados.
Pendientes: revisión humana del nuevo incremento, controles CI/SAST del nuevo
commit, referencia de aprobación ST-029 en Jira y conexión con itinerarios/alertas
reales cuando el backend proporcione el contrato. El eventual merge no implica
finalizar automáticamente ECL-56/ST-030 ni ECL-22/EN-004.

Registro anterior: `ea114f9` creó el prototipo parcial; `6f0cf39` corrigió la
trazabilidad y pendientes documentales. Los checks de CI/CodeQL comunicados por
el equipo corresponden a revisiones anteriores, no prueban esta nueva revisión.
