# Frontend de EcoLogística Lima

## ST-032: itinerario offline y sincronización

Validación y reproducción: [VALIDACION_ST032.md](<../docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST032.md>).
`npm run build` genera el shell público y manifiesto versionado; servir `dist/`
sobre HTTPS o localhost. `npm run dev` no instala el Service Worker.
Primero iniciar sesión y consultar la ruta online; después la misma pestaña puede
recargar sin red hasta vencer la sesión. No existe login nuevo offline.

IndexedDB guarda dirección, referencia y ventana por propietario durante 24 h,
sin cifrado automático. No guarda credenciales ni campos de contacto.
Logout borra la pista de identidad y el snapshot; advierte y conserva los
reportes pendientes para recuperarlos autenticando la misma cuenta. Evitar datos
personales innecesarios en referencias libres. El cache del Service Worker solo
contiene recursos públicos, nunca respuestas API.

Al reconectar se verifica la sesión, se actualiza el itinerario y se envía la cola;
los errores de red se reintentan conservando el UUID hasta confirmar persistencia.
El backend debe estar actualizado a `0009_driver_stop_order` y las asignaciones
deben referenciar pedidos auténticos para incluir dirección y ventana.

Base técnica React + TypeScript construida con Vite. Incluye navegación mínima,
configuración externa de la URL del API, validaciones automáticas y estilos CSS
responsive.

## Requisitos

- Node.js 22.18.0 (definido en `.nvmrc`) o una versión compatible con
  `>=22.12.0 <27`.
- npm 10 o superior.

Si se usa NVM, ejecutar `nvm use` dentro de `frontend/`.

## Instalación reproducible

El arranque local con Docker Compose se documenta en el
[README principal](../README.md#arranque-local-con-docker-compose--ecl-29).
Esta instalación directa sigue disponible. La imagen local instala con
`npm ci` y ejecuta Vite; no monta el código del host, por lo que los cambios
requieren reconstruir la imagen.

```bash
cd frontend
npm ci
```

El archivo `package-lock.json` fija todas las versiones resueltas.

## Configuración de entorno

Copiar `.env.example` como `.env.local` y ajustar únicamente para el entorno
local:

```bash
cp .env.example .env.local
```

`VITE_API_BASE_URL` es obligatoria para construir las URLs del API y debe
ser una URL HTTP o HTTPS válida. Las variables `VITE_*` quedan expuestas en el
bundle del navegador: nunca deben contener secretos, tokens ni credenciales.

En desarrollo, el frontend se sirve desde `http://127.0.0.1:5173` y el backend
desde `http://127.0.0.1:8000`. El backend debe configurar:

```text
CORS_ALLOWED_ORIGINS=["http://127.0.0.1:5173"]
```

Las solicitudes autenticadas usan `credentials: "include"` para enviar la cookie
HttpOnly. No mezclar `localhost` con `127.0.0.1`: la sesión usa `SameSite=Strict`
y ambos procesos deben conservar una relación de mismo sitio. La sesión de un
Operador o Administrador debe existir antes de usar el formulario de pedidos.

## Acceso y roles

La ruta `/login` envía `POST /login` con correo y contraseña mediante
`credentials: "include"`. El backend crea la cookie de sesión HttpOnly y responde
con `usuario_id` y uno de los roles `ADMINISTRADOR`, `OPERADOR`, `CONDUCTOR`,
`ANALISTA` o `AUDITOR`. El frontend conserva esa identidad únicamente en memoria
React. No guarda credenciales ni la identidad en almacenamiento del navegador.

Tras una recarga, la identidad en React vuelve a ser desconocida aunque la cookie
del backend pudiera seguir vigente. No existe un endpoint `/me` para recuperar el
rol, por lo que la interfaz solicita iniciar sesión de nuevo para mostrar acciones
según rol. El enlace y la ruta `/pedidos/nuevo` se muestran visualmente solo a
`ADMINISTRADOR` y `OPERADOR`. El RBAC del backend sigue siendo la autoridad para
cada petición.

## Vehículos — ECL-41

La ruta `/vehiculos` reúne el listado y el registro de vehículos:

| Rol | Acceso efectivo a esta vista |
|---|---|
| `ADMINISTRADOR`, `OPERADOR` | Listar y crear. |
| `AUDITOR` | Solo listar; el formulario no se monta. |
| `CONDUCTOR`, `ANALISTA` | Sin acceso a esta vista de flota general. |

La navegación y la ruta comparten una sola regla visual. Sin identidad se redirige
a `/login`; con rol no permitido se muestra acceso denegado sin solicitar el
listado. El RBAC del backend sigue siendo la autoridad real de cada operación.
Se conserva la limitación de ECL-37: tras recargar, la identidad en memoria se
pierde y hay que iniciar sesión otra vez. No se usa almacenamiento del navegador
ni se añade `/me`.

El servicio utiliza `buildApiUrl('vehiculos')` y `credentials: 'include'`:

- `GET /vehiculos`: espera `200` y un array directo; no envía body, `Content-Type`
  ni otros headers adicionales. Es un GET simple y no requiere preflight.
- `POST /vehiculos`: envía JSON con `Content-Type: application/json` y espera
  `201`. Solo incluye placa, tipo, las dos capacidades, rendimiento, factor CO₂
  y año de fabricación. El preflight utiliza POST y `content-type`.

La configuración CORS actual es suficiente para esas dos operaciones con el
origen documentado `http://127.0.0.1:5173` permitido. No añadir `Content-Type` al
GET: provocaría un preflight GET que la configuración actual rechaza.

Las capacidades, rendimiento y factor CO₂ se mantienen como **strings decimales**
en el formulario, request y response. Se valida precisión y escala sin convertir
a `Number`, admitiendo ceros finales como `1.2300`. Se usa punto decimal, sin
separadores de miles ni exponentes en el formulario. La placa conserva el texto
introducido; el backend la normaliza y la confirmación muestra la placa devuelta.

El listado mantiene el orden recibido e incluye vehículos activos e inactivos.
El botón **Actualizar listado** consulta nuevamente el API. Tras crear se limpia
el formulario y se actualiza la tabla en la misma ruta. Si ese GET falla, se
conserva la confirmación del registro y se permite reintentar solo la consulta.
Las respuestas GET obsoletas se ignoran. Los errores se presentan con mensajes
propios, sin exponer cuerpos ni detalles arbitrarios del backend.

ECL-41 no incluye detalle, edición, desactivación, reactivación, filtros,
paginación ni asignaciones.

## Itinerario móvil del conductor — ST-030

La ruta `/conductor/itinerario` y el enlace **Mi itinerario** están disponibles
únicamente para una identidad autenticada con rol `CONDUCTOR`. Sin identidad
se solicita iniciar sesión; los demás roles reciben acceso denegado. Tras
recargar se requiere iniciar sesión de nuevo, como en las otras vistas.

La vista sigue el diseño ECL-55/ST-029 aprobado según la confirmación de Giancarlo.
Muestra cuatro paradas ficticias, siguiente parada destacada, alertas operativas
de demostración, filtros y detalle. La siguiente parada es la primera no completada
por secuencia; no cambia al filtrar ni al abrir otro detalle. El detalle muestra
únicamente las alertas asociadas a esa parada. Incluye un ejemplo sin asignación.
Los controles se recorren con Tab y se activan con Enter o espacio. Al cambiar de
vista el foco pasa al título. El diseño contempla 360 px en una columna.

Los datos están identificados como demostración: no se consulta una API de rutas,
no se modifican entregas reales y no se incluye GPS, persistencia ni sincronización
offline. La integración real debe aplicar autorización en el backend por conductor
y asignación. El backend local no ofrece endpoints de itinerarios ni alertas;
no se inventó un contrato ni se consultan recursos de otros conductores. La
integración de esos datos sigue pendiente y debe revisarse antes de cerrar el ticket.

**Desde ECL-56 (13/10/2026) el itinerario ficticio está desactivado por
defecto.** Solo se muestra si el build se genera con
`VITE_DEMO_ITINERARY=true` (ver `.env.example`); cualquier otro valor lo
desactiva. Sin esa variable, el conductor ve sus paradas reales o el estado
vacío «Aún no tienes paradas asignadas», también cuando falla la carga, sin
recurrir al ejemplo. `verify-driver-itinerary.mjs` recorre el ejemplo y
requiere una vista previa generada con la variable activada.

Para probar el acceso integrado se necesita el backend y una cuenta de prueba
autorizada con rol `CONDUCTOR`. Revisar escritorio y 360 px, filtros, selección,
teclado y denegación a otros roles. Las pruebas de React simulan autenticación;
la verificación adicional de navegador usa login real de conductor y login
simulado de Auditor. Resultados y capturas en
[VALIDACION_ST030.md](<../docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST030.md>) y [evidencias ECL-56](evidencias/ECL-56/README.md).

## Sistema de diseño — ECL-22 / EN-004

- Estilos en CSS plano: `src/styles/tokens.css` (único archivo con colores
  literales; paleta, escala tipográfica 1.200, espaciado 4/8 px, radios,
  sombras, z-index y duraciones), `base.css`, `layout.css` y `components.css`.
- Modo oscuro por `prefers-color-scheme` y manual (menú de cuenta → Tema), con
  `data-theme` en `<html>`; se respeta `prefers-reduced-motion`.
- Fuente Inter Variable autoalojada (`@fontsource-variable/inter`, solo latin y
  latin-ext) e iconos `lucide-react` con `aria-hidden` en los decorativos.
  `build-offline.mjs` precachea los `.woff2` para el uso sin conexión.
- Componentes en `src/components/ui/`: Button, Badge/StatusBadge, Card,
  DataTable (tabla en escritorio, tarjetas en móvil), EmptyState, Skeleton,
  Alert, Toast, PageHeader con migas de pan, FormSection/FormActions, StatCard y
  Combobox (el de ECL-53).
- Layout por rol en `src/components/layout/`: sidebar colapsable y menú de
  cuenta para administración/operación; navegación inferior para el conductor.
- `node scripts/check-contrast.mjs` verifica el contraste AA de los tokens.
- Capturas y auditoría: [evidencias ECL-22](evidencias/ECL-22-rediseno/README.md).

## Desarrollo

```bash
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

## Build y previsualización

```bash
npm run build
npm run preview
```

## Calidad

```bash
npm run typecheck
npm run lint
npm run test
npm run test:coverage
```

La cobertura excluye únicamente `src/main.tsx` (bootstrap del DOM),
`src/env.d.ts` (declaraciones) y `src/test/setup.ts` (configuración del entorno
de pruebas). Los módulos de aplicación, páginas y configuración del API sí se
miden y deben alcanzar al menos 80% en líneas, sentencias, funciones y ramas.

## Evaluación de accesibilidad — ECL-67 / EN-011

Con Docker y los datos de demostración ya disponibles en `127.0.0.1`, ejecutar
desde la raíz del repositorio en PowerShell:

```powershell
# Herramientas temporales: no modifican package.json ni el lockfile del producto.
npm install --prefix .tmp-ecl67 --no-save --package-lock=false --no-audit --no-fund playwright@1.64.1 axe-core@4.14.0 lighthouse@13.5.0 puppeteer-core@25.16.0
$env:EVIDENCE_DIR = "$PWD/.tmp-ecl67/evaluacion-$(Get-Date -Format yyyyMMdd-HHmmss)"
node frontend/scripts/verify-accessibility.mjs --sprint3
node frontend/scripts/check-contrast.mjs --json
Remove-Item env:EVIDENCE_DIR
```

Requiere Chrome instalado en su ruta habitual de Windows y Node >=22.19 para
Lighthouse 13 (la aplicación conserva sus requisitos y dependencias). Se puede
usar `ECL67_TOOLS` para indicar otra carpeta `node_modules` de las herramientas.
El script obtiene las contraseñas demo de `.env` local, sin imprimirlas; los
campos de contraseña deben estar vacíos antes de generar reportes o capturas.

La opción `--sprint3` evalúa once vistas con API real, ambos temas y anchos de
1280, 360 y 320 px. Guarda axe JSON, Lighthouse JSON/HTML y capturas. Lighthouse
usa `snapshot` sobre la sesión autenticada: una navegación completa perdería
la identidad de operación mantenida en memoria y mediría el login por error.
Se registra también el foco del menú móvil y una prueba de tamaño de fuente
al 200 %, que no reemplaza el zoom real del navegador. `--axe-only` omite
Lighthouse; `ECL67_SCREENS` permite seleccionar IDs separados por comas.
Cada ejecución exige una carpeta nueva para conservar la evidencia anterior.

Para una comprobación adicional del login mediante la CLI:

```powershell
$env:CHROME_PATH = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
npx --prefix .tmp-ecl67 --no-install lighthouse http://127.0.0.1:5173/login --only-categories=accessibility --preset=desktop --chrome-flags='--headless=new' --output=json --output=html --output-path=.tmp-ecl67/login-cli --quiet
Remove-Item env:CHROME_PATH
```

Los reportes conservan las comprobaciones que requieren revisión humana.
Un puntaje de Lighthouse o cero violaciones de axe no equivalen a un porcentaje
de conformidad WCAG. La evaluación incluye por separado teclado, lector de
pantalla, zoom real y una matriz de criterios A/AA aplicables.
Sin `--sprint3`, el script anterior conserva su recorrido histórico ST-031.

## Gestión de conductores — ECL-49 / ST-023

La ruta `/conductores` permite a ADMINISTRADOR y OPERADOR registrar, listar,
consultar y actualizar perfiles mediante la API ECL-48. Incluye paginación,
validación de campos, disponibilidad en hora de Lima y estados de carga/error.
El formulario de alta crea la cuenta con email y contraseña inicial; la edición
gestiona el perfil sin modificar credenciales. Los demás roles no disponen del enlace
y reciben acceso denegado al abrir la ruta.

Validación y reproducción en [VALIDACION_ST023.md](<../docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST023.md>).
Capturas de Chrome y Firefox en [evidencias ECL-49](evidencias/ECL-49/README.md).

## Preferencias de entrega — ECL-53 / ST-027

La ruta `/clientes/preferencias` permite a ADMINISTRADOR y OPERADOR consultar y
editar horario preferido, referencia de ubicación y restricciones de acceso
mediante GET/PATCH `/clientes/{cliente_id}/preferencias` de ST-026.
Se utiliza el ID de un cliente existente porque la API todavía no proporciona
un listado para seleccionar clientes. No se crean clientes desde esta vista.

Los campos de texto respetan los límites 120/255/255 y preservan los espacios
del contenido. Las casillas “Sin…” permiten limpiar explícitamente con null;
los campos sin cambios se omiten del PATCH. El horario es descriptivo y no
modifica las ventanas de los pedidos. Los demás roles no disponen del enlace
y reciben acceso denegado al abrir la ruta. Un 401 devuelve al login.

Se reutilizan `FormField`, extraído del formulario de pedidos, y los estilos
existentes de formularios y avisos. La regresión de pedidos permanece en verde.
Ver [VALIDACION_ST027.md](<../docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST027.md>),
[capturas ECL-53](evidencias/ECL-53/README.md) y la
[guía para José](<../docs/03 Implementación/Sprint 02/guias/GUIA_JOSE_ST027.md>) para resultados, reproducción y PR.

[← Volver al README principal](../README.md)
