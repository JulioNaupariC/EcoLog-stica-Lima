# ECL-120 — Registro de resultados y cierre de rutas

Fecha de validación: 08/11/2026 (America/Lima). Autor: Giancarlo Soto, UX/UI. Subtarea de US-009 / ECL-15. Revisores: José (frontend) y Julio (documentación). Auditoría independiente y aprobación del head final se verifican en el PR.

## Alcance y fuentes

Extiende `/operacion/rutas`, en el detalle de una optimización COMPLETADA. Usa el backend de [ECL-119](<ECL-119 cierre de rutas y sostenibilidad.md>) ya integrado y la [BDD US-009 ratificada](<../../02 Planificación/BDD/ECL-15-US-009-dashboard.md>). No modifica backend, migraciones, matriz RBAC, requisitos ni dependencias.

Permisos vigentes: **Operador** consulta el detalle y registra resultados/cierra rutas; **Administrador** consulta el detalle en lectura; **Analista y Auditor** consultan el dashboard agregado; **Conductor** no accede al detalle operativo. Se conserva el cambio obligatorio de contraseña. No se amplía la lectura de nombres/ubicaciones a roles agregados.

La guía se alinea con [RF-008/009](<../../01 Inicio/06. Requisitos funcionales V_1_1_0.md>), [RNF de seguridad, accesibilidad y calidad](<../../01 Inicio/07. Requisitos no funcionales V_1_2_0.md>), [reglas de negocio](<../../01 Inicio/09. Reglas de negocio V_1_1_0.md>), [modelo de datos v1.4.0](<../../01 Inicio/11. Base de datos V_1_4_0.md>) y [glosario del Sprint 4](CONVENCIONES_Y_GLOSARIO_ECL99.md).

## Registro y cierre

- Cada ruta muestra su estado propio (Planificada, En curso o Cerrada), distinto de COMPLETADA de la optimización.
- Cada parada pendiente ofrece «Registrar resultado». ATENDIDA propone la hora actual de Lima, editable y con representación explícita de 24 horas. No se utiliza la ETA como atención real. Se valida jornada desde 00:00 de Lima y ausencia de hora futura; se envía offset `-05:00`.
- NO_ATENDIDA envía solo el estado, sin una hora residual; se informa que cuenta como incumplida. Las paradas con resultado final no ofrecen edición. Los detalles simulados se mantienen en lectura para evitar escribir identificadores de fixtures.
- Los estados cambian únicamente después del acuse validado del servidor, con comprobación de ruta/parada, resultado y hora. No hay actualización optimista, reintento automático ni cola offline de estas escrituras.
- «Cerrar ruta» se habilita con todas las paradas terminales. La confirmación está dentro de la página, muestra los conteos y enfoca Cancelar cierre. Cancelar devuelve el foco; confirmar espera la respuesta. Nunca llama a `window.confirm`.
- El acuse de cierre exige estado CERRADA, fecha con zona y conteos consistentes con las paradas consultadas. El aviso de éxito recibe foco; se bloquean las acciones y se ofrece el dashboard del periodo de cierre. Una ETA u optimización completada no cierran automáticamente la ruta.
- GET del detalle publica estados, pero no publica atendida_en ni cerrada_en. La hora de cierre anunciada procede del acuse de la operación actual; no se inventa una hora al volver a cargar una ruta ya cerrada.

## Errores, foco y concurrencia

| Caso | Comportamiento |
|---|---|
| 401 | Activa el flujo de sesión vencida. |
| 403 | Informa que solo Operador puede escribir y retira las acciones. |
| 404 / 409 | Mensaje en la ruta con role=alert y foco; exige actualizar el estado antes de continuar. Solo se muestran motivos conocidos y el conteo seguro «Faltan N paradas por registrar». |
| 422 | Mensaje junto al campo, role=alert, aria-invalid y foco en la hora; conserva el borrador. El servidor sigue siendo autoridad sobre la hora. |
| 503 / red / respuesta incoherente | Error de servicio, nunca «Sin datos». Mantiene el borrador y bloquea nuevas escrituras hasta una lectura válida del detalle. Si también falla esa lectura, el bloqueo continúa. |
| Envío doble / cambio de ruta | Exclusión de escrituras concurrentes y descarte de respuestas tardías mediante cancelación y secuencia de petición. |

Los detalles de error arbitrarios no se reflejan. Salir durante una petición no deshace una posible operación ya procesada por el servidor: al volver se consulta el estado. Los borradores de esta pantalla no se guardan automáticamente en disco. Las acciones permanecen dentro de cada formulario pequeño en móvil, evitando heredar la barra fija de formularios largos.

## Pruebas ejecutadas

Suite completa de frontend: **1013 pruebas en 65 archivos**. Typecheck, lint y build aprobados. Cobertura global de líneas: **98,02 %**; los cuatro archivos nuevos de componentes/dominio/servicio tienen **121/122 líneas cubiertas**, por encima del mínimo de 80 %. El CI vuelve a calcularla para el head publicado. Se prueban servicio, fecha/hora Lima, éxito, idempotencia, acuses incoherentes, 401/403/404/409/422/503, foco, roles, cancelación y doble envío. Las pruebas de mapa/dashboard existentes permanecen en la suite.

Prueba real en base PostgreSQL/PostGIS desechable y API independiente en 8001: seed sintético, login Operador real, optimización por API, **13 resultados registrados desde la interfaz (1 ATENDIDA y 12 NO_ATENDIDA)**, cierre desde la confirmación de la página, nueva lectura persistida y dashboard con `simulado:false`. Repetir POST de cierre devolvió 200; la comprobación SQL exigió exactamente un evento RUTA_CERRADA. El agregado real de esa muestra midió 495 bytes UTF-8; no es una campaña RNF-012 representativa ni una prueba de rendimiento. El contenedor/API temporal y la base desechable se eliminaron; no se recreó ni sembró la base demo del usuario.

Verificación automatizada de interfaz con HTTP sintético interceptado: Chrome 157.0.8103.38 y Firefox 159.0.1, 360 y 1280 px, claro/oscuro. Sin desbordamiento ni violaciones detectadas por axe; Lighthouse snapshot dio **100/100 en accesibilidad** en ambos temas. Se probaron validación local sin petición, 422 junto al campo, 503 con borrador/actualización, 409 con lectura del estado nuevo, cierre por teclado y lectura del Administrador. Axe deja comprobaciones incompletas de contraste en algunas zonas; los resultados automáticos no equivalen a conformidad WCAG completa y esas observaciones requieren revisión manual.

Giancarlo declaró «Narrador, foco y teclado correctos en todo el flujo» en el banco local con dos paradas simuladas, sin credenciales ni escrituras reales. El flujo solicitado incluía error 503, recuperación, ATENDIDA/NO_ATENDIDA y cancelar/confirmar cierre. No se registró versión de Narrador ni grabación. Los últimos ajustes de espaciado y representación de 24 horas se comprobaron después con las verificaciones automáticas.

Evidencias nuevas: [interfaz y hashes](evidencias/ECL-120/revision-20261108/browser-results.json), [API/BD real y hashes](evidencias/ECL-120/revision-20261108/real-api-results.json), [Lighthouse resumido](evidencias/ECL-120/revision-20261108/lighthouse-summary.json), [formulario de escritorio](evidencias/ECL-120/revision-20261108/chrome-light-1280.png), [formulario móvil oscuro](evidencias/ECL-120/revision-20261108/firefox-dark-360.png), [dashboard con datos reales de prueba](evidencias/ECL-120/revision-20261108/dashboard-real.png) y [declaración manual](evidencias/ECL-120/revision-20261108/manual-narrador.json). Las evidencias históricas permanecen intactas.

## Reproducción y demo

1. Para la demo normal, iniciar sesión como Operador. En «Rutas y alertas», elegir fecha y una optimización COMPLETADA. Si no existe, el responsable genera una optimización con el endpoint existente POST /optimizaciones; crear una pantalla de optimización queda fuera de esta subtarea.
2. Registrar las paradas con resultados reales, revisar los conteos y confirmar el cierre. Abrir el dashboard con un periodo que incluya **la fecha de cierre**, no solo la fecha de planificación. Las rutas previas a 0018 sin referencia secuencial requieren una nueva optimización; el 409 lo explica.
3. Para repetir la verificación automatizada, desde frontend iniciar Vite con VITE_API_BASE_URL=http://127.0.0.1:8001 y `npm run dev -- --host 127.0.0.1 --port 5184 --strictPort`. Desde la raíz, `node frontend/scripts/verify-route-execution.mjs` intercepta HTTP sintético, sin base real. ECL120_BROWSER_OUTPUT permite una carpeta nueva; nunca usar una evidencia histórica como destino.
4. Para el flujo real aislado, con el backend reconstruido y db saludable, ejecutar desde la raíz `& ./frontend/scripts/verify-route-execution-real.ps1` manteniendo ese Vite abierto. Exige puerto 8001 libre, crea únicamente una base con prefijo ecologistica_ecl120_ y sufijo _demo, instala PostGIS/migraciones y seed con contraseña efímera en memoria, y limpia sus recursos con comprobación del nombre. No muestra contraseñas ni utiliza las claves demo del usuario.

Los verificadores usan las herramientas de navegador ya presentes como dependencias transitivas; no se añadieron paquetes. No se cambian Jira ni los estados de los tickets automáticamente. La auditoría técnica independiente y las aprobaciones de frontend/documentación siguen siendo necesarias antes de integrar.

[← Índice del Sprint 4](README.md) · [README principal](../../../README.md)
