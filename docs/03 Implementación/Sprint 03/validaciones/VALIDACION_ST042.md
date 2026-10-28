# ECL-75 / ST-042 — Vista de incidencias pendientes para Operación

| Campo | Valor |
|---|---|
| Responsable | Giancarlo Marcio Soto Escobar — @GiancarloSE |
| Historia padre | US-012 / ECL-18 |
| Sprint | Sprint 3 |
| Rama | `feat/ECL-75-vista-incidencias` |
| Fecha de verificación | 26/10/2026, America/Lima |
| Revisión frontend | José — @JoseDelgadillo277 |
| Revisión documental | Frank — @FrankRoyYA |

## Alcance y contrato

La ruta `/operacion/incidencias` permite a Administrador y Operador consultar
reportes pendientes. La navegación incorpora «Incidencias pendientes» bajo
«Operación» y la guarda de ruta usa la misma regla de roles. Analista, Auditor
y Conductor no tienen entrada en el menú y reciben acceso denegado al navegar
a esa ruta. Sin identidad se solicita iniciar sesión.

Se consume la API real de ECL-73, ya integrada en `main`, conforme a la
[BDD aprobada de ECL-72](<../../../02 Planificación/BDD/ECL-72-ST-039-incidencias.md>),
RF-012 y RN-022. Las simulaciones se reservan para pruebas de estados y
paginación. No se modifica backend, OpenAPI, permisos globales ni base de datos.

```text
GET /incidencias?estado=PENDIENTE_VALIDACION&page=1&page_size=20
```

La petición envía la cookie de sesión, usa `cache: no-store`, admite cancelación
y tiene un límite de espera de 15 segundos. El servicio comprueba el contrato
antes de renderizar y proyecta exclusivamente sus campos permitidos. Conserva
la paginación del servidor y ordena los elementos de cada página por instante
de ocurrencia descendente e ID ascendente en empate. La ordenación global entre
páginas corresponde al servidor.

No incluye acciones de validar, descartar, bloquear una vía ni reoptimizar.
Tampoco incorpora la tarjeta opcional de Inicio. ECL-67 y las pruebas por ruta
de ECL-76 conservan su alcance propio.

## Interfaz y accesibilidad de esta vista

- Reutiliza `PageHeader`, `DataTable`, `Badge`, `Button`, `Alert`, `EmptyState`
  y `Skeleton`, con los tokens del rediseño ECL-22 y la guía ST-029.
- Presenta hora de ocurrencia en `America/Lima`, formato `dd/mm HH:mm`; el
  elemento `time` conserva el instante original y un nombre accesible con fecha
  completa y zona explícita.
- Muestra tipo, severidad con texto e icono, nombre del conductor, coordenadas
  con cinco decimales y observación. No presenta ID, DNI, teléfono ni licencia
  del conductor.
- El enlace a OpenStreetMap abre una pestaña nueva, lo anuncia en su nombre
  accesible y usa `noopener noreferrer` y `no-referrer`. No carga mapas ni
  envía coordenadas a terceros antes de abrir el enlace.
- Las observaciones de más de 100 puntos de código muestran un resumen y un
  detalle nativo que puede abrirse con teclado. El texto completo se conserva
  y React lo trata como texto, sin interpretar HTML. Una observación vacía se
  identifica como «Sin observación».
- Durante la carga anuncia el estado y deshabilita la actualización. Si tarda
  un segundo aparece el esqueleto, oculto a tecnologías de asistencia.
- El vacío informa «No hay incidencias pendientes de validación». Los errores
  ofrecen «Reintentar»; un 403 explica los roles autorizados y un 401 devuelve
  el control a la gestión de sesión existente.
- La paginación ofrece «Anterior», «Siguiente» y «Página X de Y». Si el total
  disminuye y desaparece la página solicitada, consulta una página válida.
- A 360 px la tabla se presenta como tarjetas sin duplicar contenido ni
  desbordar horizontalmente la página. Se conserva foco visible y orden de Tab.

## Pruebas automatizadas

| Archivo | Comprobación |
|---|---|
| `frontend/src/services/incidentList.test.ts` | URL, cookie, cancelación, orden con offsets distintos y empates, minimización de datos, metadatos y contenido inválidos, errores HTTP y de red |
| `frontend/src/pages/OperationIncidentsPage.test.tsx` | Lista, hora de Lima, severidades, mapa, observación completa y HTML como texto, vacío, carga lenta, reintento, 403, 401, paginación y desmontaje |
| `frontend/src/app/App.test.tsx` | Ruta y menú para Administrador/Operador; denegación de Analista/Auditor/Conductor; acceso sin identidad |

Resultados locales, con Node.js 22.20.0 y Vitest 5.0.1:

| Validación | Resultado |
|---|---|
| `npm run typecheck` | Correcto |
| `npm run lint` | Correcto |
| `npm run test:coverage -- --maxWorkers=2` | 50 archivos, 694 pruebas aprobadas |
| `npm run build` | Compilación de producción correcta |
| `python scripts/check_docs.py` | Correcto; enlaces, índice y retornos válidos |
| Cobertura global de líneas / ramas | 97.61% / 92.75% |
| Cobertura global de sentencias / funciones | 95.35% / 94.81% |
| `incidentList.ts` | 100% en líneas, ramas, sentencias y funciones |
| `OperationIncidentsPage.tsx` | 100% líneas y funciones; 92.30% ramas; 98.63% sentencias |

El incremento supera el mínimo de cobertura del 80%. Los reportes completos
se generan en `frontend/coverage/` (ignorado por Git). La comprobación documental
se ejecutó sobre los archivos preparados en el índice antes del commit.

## Comprobación en Docker y Chrome

El frontend se reconstruyó con Docker Compose y se comprobó contra
`http://127.0.0.1:8000` y los datos ficticios del seed. La API devolvió las tres
incidencias de demostración; Administrador y Operador obtuvieron 200, y los
otros tres roles obtuvieron 403. También se verificó el menú y la guarda de
ruta en el navegador.

El [registro de ejecución](<evidencias/ECL-75/results.json>) contiene 21 entradas
de comprobación y captura en Chrome 156.0.8078.48. Las cuatro combinaciones de
360/1280 px y claro/oscuro conservaron `scrollWidth == innerWidth`.
La revisión automatizada con axe-core se limita a esta vista y no detectó
violaciones en esas combinaciones. No constituye una auditoría completa WCAG
2.1 AA, una prueba de lector de pantalla ni la entrega de ECL-67.

Se probaron por teclado la actualización, el acceso al mapa, la paginación y
la apertura de una observación larga. Los estados vacío, HTTP 503, HTTP 403,
carga lenta y paginación de 21 registros se simularon mediante interceptación
en el navegador, sin alterar registros de la base. Cada captura distingue su
origen en el [índice de evidencias](<evidencias/ECL-75/README.md>).

## Reproducción

Desde la raíz, con Docker activo, la base migrada y el seed cargado:

```powershell
docker compose --env-file .env build frontend
docker compose --env-file .env up -d --wait frontend

cd frontend
npm ci
npm run typecheck
npm run lint
npm run test:coverage -- --maxWorkers=2
npm run build
cd ..
```

Para el navegador se usa Chrome instalado y herramientas temporales fuera de
las dependencias del producto. El script lee las contraseñas de demo del `.env`
privado; no las muestra ni captura la pantalla de login. Los cinco valores
`SEED_DEMO_PASSWORD_<ROL>` deben corresponder a las cuentas sembradas.

```powershell
npm install --prefix .tmp-ecl75 --no-save --package-lock=false playwright axe-core
$env:ECL75_OUTPUT = '.tmp-ecl75/capturas-repeticion'
node frontend/scripts/verify-operation-incidents.mjs
Remove-Item env:ECL75_OUTPUT
```

Usar un directorio de salida nuevo en cada repetición: el script se niega a
sobrescribir capturas anteriores. Para elegir otra instalación de herramientas
existen `ECL75_PLAYWRIGHT_MODULE` y `ECL75_AXE_PATH`.

## Revisión e integración

La autorrevisión y las pruebas locales no sustituyen la auditoría técnica
independiente, la revisión de alertas CodeQL ni la aprobación humana de los
dueños de frontend y documentación. Esas revisiones se registran en el PR.
No se ha integrado el cambio a `main`.

[↑ Índice del Sprint 3](<../README.md>)

[← Volver al README principal](<../../../../README.md>)
