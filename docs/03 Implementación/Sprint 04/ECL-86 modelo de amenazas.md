# ECL-86 — Modelo de amenazas STRIDE y alertas de seguridad

## Alcance y método

Este modelo cubre cuatro flujos del sistema actual: login, restablecimiento de
contraseña, cola offline de incidencias del conductor y solicitud/consulta de
optimización de rutas. STRIDE se aplica en cada límite de confianza; «no se
identificó un control» expresa una brecha en el alcance revisado, no una
afirmación de explotación.

El alcance responde a OWASP A06:2025 (Insecure Design) mediante el análisis de
amenazas y a A09:2025 (Security Logging and Alerting Failures) mediante el
análisis de auditoría, métricas y alerta propuesta.

Las referencias enlazan al código, pruebas y documentación disponibles en el
repositorio. El riesgo residual no equivale a una vulnerabilidad confirmada ni
a la aceptación del riesgo. Los controles que pertenecen al diseño objetivo o
a trabajo pendiente no se presentan como ya implementados.

## 1. Login

**Activos:** credenciales y hashes; estado de bloqueo; sesión opaca y cookie;
identidad, rol y eventos de acceso.

**Actores:** usuario legítimo; atacante externo con credenciales probadas,
robadas o elegidas; operador de la plataforma con acceso a la auditoría.

| STRIDE | Amenaza | Controles existentes (evidencia) | Riesgo residual y seguimiento |
|---|---|---|---|
| **S — Suplantación** | Uso de una contraseña adivinada, reutilizada o robada para iniciar sesión como otra persona. | Argon2id y verificación de credenciales; respuesta genérica ante credenciales inválidas; bloqueo de cuenta tras 3 intentos fallidos durante 15 minutos. [passwords.py](../../../backend/app/core/passwords.py), [autenticacion.py](../../../backend/app/services/autenticacion.py), [reglas de negocio RN-001](../../01%20Inicio/09.%20Reglas%20de%20negocio%20V_1_1_0.md), [test de persistencia del bloqueo](../../../backend/tests/integration/test_auth_persistence.py). | **Parcial:** el bloqueo es por cuenta; no se identificó un límite por origen ni una alerta de intentos anómalos. El bloqueo también puede ser abusado para impedir el acceso a una cuenta. Seguimiento del riesgo de seguridad: [RSK-06](../../02%20Planificaci%C3%B3n/03%20Registro%20de%20riesgos%20V_1_0_0.md) / [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86); la remediación preventiva adicional no está asignada en la información disponible. |
| **T — Manipulación** | Alterar el cuerpo de login para fijar identidad/rol o explotar errores de validación que devuelvan datos enviados. | El esquema acepta solo las credenciales; la identidad y el rol se resuelven desde la cuenta. Las respuestas de autenticación y validación no repiten secretos. [auth.py](../../../backend/app/api/auth.py), [test de campos de identidad no permitidos](../../../backend/tests/unit/test_auth_api.py), [SanitizedRoute](../../../backend/app/api/validation.py). | **Bajo, no eliminado:** una sesión válida robada sigue siendo una credencial utilizable hasta revocación o vencimiento; ver también Suplantación. Seguimiento: [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). |
| **R — Repudio** | Un usuario niega un inicio fallido, exitoso o el bloqueo producido. | Se registran `LOGIN_EXITOSO`, `LOGIN_FALLIDO` y `CUENTA_BLOQUEADA` con resultado tipado; el evento fallido no registra contraseña ni atribuye un actor autenticado inexistente. [auditoria.py](../../../backend/app/repositories/auditoria.py), [autenticacion.py](../../../backend/app/services/autenticacion.py), [test de auditoría de acceso](../../../backend/tests/unit/test_auditoria.py). | **Parcial:** la auditoría persistida no implica alertamiento ni centralización de eventos; una revisión tardía puede retrasar la detección. Seguimiento: [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). |
| **I — Divulgación de información** | Enumerar cuentas o extraer la cookie/token desde una respuesta del login. | El error es el mismo 401 para credenciales inválidas; el token no se incluye en el cuerpo, la cookie usa `HttpOnly`, `SameSite=Strict`, `Secure` en producción y la respuesta usa `Cache-Control: no-store`. [auth.py](../../../backend/app/api/auth.py), [test de respuesta genérica](../../../backend/tests/unit/test_auth_api.py), [RNF-017](../../01%20Inicio/07.%20Requisitos%20no%20funcionales%20V_1_2_0.md). | **Residual:** el robo de una cookie desde el dispositivo o navegador comprometido no queda impedido por estos atributos; la vigencia absoluta de sesión es de hasta 12 horas y la renovación no cambia el token. [ECL-83](ECL-83%20aviso%20de%20sesion.md). |
| **D — Denegación de servicio** | Automatizar intentos para consumir autenticación o bloquear repetidamente una cuenta objetivo. | Tres intentos fallidos bloquean esa cuenta por 15 minutos; Argon2id impone costo de verificación. [autenticacion.py](../../../backend/app/services/autenticacion.py), [test de persistencia del bloqueo](../../../backend/tests/integration/test_auth_persistence.py). | **Abierto:** no se identificó limitación de solicitudes por IP/origen ni métrica de bloqueos para alerta. El bloqueo de cuenta puede ser utilizado como vector de indisponibilidad. Seguimiento: [RSK-06](../../02%20Planificaci%C3%B3n/03%20Registro%20de%20riesgos%20V_1_0_0.md) / [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86); control preventivo por origen sin ticket de remediación identificado. |
| **E — Elevación de privilegios** | Un usuario cambia su rol en el cliente o usa una sesión para invocar funciones de otro rol. | El rol procede de la sesión del servidor; la autorización se aplica por permiso y el login de contraseña temporal obliga al cambio antes de operaciones. [dependencies.py](../../../backend/app/api/dependencies.py), [rbac.py](../../../backend/app/core/rbac.py), [pruebas de autorización](../../../backend/tests/unit/test_auth_dependencies.py). | **Residual:** el alcance efectivo depende de la corrección de la matriz RBAC y de proteger/revocar la sesión; no hay evidencia en este flujo de detección automática de cambios anómalos de rol. Seguimiento de alertas: [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). |

## 2. Restablecimiento de contraseña

**Activos:** cuenta objetivo; contraseña temporal y su hash; sesiones activas;
auditoría de actor, objetivo y revocaciones.

**Actores:** Administrador autenticado; usuario objetivo; atacante con sesión
administrativa comprometida; operador de la plataforma.

| STRIDE | Amenaza | Controles existentes (evidencia) | Riesgo residual y seguimiento |
|---|---|---|---|
| **S — Suplantación** | Usar la función para tomar control de una cuenta a través de un administrador suplantado o una sesión administrativa robada. | Solo Administrador puede restablecer a otra cuenta activa; la temporal expira a las 24 horas, se entrega una sola vez y fuerza cambio; se revocan las sesiones previas. [restablecimiento.py](../../../backend/app/services/restablecimiento.py), [RN-016 a RN-018](../../01%20Inicio/09.%20Reglas%20de%20negocio%20V_1_1_0.md), [pruebas de restablecimiento](../../../backend/tests/integration/test_password_reset.py). | **Residual:** la acción hereda el nivel de confianza de la sesión administrativa; no se identificó un segundo factor en el flujo revisado. Seguimiento: [RSK-06](../../02%20Planificaci%C3%B3n/03%20Registro%20de%20riesgos%20V_1_0_0.md) / [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86); remediación adicional no asignada en la información disponible. |
| **T — Manipulación** | Sustituir el usuario objetivo, reutilizar la temporal o dejar un cambio sin auditoría/revocación. | El actor se obtiene de la sesión; se excluye el autorrestablecimiento; la temporal se persiste como hash; cambio, revocación y auditoría se realizan en transacción. [usuarios.py](../../../backend/app/api/usuarios.py), [restablecimiento.py](../../../backend/app/services/restablecimiento.py), [DetalleContrasena](../../../backend/app/repositories/auditoria.py), [pruebas de atomicidad y sesiones](../../../backend/tests/integration/test_password_reset.py). | **Bajo:** las pruebas cubren el contrato y la atomicidad; un administrador con sesión válida conserva capacidad deliberada para cambiar la credencial de otra cuenta. Seguimiento de revisión: [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). |
| **R — Repudio** | El administrador niega haber restablecido una cuenta o la cuenta niega la revocación de sus sesiones. | Auditoría atómica con actor, objetivo y cantidad de sesiones revocadas, sin contraseña ni hash. [restablecimiento.py](../../../backend/app/services/restablecimiento.py), [auditoría tipada](../../../backend/app/repositories/auditoria.py), [RNF-017](../../01%20Inicio/07.%20Requisitos%20no%20funcionales%20V_1_2_0.md). | **Parcial:** el registro local permite trazabilidad, pero no se identificó una alerta ante volumen o patrón anómalo de restablecimientos. Seguimiento: [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). |
| **I — Divulgación de información** | Exponer la contraseña temporal en cachés, respuestas de error, logs o auditoría. | La temporal se entrega una vez con `Cache-Control: no-store` y `Pragma: no-cache`; solo se guarda su hash; los errores son saneados y el detalle de auditoría no contiene credenciales. [usuarios.py](../../../backend/app/api/usuarios.py), [restablecimiento.py](../../../backend/app/services/restablecimiento.py), [auditoria.py](../../../backend/app/repositories/auditoria.py), [test de secretos en respuestas/logs](../../../backend/tests/integration/test_password_reset.py). | **Residual:** la respuesta debe llegar al administrador autorizado para su entrega manual; exposición visual, captura o dispositivo administrativo comprometido no se evita con `no-store`. No se implementa envío por correo en este flujo. Seguimiento: [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). |
| **D — Denegación de servicio** | Repetir restablecimientos para revocar sesiones o dejar cuentas sin acceso. | La operación exige permiso administrativo, usuario objetivo válido/activo y revoca sesiones de forma transaccional; los fallos de almacenamiento no se presentan como éxito. [restablecimiento.py](../../../backend/app/services/restablecimiento.py), [usuarios.py](../../../backend/app/api/usuarios.py). | **Abierto/parcial:** no se identificó límite de frecuencia ni alerta para múltiples restablecimientos por actor/objetivo. Seguimiento de la brecha de alertamiento: [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86); no hay ticket de remediación de frecuencia identificado. |
| **E — Elevación de privilegios** | Un rol no administrador restablece credenciales o un administrador cambia su propia contraseña usando el flujo ajeno. | `require_permission` y autorización de servicio rechazan otros roles; el autorrestablecimiento devuelve conflicto y requiere el flujo de cambio normal. [usuarios.py](../../../backend/app/api/usuarios.py), [restablecimiento.py](../../../backend/app/services/restablecimiento.py), [pruebas de permisos](../../../backend/tests/unit/test_restablecimiento.py). | **Bajo:** depende de la protección de la sesión administrativa y de la matriz RBAC. Seguimiento: [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). |

## 3. Cola offline de incidencias

**Activos:** identidad/propietario de la cola; borrador y payload con tipo,
severidad, hora, ubicación y observación; `operation_id`; acuse del servidor;
itinerario consultado para validar contexto.

**Actores:** Conductor autenticado; persona con acceso al dispositivo/perfil del
navegador; atacante que manipule datos locales o reenvíe una operación.

| STRIDE | Amenaza | Controles existentes (evidencia) | Riesgo residual y seguimiento |
|---|---|---|---|
| **S — Suplantación** | Cambiar el propietario local o sincronizar una cola bajo la sesión de otro conductor. | La cola está indexada por propietario; antes de cada envío se comprueba el itinerario del propietario; el backend toma la identidad de la sesión, exige rol Conductor y compara `X-Expected-Owner-ID` con esa identidad. [incidentStorage.ts](../../../frontend/src/services/incidentStorage.ts), [incidentSync.ts](../../../frontend/src/services/incidentSync.ts), [incidencias.py](../../../backend/app/api/incidencias.py), [RN-020](../../01%20Inicio/09.%20Reglas%20de%20negocio%20V_1_1_0.md). | **Residual:** el propietario local no es una frontera criptográfica ante alguien que controle el perfil/dispositivo; la autorización final sigue siendo del servidor. Riesgo de continuidad/conectividad relacionado: [RSK-08](../../02%20Planificaci%C3%B3n/03%20Registro%20de%20riesgos%20V_1_0_0.md); revisión de alertas: [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). |
| **T — Manipulación** | Editar una incidencia guardada antes de sincronizarla o reutilizar su `operation_id` con contenido distinto. | Proyección explícita de campos al guardar borradores; validación del payload en servidor; clave idempotente por conductor y operación; contenido diferente devuelve conflicto sin sobrescribir. [incidentStorage.ts](../../../frontend/src/services/incidentStorage.ts), [incidencias.py](../../../backend/app/api/incidencias.py), [incidencias service](../../../backend/app/services/incidencias.py), [tests de sincronización](../../../frontend/src/services/incidentSync.test.ts). | **Parcial:** la edición local por una persona con acceso al navegador no se detecta criptográficamente; el servidor valida formato, identidad y reglas, pero no puede probar la intención original del conductor. Seguimiento del riesgo: [RSK-06](../../02%20Planificaci%C3%B3n/03%20Registro%20de%20riesgos%20V_1_0_0.md) / [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). |
| **R — Repudio** | El conductor niega el envío o la plataforma no puede correlacionar reintentos de una incidencia offline. | El servidor persiste actor, `operation_id` y acuse; el registro de auditoría se confirma en la misma transacción y contiene categorías/indicadores, no texto libre ni ubicación. [incidencias service](../../../backend/app/services/incidencias.py), [auditoria.py](../../../backend/app/repositories/auditoria.py), [test de idempotencia](../../../backend/tests/integration/test_incidencias.py). | **Parcial:** la auditoría no conserva una copia textual del payload; el contenido operativo está en el registro de incidencia. Se prioriza minimización de datos de auditoría. Seguimiento de privacidad: [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). |
| **I — Divulgación de información** | Extraer del dispositivo datos de ubicación/observación guardados mientras no hay conexión. | Se limita el borrador a campos explícitos y se separa la base IndexedDB de la cola de itinerario; en el servidor las proyecciones/listados limitan datos personales. [incidentStorage.ts](../../../frontend/src/services/incidentStorage.ts), [RN-022](../../01%20Inicio/09.%20Reglas%20de%20negocio%20V_1_1_0.md), [contrato ECL-98](ECL-98%20resolucion%20incidencias.md). | **Riesgo abierto, sin control de cifrado local identificado:** IndexedDB conserva ubicación y observación en el dispositivo y este código no cifra esos datos en reposo. Seguimiento: [RSK-06](../../02%20Planificaci%C3%B3n/03%20Registro%20de%20riesgos%20V_1_0_0.md) / [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). La información revisada no identifica un ticket Jira separado para cifrado/retención local; ECL-86 registra el riesgo, no lo remedia. |
| **D — Denegación de servicio** | Acumular reportes pendientes, agotar almacenamiento del navegador o impedir su sincronización con reintentos/fallos. | La cola conserva payload ante timeout/5xx, usa `operation_id` para evitar duplicados y la API valida límites de campo y responde errores sanitizados. [incidentSync.ts](../../../frontend/src/services/incidentSync.ts), [incidentStorage.ts](../../../frontend/src/services/incidentStorage.ts), [tests de sincronización](../../../frontend/src/services/incidentSync.test.ts), [RN-019 a RN-021](../../01%20Inicio/09.%20Reglas%20de%20negocio%20V_1_1_0.md). | **Riesgo abierto:** no se identificó límite explícito de cantidad/tamaño total de la cola local ni alerta de cola bloqueada; el almacenamiento disponible depende del navegador/dispositivo. Seguimiento: [RSK-08](../../02%20Planificaci%C3%B3n/03%20Registro%20de%20riesgos%20V_1_0_0.md) / [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86); ticket específico de cuota no identificado. |
| **E — Elevación de privilegios** | Un rol distinto de Conductor registra incidencias a nombre de un conductor o vincula una parada ajena. | El endpoint restringe el rol a Conductor; el actor se obtiene de la sesión; la API verifica propiedad de parada/jornada y el cliente no elige reportante ni estado. [incidencias.py](../../../backend/app/api/incidencias.py), [incidencias service](../../../backend/app/services/incidencias.py), [RN-019](../../01%20Inicio/09.%20Reglas%20de%20negocio%20V_1_1_0.md). | **Bajo:** el encabezado del propietario es solo una comprobación de consistencia, no autorización; la autorización efectiva está en el servidor. [incidencias.py](../../../backend/app/api/incidencias.py). |

## 4. Optimización de rutas

**Activos:** pedidos, vehículos y parámetros de optimización; resultados de
rutas/paradas y geodatos; disponibilidad de API/BD y capacidad de cálculo;
identidad del Operador solicitante.

**Actores:** Operador autorizado; usuario con otro rol; atacante externo; worker
como actor previsto por la arquitectura objetivo. En la implementación
documentada para este ticket, el cálculo se ejecuta en la solicitud API; no se
afirma que el worker/cola del diseño C4 esté desplegado.

| STRIDE | Amenaza | Controles existentes (evidencia) | Riesgo residual y seguimiento |
|---|---|---|---|
| **S — Suplantación** | Un atacante ejecuta o consulta optimizaciones como Operador. | La API obtiene identidad de sesión y requiere permisos separados para ejecutar, listar y consultar; el actor de la corrida no procede del cuerpo. [rutas.py](../../../backend/app/api/rutas.py), [ECL-96 contrato](ECL-96%20servicio%20de%20optimizacion.md), [rbac.py](../../../backend/app/core/rbac.py). | **Residual:** una sesión válida de Operador comprometida conserva esas capacidades hasta revocación/vencimiento. Seguimiento de detección de eventos: [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). |
| **T — Manipulación** | Manipular selección, fecha, recursos o parámetros para usar datos no elegibles o producir una corrida inconsistente. | Validación de selección y esquema; límites de 150 pedidos/15 vehículos; parámetros versionados; la corrida registra actor/instantánea y solo responde éxito tras persistir el resultado completo. [rutas.py](../../../backend/app/api/rutas.py), [optimizaciones.py](../../../backend/app/services/optimizaciones.py), [ECL-96 contrato](ECL-96%20servicio%20de%20optimizacion.md), [tests de API](../../../backend/tests/unit/test_rutas_api.py). | **Residual:** la validez y actualidad de los datos de entrada siguen dependiendo de los datos maestros y parámetros cargados por usuarios autorizados. Seguimiento de integridad: [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). |
| **R — Repudio** | El solicitante niega haber iniciado una corrida o cuestiona su resultado. | Cada optimización almacena `solicitada_por`, fecha, estado, versión de parámetros e instantánea; la autorización registra eventos permitidos/denegados. [modelo de datos](../../01%20Inicio/11.%20Base%20de%20datos%20V_1_4_0.md), [optimizaciones.py](../../../backend/app/services/optimizaciones.py), [autorizacion.py](../../../backend/app/services/autorizacion.py). | **Parcial:** no se identificó un evento de auditoría de negocio `OPTIMIZACION_SOLICITADA` separado del registro de autorización y de la fila de optimización. Seguimiento: [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86); confirmar con revisión técnica si el registro transaccional actual es evidencia suficiente. |
| **I — Divulgación de información** | Un rol no autorizado obtiene rutas, paradas, ubicaciones o información asociada al conductor. | Listado de optimizaciones con resúmenes sin datos personales; detalle de rutas restringido a Administrador/Operador; selección paginada y errores sin eco de identificadores/valores. [rutas.py](../../../backend/app/api/rutas.py), [ECL-96 contrato](ECL-96%20servicio%20de%20optimizacion.md), [RNF-004](../../01%20Inicio/07.%20Requisitos%20no%20funcionales%20V_1_2_0.md). | **Residual por diseño:** Administrador/Operador autorizado sí consulta detalles operativos y geográficos; debe protegerse su sesión y restringirse el acceso por rol. La matriz actual documenta alcance general, no aislamiento por operador solicitante. Seguimiento: [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). |
| **D — Denegación de servicio** | Solicitudes concurrentes de cálculo consumen CPU/recursos de la API o base y degradan otras solicitudes. | Límites de selección (150 pedidos/15 vehículos) y límite de búsqueda configurable; la corrida se marca FALLIDA con error seguro si el cálculo falla. [optimizaciones.py](../../../backend/app/services/optimizaciones.py), [rutas.py](../../../backend/app/api/rutas.py), [ECL-96 fuera de alcance](ECL-96%20servicio%20de%20optimizacion.md). | **Riesgo abierto:** el cálculo se ejecuta dentro de la solicitud y no se identificó cola de trabajos, worker ni límite de concurrencia/rate limit en el flujo actual. Seguimiento de rendimiento/desacoplamiento: [RSK-02](../../02%20Planificaci%C3%B3n/03%20Registro%20de%20riesgos%20V_1_0_0.md) / [ECL-21](https://continental-team-il84x39k.atlassian.net/browse/ECL-21). |
| **E — Elevación de privilegios** | Un Conductor, Analista o Auditor usa el endpoint de ejecución o el de detalle para acceder a funciones operativas. | Permisos `OPTIMIZACIONES_EJECUTAR` y `RUTAS_CONSULTAR` aplicados en cada endpoint con roles distintos; listado y detalle tienen permisos documentados. [rutas.py](../../../backend/app/api/rutas.py), [rbac.py](../../../backend/app/core/rbac.py), [tests de permisos](../../../backend/tests/unit/test_rutas_api.py). | **Bajo:** la cobertura depende de que endpoints nuevos mantengan las dependencias de permiso; incluir rutas añadidas en las pruebas RBAC de regresión. Seguimiento: [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). |

## 5. Regla de alerta propuesta — HTTP 5xx

**Estado: propuesta; no desplegada ni validada por el responsable técnico.**
ECL-60 instrumenta `ecolog_http_5xx_total` y
`ecolog_http_requests_total`, con etiquetas acotadas a método, plantilla de
ruta y estado (para requests); las métricas no incluyen cuerpos, credenciales,
tokens ni datos personales. La evidencia de ECL-60 acredita instrumentación,
no una campaña continua ni un sistema de alertamiento.

Propuesta para una plataforma compatible con Prometheus:

```yaml
- alert: EcoLogisticaHttp5xxRateHigh
  expr: |
    (
      sum(rate(ecolog_http_5xx_total[5m]))
      /
      sum(rate(ecolog_http_requests_total[5m]))
    ) > 0.01
    and
    sum(rate(ecolog_http_requests_total[5m])) > 0
  for: 5m
  labels:
    severity: warning
    service: ecologistica-api
  annotations:
    summary: "Tasa HTTP 5xx superior al 1%"
    description: "La tasa agregada supera el umbral durante la ventana sostenida; revisar disponibilidad de la API."
```

El umbral de 1% toma como referencia RNF-008, pero la ventana de cinco minutos
es una propuesta de operación, no un requisito ya aprobado. La notificación
debe incluir únicamente nombre de alerta, servicio, periodo y valor agregado;
no adjuntar request/response, identificadores de usuario, contraseñas, tokens,
ubicaciones ni observaciones.

**Confirmación solicitada a Antony Munive (@ANTONY-MUNIVE):** validar si esta
regla es implementable con la instrumentación ECL-60 en su estado actual,
considerando que los contadores son locales al proceso y que `GET /metrics`
requiere permiso `INDICADORES_CONSULTAR`. Confirmar también el scraping/
autenticación y destino de alertas. Hasta esa confirmación, no se declara
implementable, activa ni aceptada.

Evidencia: [métricas ECL-60](../../../backend/evidencias/ECL-60/metricas.prom),
[contrato de `/metrics`](../../../backend/app/api/metrics.py),
[implementación de métricas](../../../backend/app/monitoring/metrics.py),
[limitaciones de la evidencia ECL-60](../../../backend/evidencias/ECL-60/README.md),
[RNF-008](../../01%20Inicio/07.%20Requisitos%20no%20funcionales%20V_1_2_0.md).

## 6. Resumen de riesgos abiertos

| Riesgo | Flujo / amenaza | Control no identificado o insuficiente | Ticket de seguimiento |
|---|---|---|---|
| Intentos distribuidos y bloqueo abusivo de cuentas | Login — S/D | Bloqueo por cuenta existente; límite por origen y alerta de bloqueos no identificados. | [RSK-06](../../02%20Planificaci%C3%B3n/03%20Registro%20de%20riesgos%20V_1_0_0.md) / [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). Sin ticket separado de remediación identificado. |
| Exposición de datos offline en el dispositivo | Cola offline — I | IndexedDB no cifra en reposo ubicación/observación; no hay ticket específico de cifrado/retención identificado. | [RSK-06](../../02%20Planificaci%C3%B3n/03%20Registro%20de%20riesgos%20V_1_0_0.md) / [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). |
| Crecimiento de cola offline | Cola offline — D | No se identificó cuota funcional para cantidad/tamaño total de pendientes ni alerta de sincronización detenida. | [RSK-08](../../02%20Planificaci%C3%B3n/03%20Registro%20de%20riesgos%20V_1_0_0.md) / [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). Sin ticket específico de cuota identificado. |
| Saturación de API por optimizaciones | Optimización — D | Cálculo síncrono; el worker/cola es parte de EN-003, no se afirma implementado aquí. | [RSK-02](../../02%20Planificaci%C3%B3n/03%20Registro%20de%20riesgos%20V_1_0_0.md) / [ECL-21](https://continental-team-il84x39k.atlassian.net/browse/ECL-21). |
| Detección tardía de actividad anómala | Login, restablecimiento y optimización — R | Eventos de auditoría y métricas disponibles, pero no se encontró en el repositorio una regla ni canal de alertas desplegado. | [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86). Regla 5xx propuesta en este documento, pendiente de Antony. |

Las referencias a Jira documentan seguimiento, no confirman estado, prioridad,
responsable ni cierre. Cuando no se encontró un ticket específico para
remediación, se declara expresamente; no se asigna una clave inventada.

## Referencias

- [ECL-99 — Convenciones y glosario del Sprint 4](CONVENCIONES_Y_GLOSARIO_ECL99.md)
- [ECL-83 — Aviso y renovación de sesión](ECL-83%20aviso%20de%20sesion.md)
- [ECL-96 — Servicio de optimización](ECL-96%20servicio%20de%20optimizacion.md)
- [ECL-98 — Resolución de incidencias](ECL-98%20resolucion%20incidencias.md)
- [ECL-60 — Instrumentación de métricas](../../../backend/evidencias/ECL-60/README.md)
- [ECL-86 en Jira](https://continental-team-il84x39k.atlassian.net/browse/ECL-86)

[← Índice del Sprint 4](README.md) · [← Volver al README principal](../../../README.md)
