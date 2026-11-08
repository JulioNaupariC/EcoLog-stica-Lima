# ECL-15 / US-009 — Dashboard de operación y sostenibilidad

Fecha: 08/11/2026 (America/Lima). Autor: Giancarlo Soto, UX/UI. Historia de usuario de 5 Story Points. Revisores previstos: José para frontend y un dueño de documentación. La auditoría técnica independiente y aprobación humana se verifican en el PR.

## Alcance de esta entrega

Implementa la página `/indicadores/sostenibilidad`, enlazada desde el menú y los accesos rápidos de Inicio. Consume con cookie el endpoint publicado `GET /indicadores/sostenibilidad?desde=...&hasta=...`, sin descargar listas de rutas ni geometrías. No cambia backend, migraciones, permisos ni requisitos.

Giancarlo autorizó elegir el avance útil mientras Antony no respondía a la coordinación. Se eligió entregar el frontend sobre el contrato existente, con origen explícito. Aunque ST-047 ya calcula optimizaciones reales, el endpoint de sostenibilidad de `main` continúa utilizando `RutasSimuladasService`. Por tanto, **esta entrega no acredita agregación de rutas cerradas reales ni conformidad completa de toda la BDD de US-009**.

Fuentes: [BDD ratificada v1.0.0](<../../02 Planificación/BDD/ECL-15-US-009-dashboard.md>), [RF-009](<../../01 Inicio/06. Requisitos funcionales V_1_1_0.md>), [RNF-011 y RNF-012](<../../01 Inicio/07. Requisitos no funcionales V_1_2_0.md>), [reglas de negocio](<../../01 Inicio/09. Reglas de negocio V_1_1_0.md>) y [glosario del Sprint 4](CONVENCIONES_Y_GLOSARIO_ECL99.md).

## Comportamiento

- Administrador, Operador, Analista y Auditor acceden al agregado. La inclusión del Auditor proviene de la ratificación de Julio en la BDD; no se cambia la matriz. Conductor no ve el enlace y recibe acceso denegado en la ruta. Se conserva el bloqueo de cambio obligatorio de contraseña.
- Periodo inicial: primer día del mes hasta hoy en Lima. Las fechas se editan y se aplican explícitamente con «Consultar periodo». Se muestra el periodo devuelto por la API; editar el formulario no renombra los datos ya consultados.
- Desde posterior a Hasta, fechas imposibles o ausentes: mensaje accesible, foco en Desde y ninguna petición inválida. Se cancelan solicitudes anteriores y se ignoran respuestas tardías o fuera de orden.
- Carga, sesión vencida, permisos, 422, red/servidor, respuesta incoherente y periodo vacío son estados distintos. Un error nunca se presenta como «Sin datos» ni publica un agregado parcial. 401 activa el flujo de sesión vencida.
- Totales con unidades km, kg CO₂, L y S/; rutas cerradas y cumplimiento en %. Tabla semántica con optimizada, secuencial y ahorro. La referencia se reconstruye como optimizada + ahorro del agregado; no se recalculan indicadores a partir de rutas en el navegador. Se redondea solo la presentación, a dos decimales como máximo.
- El porcentaje publicado corresponde al ahorro de distancia. Se conservan ahorros negativos y ceros verdaderos; pct null se presenta como no calculable y el cumplimiento null como no disponible. Sin datos no se muestran tarjetas con ceros ni tablas vacías.
- Versiones históricas recibidas visibles y enlace a EN-008. No se sustituyen por la versión vigente. El equivalente ambiental indica «No disponible»: el contrato actual no publica el objeto con proyecto, factor, fuente y unidad que exige RN-014.
- `simulado:true` muestra «Datos de prueba». El texto distingue estimaciones de planificación de telemetría medida; no afirma créditos certificados. No existe fallback silencioso a fixtures en el cliente: los fixtures se usan en las pruebas, y la app consulta siempre el API configurado.

## Trazabilidad de validación

| Escenario BDD | Evidencia de frontend | Límite de esta entrega |
|---|---|---|
| D01, periodo con rutas | Fixture ST-045 y referencia BDD de 150 km, 50 km de ahorro, 25 % y cumplimiento 75 % | No se prueba agregado real de BD |
| D02, versiones y exactitud | Conservación de versiones múltiples y representación de unidades | Las 20 referencias de cálculo e historial real corresponden al backend/EN-008 |
| D03, equivalente ambiental | «No disponible», sin factor ni proyecto inventados | No existe objeto publicado para representar equivalencia disponible |
| D04, errores y roles | Cliente HTTP y navegación probados para todos los roles, 401/403/422 y fechas inválidas | No cambia RBAC del servidor |
| D05, datos incompletos | Respuesta inválida produce error seguro, sin sumas parciales | Cierre transaccional no implementado aquí |
| D06, vacío/cero/negativos | Casos unitarios y de página separados | Datos sintéticos |
| D07, límites y reintentos | Un solo día, periodo aplicado y respuestas fuera de orden | Filtro por cerrada_en y cierre idempotente pendientes de backend |
| D08, accesibilidad/transferencia | Chrome y Firefox, móvil/escritorio, claro/oscuro, axe y Lighthouse; rechazo de cuerpo >250000 bytes | Bytes del fixture no acreditan transferencia real ni EXPLAIN de una consulta productiva |

## Pruebas ejecutadas

08/11/2026: `npm run typecheck`, `npm run lint`, `npm run test:coverage -- --maxWorkers=2` y `npm run build` aprobados. Suite completa: **945 pruebas en 63 archivos**. Cobertura global de líneas: **97,93 %**; dominio, servicio y página nuevos: **100 % de líneas** (91/91), con ramas de la página 43/45 y las del dominio/servicio completas. Los tests se ejecutan sin apuntar a la API local; el build sí configura su URL.

El build separa la página en un chunk diferido, sin dependencias nuevas. Las copias de fixtures de frontend ya versionadas coinciden con las de ST-045; no se alteraron las evidencias históricas.

Revisión reproducible: levantar frontend en `127.0.0.1:5184` con VITE_API_BASE_URL configurada y ejecutar desde la raíz `node frontend/scripts/verify-sustainability.mjs`. Usa puppeteer-core, axe-core y Lighthouse ya instalados transitivamente; ECL15_ORIGIN y ECL15_OUTPUT permiten elegir URL y una carpeta nueva. No usar una carpeta de evidencia histórica como destino.

La verificación automatiza la SPA completa con login y GET interceptados, sin credenciales reales. Chrome 157.0.8103.38 y Firefox 159.0.1: 360/1280 px, temas claro/oscuro, sin desbordamiento ni violaciones WCAG A/AA detectadas por axe. Lighthouse en modo snapshot: accesibilidad **100/100**, sin auditorías fallidas. También se comprueban Enter, foco tras rango inválido y distinción vacío/error. El JSON sintético mayor usado mide 382 bytes UTF-8 sin comprimir; no se midieron bytes transferidos reales ni se revisó un plan SQL.

Evidencias nuevas: [resumen y hashes de fuente](evidencias/ECL-15/revision-20261108/results.json), [Lighthouse resumido](evidencias/ECL-15/revision-20261108/lighthouse-summary.json), [escritorio claro](evidencias/ECL-15/revision-20261108/chrome-light-1280.png) y [móvil oscuro](evidencias/ECL-15/revision-20261108/firefox-dark-360.png). Los informes completos quedan disponibles localmente al ejecutar el verificador; los resultados automáticos no equivalen a conformidad WCAG completa. Giancarlo confirmó en la app local «Narrador, teclado y ambos periodos correctos» al consultar noviembre de 2026 y enero de 2025: [declaración manual](evidencias/ECL-15/revision-20261108/manual-narrador.json). No se registró versión de Narrador ni rol concreto; no se afirma una grabación o una prueba de todos los roles con lector.

## Coordinación pendiente

Antony debe coordinar la agregación real conforme a la BDD ratificada: definición de cierre y cerrada_en, ventanas con atendida_en real y NO_ATENDIDA en denominador, versiones históricas comparables, auditoría de consultas y equivalente ambiental nullable con fuente/proyecto/factor. Revisar también que el esquema admita cumplimiento null cuando no exista denominador. No inferir cierres de optimización COMPLETADA ni de ETA.

La interfaz está preparada para respuestas del mismo contrato con `simulado:false`; esto no garantiza compatibilidad con extensiones futuras de campos. La respuesta simulada actual reproduce el fixture completo ante cualquier solapamiento de periodos: no es un filtro de datos reales. El PR debe revisarse con este límite explícito; el cierre funcional completo de US-009 requiere coordinar esos pendientes, sin cambiar requisitos para adaptarlos al estado del código.

[← Índice del Sprint 4](README.md) · [README principal](../../../README.md)
