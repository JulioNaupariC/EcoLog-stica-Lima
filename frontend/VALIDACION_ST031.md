# ST-031 / ECL-57 — Responsive y accesibilidad

Fecha: 09/10/2026. Corrección sobre main `8035345`.

Se reemplazó el foco amarillo por azul `#1d4ed8` (6.70:1 sobre blanco), se
incorporó un enlace para saltar al contenido y se ajustaron los controles de
reportes para texto largo y un área mínima de 44 px de altura.

## Checklist ejecutado

| Criterio | Resultado y evidencia |
|---|---|
| Sin desplazamiento horizontal a 360 px | Aprobado en Chrome 155.0.8059.40 y Firefox 157.0: viewport = scrollWidth = 360. También 768/1280 px. |
| Controles por teclado | Tab recorre navegación y botones de reportes. Enter en el enlace de salto enfoca el contenido principal. |
| Etiquetas y foco visible | Controles con texto/label; foco azul en navegación, login y reportes. |
| Contraste | axe-core 4.10.3: cero infracciones y cero comprobaciones incompletas en los estados examinados; foco calculado 6.70:1. |
| Espaciado de texto | Sin desbordamiento al aplicar interlineado 1.5, letras .12em, palabras .16em y separación de párrafos 2em. |
| Compatibilidad | Mismos seis estados examinados en ambos navegadores; capturas y resultados JSON conservados. |

Los seis estados son login, validación vacía, itinerario a 360/768/1280 y
espaciado ampliado. La autenticación/API del script son simuladas; IndexedDB
y los navegadores son reales. El objetivo de esta evidencia es la interfaz.
No certifica todos los criterios WCAG en todas las pantallas del producto ni
sustituye las pruebas con participantes/lector de pantalla del RNF global.

## Repetir

Desde frontend, preparar dependencias de prueba aisladas:

```powershell
npm.cmd install --prefix node_modules/.st031-check --no-save --no-package-lock axe-core@4.10.3 playwright@1.64.0
node node_modules/.st031-check/node_modules/playwright/cli.js install firefox
$env:VITE_API_BASE_URL='http://127.0.0.1:5178/review-api'
npm.cmd run dev -- --host 127.0.0.1 --port 5178 --strictPort
```

En otra terminal de frontend:

```powershell
$env:PLAYWRIGHT_MODULE='node_modules/.st031-check/node_modules/playwright/index.mjs'
$env:AXE_SCRIPT='node_modules/.st031-check/node_modules/axe-core/axe.min.js'
node scripts/verify-accessibility.mjs
```

Chrome debe estar instalado. El script falla si detecta desbordamiento,
infracciones axe o regresiones de teclado verificadas. Las evidencias están en
[evidencias/ECL-57](evidencias/ECL-57/resultados.json).

TypeScript, ESLint y build aprobados. Resultado de pruebas unitarias: 441
aprobadas. CI remoto y revisión humana pendientes del nuevo PR.
