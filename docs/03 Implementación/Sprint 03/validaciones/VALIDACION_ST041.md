# ECL-74 / ST-041 — Formulario móvil de incidencias

Implementación de José Delgadillo en `feat/ECL-74-formulario-incidencia`.
Fecha de validación: 26/10/2026 (America/Lima). Datos exclusivamente sintéticos.

[Ticket ECL-74](https://continental-team-il84x39k.atlassian.net/browse/ECL-74)
· Historia padre ECL-18 / US-012.

## Alcance implementado

El Conductor abre «Reportar incidencia» desde su itinerario. La ruta
`/conductor/incidencias/nueva` exige identidad Conductor y respeta el bloqueo
de cambio obligatorio de contraseña. El servidor mantiene su autorización por
cookie y el permiso `incidencias.crear`.

Se usa la [BDD ECL-72 aprobada](<../../../02 Planificación/BDD/ECL-72-ST-039-incidencias.md>)
y el contrato existente de ECL-73, no el contrato provisional del adjunto.
No se implementa el listado de Operación (ECL-75), la campaña completa de
US-012 (ECL-76), ni la comprobación de jornada pendiente en ECL-82.

| Criterio de ECL-74 | Implementación | Verificación |
|---|---|---|
| Tipo, severidad, ubicación, observación y hora automática | Seis tipos, tres radios con texto/icono, GPS o parada propia; hora visible de solo lectura; 500 puntos de código Unicode | Pruebas de dominio, servicio, página y navegador |
| Faltantes conservan borrador e indican campos | Validación al salir y enviar, foco al primer error, escrituras serializadas y restauración por propietario | Rutas feliz e infeliz en `IncidentCreatePage.test.tsx` |
| Offline y reconexión sin duplicar | Persistencia previa al POST, UUID v4 estable, verificación de propietario, acuse 200/201 comprobado | Pruebas de pérdida de respuesta, concurrencia local, cambio de cuenta y recarga real offline |
| Teclado, etiquetas, 360 px y modo oscuro | Componentes/tokens ST-029; radios nativos y foco de error | Chrome/Firefox, ambos temas, sin desborde horizontal |

## Diseño y persistencia

- `src/domain/incident.ts`: tipos y validación sin dependencias de React.
- `src/services/incidents.ts`: `POST /conductor/incidencias`, cookie, timeout de
  15 segundos y validación del acuse; errores sin copiar contenido del servidor.
- `src/services/incidentStorage.ts`: base separada `ecologistica-incidents-v1`,
  versión 1, almacenes `drafts` e `incidents`. No cambia la versión 2 de
  `ecologistica-offline-v1` ni toca `itineraries`/`pendingReports`.
- El alta en cola y la retirada del borrador forman una transacción. Una
  corrección de 422 también actualiza contenido y retira el borrador de forma
  atómica, conservando la operación original.
- `src/services/incidentSync.ts` y `useIncidentSynchronization`: coordinador
  por cuenta montado en App, Web Locks cuando está disponible, reconexión y
  sondeo de 15 segundos. Cancela solicitudes al cambiar de sesión. Antes de
  cada POST contrasta `owner_id` con el itinerario autenticado del servidor.
- Un acuse validado cambia el registro local a confirmado, fuera de la cola
  pendiente; se conserva el recibo para mostrar el ID y «Pendiente de validación».
  El registro no valida la incidencia ni reoptimiza rutas.
- Se reutilizan `useOnlineStatus`, componentes y diseño del Sprint 2. La cola
  de entregas y sus coordinadores siguen usando su contrato original; una
  incidencia no cambia el estado de entrega de una parada.
- La ruta se incluye en el service worker de producción para recarga offline.
  La caché conserva únicamente la aplicación pública; los datos van a IndexedDB.

Solo se guardan los campos operativos, UUID de propietario y operación,
fechas y acuse. No se guardan cookies, tokens, contraseñas, DNI ni contactos.
La observación advierte que no se introduzcan datos personales.

## Política de fallos

| Resultado | Comportamiento |
|---|---|
| 200/201 con acuse de la misma operación | Confirmado, ID visible, no se vuelve a enviar |
| Offline, timeout, pérdida de respuesta o 5xx | Pendiente; se conserva contenido y UUID exactos para reintento |
| 401 | Pausa también el reintento manual; se reanuda tras iniciar sesión con la misma cuenta |
| 403 | Error visible, conserva reporte; solo reintento explícito |
| 409 | Conflicto visible, no reintenta ni cambia de UUID; requiere revisión de Operación |
| 422 | Error visible; permite corregir el reporte conservando su UUID |
| Fallo de almacenamiento | No se anuncia encolado ni confirmación; se mantienen los campos en pantalla |

Cambiar de cuenta no muestra ni envía borradores o reportes de otro conductor.
El cierre de sesión cuenta también incidencias pendientes y advierte antes de
salir, conservándolas para volver a autenticarse.

## Ajuste mínimo del itinerario autorizado por José

`DeliveryDetails` incorpora `latitud` y `longitud` opcionales del pedido ya
asignado, con límites geográficos. No cambia permisos, tablas ni migraciones.
React valida las coordenadas y las conserva en la instantánea offline. Las
instantáneas antiguas siguen siendo válidas; una parada sin coordenadas muestra
esa limitación y no inventa una posición. El GPS sigue disponible.

Se verifica la proyección mínima, la cuenta usada al consultar y los pedidos
que tienen solo referencia. OpenAPI publica automáticamente el esquema Pydantic.
Por este ajuste, además de UX/UI y documentación, se debe solicitar revisión
de un dueño de `backend/` (@ANTONY-MUNIVE o @JulioNaupariC), además de
@GiancarloSE para frontend y @FrankRoyYA para documentación, según CODEOWNERS.

## Verificaciones y evidencias

Las pruebas nuevas usan nombres de ruta dorada, feliz, infeliz y de borde.
La ejecución focalizada inicial pasó **31 pruebas**. Cobertura de los seis
archivos nuevos de producción: **96,44 % líneas**, **93,47 % sentencias**,
**88,54 % ramas**, **90,21 % funciones**; todos los umbrales agregados superan
80 %. La suite global y las verificaciones finales se registran en el cuerpo
del PR, junto con las limitaciones reales de ejecución.

[Capturas y resultados de navegadores](<evidencias/ECL-74/README.md>) incluyen
foco en faltantes, formulario completo con GPS rechazado, recarga offline y
acuse tras reconexión, en las cuatro combinaciones navegador/tema. Cada caso
registró una operación y un POST, sin errores JavaScript. Estas pruebas usan
una API HTTP sintética local, no acreditan integración con PostgreSQL.

Comandos desde la raíz:

```powershell
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend run test -- --maxWorkers=1
npm --prefix frontend run test:coverage -- --maxWorkers=1
Push-Location backend
python -m ruff check .
python -m ruff format --check .
python -m pytest tests/unit --cov=app --cov-fail-under=80
Pop-Location
python scripts/check_docs.py
```

## Pendientes externos para integrar

Docker no está disponible en el equipo de ejecución. Sigue pendiente probar
el flujo con sesión autorizada, FastAPI y PostgreSQL/PostGIS reales siguiendo
el arranque del README; también la campaña de 10/10 de ECL-76. No se presentan
las pruebas simuladas como evidencia de esa integración.

La auditoría técnica independiente, aprobación humana por dueños de las áreas,
CI y revisión de alertas CodeQL requieren el PR en GitHub. La entrega se prepara
como Draft, conforme a la política de contribución; esta sesión no se autoaprueba.

[Cuerpo preparado del PR](<ECL-74-PR.md>)

[↑ Índice del Sprint 3](<../README.md>)

[← Volver al README principal](<../../../../README.md>)
