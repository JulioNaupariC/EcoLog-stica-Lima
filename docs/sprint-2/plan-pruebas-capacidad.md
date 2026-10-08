# Plan de pruebas de capacidad y disponibilidad — Sprint 2

**Proyecto:** EcoLogística Lima  
**Trazabilidad:** ECL-59 / ST-033 → ECL-23 / EN-005; RNF-007 (disponibilidad) y RNF-008 (capacidad).  
**Dependencias:** ECL-60 / ST-034 (instrumentación); ECL-61 / ST-035 (ejecución y evidencia).  
**Responsable del plan:** Julio Armando Naupari Camarena  
**Estado:** metodología propuesta; sin resultados de ejecución.

## 1. Objetivo y umbrales

Planificar ensayos reproducibles sobre la API FastAPI y PostgreSQL/PostGIS, con datos sintéticos y sin afectar producción.

| Indicador | Umbral |
|---|---|
| Volumen de referencia | 1,000 pedidos por día |
| Flota de referencia | 50 vehículos |
| Carga concurrente | 100 solicitudes activas |
| P95 de registro válido `POST /pedidos` | ≤ 2 segundos |
| Tasa de respuestas HTTP 5xx | < 1 % |
| Disponibilidad objetivo | ≥ 99.5 % en horario 05:00–22:00, zona `America/Lima` |

Los 1,000 pedidos/día expresan **volumen diario de negocio**; las 100 solicitudes concurrentes expresan **estrés instantáneo**. No son medidas equivalentes y se evaluarán por separado.

**Distribución horaria propuesta, verificable y repetible (zona `America/Lima`):** para cada jornada sintética generar exactamente los siguientes pedidos válidos, distribuyendo sus instantes de envío dentro de cada franja mediante una semilla fija del generador (guardar semilla y marcas programadas/reales). No se trata de una medición real ni de demanda histórica:

| Hora (inicio incluido, fin excluido) | Pedidos programados |
|---|---:|
| 05:00–06:00 | 20 |
| 06:00–07:00 | 30 |
| 07:00–08:00 | 45 |
| 08:00–09:00 | 65 |
| 09:00–10:00 | 80 |
| 10:00–11:00 | 90 |
| 11:00–12:00 | 100 |
| 12:00–13:00 | 110 |
| 13:00–14:00 | 100 |
| 14:00–15:00 | 90 |
| 15:00–16:00 | 80 |
| 16:00–17:00 | 70 |
| 17:00–18:00 | 50 |
| 18:00–19:00 | 30 |
| 19:00–20:00 | 20 |
| 20:00–21:00 | 15 |
| 21:00–22:00 | 5 |
| **Total 05:00–22:00** | **1,000** |

**Comprobación del escenario diario:** contar solicitudes programadas, emitidas, respuestas `201` válidas y registros persistidos por franja; cada suma debe conciliar con el manifiesto. Si hay reintentos, identificarlos por separado para no confundir intentos HTTP con pedidos únicos. Ejecutar este escenario a escala temporal real (17 h) cuando sea viable; cualquier aceleración se etiqueta **simulación comprimida** y no se afirma equivalente al perfil horario real. La prueba de 10 minutos con 100 solicitudes simultáneas corresponde exclusivamente al **perfil de estrés**, no a esta distribución diaria.

## 2. Herramienta y entorno reproducible

- **Herramienta prevista:** Locust (Python), con scripts versionados y versión de dependencia fijada en el entregable de ECL-61. Su ejecución aún no está implementada.
- **Entorno:** ambiente aislado de pruebas, aplicación FastAPI y PostgreSQL 16/PostGIS 3.5; registrar CPU, RAM, número de réplicas/workers, configuración de red, versión Git, fecha, semilla del generador de datos y versiones de componentes antes de cada corrida. No ejecutar contra producción.
- **Perfiles:** (A) volumen funcional de 1,000 registros válidos distribuidos dentro de una jornada simulada; (B) estrés de 100 usuarios virtuales con una operación `POST /pedidos` activa por usuario y sin tiempo de espera entre tareas, ajustando la generación de carga para verificar la simultaneidad real del lado servidor.
- **Flota:** precargar exactamente 50 vehículos sintéticos válidos en `vehiculo`, con diversidad de tipo y capacidad; verificar mediante consulta de conteo. La existencia de 50 vehículos representa dimensión de flota, **no** implica que `POST /pedidos` asigne vehículos ni los consulte durante cada solicitud.
- **Fases propuestas por repetición del perfil de estrés:** subida gradual de 0 a 100 clientes de carga durante 1 minuto (ramp-up), 2 minutos de calentamiento y 10 minutos de medición estable; 3 repeticiones independientes. Cada cliente mantiene como máximo un `POST /pedidos` activo; al recibir la respuesta, inicia otro sin espera artificial. **Cien usuarios virtuales no prueban cien solicitudes simultáneas**: se pretende mantener **al menos 100 solicitudes `POST /pedidos` en vuelo en el servidor** durante la fase estable. Si el modelo cerrado con 100 clientes no permite alcanzar ese nivel, se deberá ajustar el generador/la tasa de llegada y el número de clientes (sin cambiar el requisito de 100 solicitudes activas) y documentar la configuración real. Registrar inicio/fin de cada petición, número activo por segundo, máximo, mínimo, porcentaje de segundos con al menos 100 en vuelo, throughput y saturación del generador. Proponer como criterio operativo de sostenimiento **100 % de los segundos completos de la ventana estable con al menos 100 peticiones en vuelo**, excluida la subida/calentamiento; si no se cumple, el perfil no acredita RNF-008. Configurar sincronización entre el generador y la métrica del servidor, y dejar registrado el método de correlación de relojes.
- **Verificación de simultaneidad:** registrar eventos de inicio/fin por petición en el generador y métricas de solicitudes en vuelo **en el servidor** mediante ECL-60; muestrear al menos una vez por segundo y conservar series crudas (no solo capturas). La observación servidor es la evidencia primaria de concurrencia; el conteo de clientes virtuales y solicitudes iniciadas no la sustituyen. Registrar capacidad del generador (CPU, fallas, cola de envío); si el generador se satura, invalidar o repetir la prueba.
- **Aislamiento:** ejecutar fuera de los periodos de servicio real con credenciales sintéticas; sin datos personales. Registrar desviaciones y condiciones de cada repetición.

Los tiempos/duraciones anteriores son parámetros **propuestos** del plan, no una descripción de pruebas ya realizadas.

## 3. Preparación de datos, autenticación y flujo real

1. Preparar una base de pruebas **independiente, descartable y no compartida** y aplicar migraciones Alembic; comprobar `alembic current` y `alembic heads`, PostgreSQL/PostGIS y disponibilidad de la API. Anotar identificador de entorno, revisión Git, versiones, capacidad de infraestructura y configuración; efectuar copia/snapshot de un estado base sintético antes de cada ejecución. Nunca apuntar a producción.
2. Preparar datos **en orden de dependencias**: (a) crear credenciales de prueba mediante el mecanismo autorizado de aprovisionamiento (el servicio actual no expone alta pública de usuarios); (b) darles rol `OPERADOR`/`ADMINISTRADOR` y verificar `pedidos.crear`; (c) persistir clientes con ID conocido; (d) precargar exactamente 50 vehículos válidos; (e) verificar por consultas de conteo y FK que usuarios, clientes y vehículos existen; (f) generar el manifiesto de 1,000 pedidos por franja con `cliente_id` válido, UUID/identificador de correlación por intento y semilla reproducible. Registrar conteos previos **sin copiar credenciales o cookies** al informe. Una operación de prueba sin usuario, cliente o sesión válidos no forma parte del escenario de negocio exitoso.
3. Antes de la medición, cada cliente virtual debe iniciar sesión por **`POST /login`** con JSON `email` y `password`, validar `200` y conservar la **cookie HttpOnly de sesión** con el cliente HTTP de Locust. Confirmar acceso con una solicitud autorizada de control fuera de medición. Si una sesión caduca durante la prueba, separar la nueva autenticación y su duración del P95 de `POST /pedidos`, y registrar el evento. Configurar **timeout total de 10 segundos por `POST /pedidos`** y 5 segundos para `POST /login` y comprobaciones auxiliares; estos valores son parámetros propuestos y deben quedar fijados en el script versionado. Un timeout de 10 s no satisface el umbral de latencia P95 ≤2 s por sí solo.
4. Preparar cargas JSON válidas para **`POST /pedidos`**: `cliente_id` existente, `direccion`, `referencia` no vacía **o** latitud/longitud juntas, `peso_kg` y `volumen_m3` positivos, ventanas de tiempo con zona horaria y `ventana_fin > ventana_inicio`, `prioridad` permitida y `tipo_producto`. Generar referencias identificables por repetición, sin PII.
5. Ejecutar `POST /pedidos` y validar **HTTP 201**, JSON con `pedido_id` UUID y `cliente_id` esperado. Una respuesta 2xx distinta de 201 o un cuerpo inválido cuenta como error funcional.
6. Verificar persistencia con consultas de lectura a la base de prueba (conteo e IDs de pedidos creados) al terminar cada corrida. **No** incluir el tiempo de verificación SQL dentro del P95 HTTP de registro.
7. **Reinicio reproducible entre repeticiones:** terminar generadores y esperar respuestas/cancelaciones; exportar resultados y manifiesto con IDs; comprobar registros persistidos; detener conexiones al entorno aislado; **restaurar el snapshot/base de prueba sintética anterior a la repetición** (mismo esquema, usuarios, clientes y 50 vehículos, sin pedidos de esa repetición); verificar `alembic current`, número de usuarios/clientes/vehículos, **cero pedidos pertenecientes a la corrida previa** y semilla idéntica antes del próximo ramp-up. Si no se dispone de snapshot, crear una base de prueba nueva desde el mismo procedimiento de aprovisionamiento y contrastar el manifiesto/cuentas, sin reutilizar datos residuales. Nunca limpiar o restaurar una base compartida o de producción.
8. Separar la preparación, el inicio de sesión, el calentamiento, el escenario de registro y la verificación posterior en los registros y métricas.

Una corrida que no crea ni persiste pedidos válidos **no puede declararse satisfactoria**, aunque sus tiempos sean bajos.


### 3.1. Componentes existentes y procedimiento de aprovisionamiento previsto

Los enlaces siguientes apuntan a componentes reales del repositorio, relativos a este documento:

| Elemento | Componente implementado | Uso previsto y límites |
|---|---|---|
| Esquema y entorno | [Arranque y migraciones](../../README.md#arranque-local-con-docker-compose--ecl-29), [migración de usuarios](../../backend/alembic/versions/0001_create_usuario.py), [vehículos](../../backend/alembic/versions/0004_create_vehiculo.py), [clientes/pedidos](../../backend/alembic/versions/0006_create_cliente_pedido.py) | Crear una base aislada y aplicar migraciones. Las migraciones crean esquema, no el conjunto sintético. |
| Usuarios | [CredentialService.create](../../backend/app/services/credenciales.py), [UsuarioRepository](../../backend/app/repositories/usuarios.py), [contrato y transacción](../../backend/README.md#credenciales--ecl-30) | Crear credenciales con hash mediante el servicio interno; el llamador confirma o revierte la transacción. No existe alta pública de usuarios. |
| Clientes | [Modelo Cliente](../../backend/app/models/cliente.py), [ejemplos create_user/create_client](../../backend/tests/integration/test_pedido_http_e2e.py) | El ejemplo persiste Cliente con una sesión SQLAlchemy y obtiene su UUID. No existe API de alta de clientes; su CRUD pertenece a ECL-11. Las funciones del test son referencias técnicas, no un script de preparación de carga. |
| Vehículos | [POST /vehiculos](../../backend/app/api/vehiculos.py), [VehicleCreate](../../backend/app/schemas/vehiculo.py), [servicio](../../backend/app/services/vehiculos.py) | Alta autenticada con permiso vehiculos.crear y respuesta 201; usar placas únicas y campos válidos según VehicleCreate. |
| Login y permisos | [POST /login](../../backend/app/api/auth.py), [RBAC](../../backend/app/core/rbac.py) | Obtener cookie de sesión después de persistir los usuarios; OPERADOR/ADMINISTRADOR para pedidos y altas de vehículos. |

**Pendiente de ECL-61:** no existe un script integrado de aprovisionamiento ni de snapshot/restauración de este conjunto de carga. ECL-61 deberá versionar ese procedimiento, sus dependencias y parámetros, siguiendo los componentes anteriores. No se presenta ningún nombre de archivo o comando de ejecución inexistente como implementado. Hasta disponer de él y verificar su repetibilidad, la preparación y la campaña de carga permanecen pendientes.

**Orden y cantidades propuestas, verificables antes de medir:**

1. Crear la base descartable, aplicar las migraciones y confirmar que no hay datos de negocio residuales.
2. Fijar en el manifiesto el número de clientes de carga `U ≥ 100` (incluyendo cualquier ajuste de concurrencia). Crear exactamente `U` usuarios sintéticos ACTIVO con rol OPERADOR o ADMINISTRADOR mediante CredentialService.create, uno por cliente virtual; guardar solo IDs y roles en la evidencia pública. Verificar conteos, unicidad y permisos. Si cambia U, regenerar y verificar el estado base antes de medir.
3. Persistir exactamente **100 clientes sintéticos** con Cliente y una transacción SQLAlchemy, siguiendo el ejemplo enlazado; conservar sus UUID en el manifiesto. Este número es un parámetro del conjunto propuesto, no un requisito de negocio.
4. Iniciar sesión y crear exactamente **50 vehículos ACTIVO** mediante POST /vehiculos: 20 CAMIONETA, 20 FURGON y 10 MOTO, placas únicas y capacidades positivas. Validar cada 201 e ID; conciliar los 50 IDs y tipos con consultas de lectura a vehiculo. El generador fijará los valores y la semilla en el manifiesto.
5. Comprobar en BD exactamente U usuarios sintéticos, 100 clientes, 50 vehículos y **cero pedidos**, y que todos los cliente_id del manifiesto existen. Conservar el conjunto de IDs esperado; no basta comparar conteos si las identidades difieren.
6. Cerrar/revocar las sesiones usadas para aprovisionar vehículos y retirar sus filas del conjunto descartable mediante el procedimiento de ECL-61, sin tocar bases compartidas; verificar cero sesiones antes de capturar el estado base confirmado con esquema, usuarios, clientes y flota, antes del login de carga y del calentamiento. Ejecutar el calentamiento separado y correlacionar sus pedidos para excluirlos de métricas; el estado base no debe contener sesiones ni pedidos de corridas anteriores.
7. Entre repeticiones, aplicar la restauración aislada descrita en el paso 7 de la sección 3 mediante el procedimiento que entregue ECL-61: verificar revisión Alembic, conteos, IDs, roles, tipos y cero pedidos/sesiones residuales; contrastar semilla y manifiesto. Reautenticar los clientes virtuales después de restaurar. Si la verificación falla, no iniciar la siguiente repetición. Una base nueva debe reproducir el conjunto lógico; documentar cualquier cambio de UUID y regenerar sus referencias antes de medir.

## 4. Medición, cálculos y errores

- **P95 que determina la aceptación de RNF-008:** el **P95 de las solicitudes `POST /pedidos` con HTTP `201`, cuerpo válido y `pedido_id` efectivamente persistido**, registradas **únicamente durante la fase estable del perfil de estrés cuya concurrencia se haya demostrado**. Duración desde el inicio de la solicitud HTTP hasta recibir completamente su respuesta, en segundos. Ordenar las `N` duraciones válidas y tomar la posición `ceil(0.95 × N)` (rango más próximo). El criterio de aceptación es **P95 válido ≤2 s en cada una de las tres repeticiones**; además publicar el P95 agregado calculado reuniendo todas las duraciones válidas de las tres repeticiones, ordenándolas de menor a mayor y seleccionando la posición `ceil(0.95 × N_total)` (índice desde 1), donde `N_total = N_1 + N_2 + N_3`. **Está prohibido promediar los percentiles individuales, incluso con ponderaciones.** Si alguna repetición es inválida o no aprobada, el agregado se etiqueta diagnóstico y nunca acredita aceptación conjunta. **P95 de todos los intentos respondidos** se publica como diagnóstico, no reemplaza al P95 válido de aceptación. Excluir calentamiento, `POST /login`, salud y SQL de verificación. No excluir ni esconder respuestas fallidas: deben registrarse por separado y someterse a criterios de errores; si una repetición de estrés tiene menos de **1,000 pedidos únicos válidos y persistidos en sus 10 minutos estables**, la corrida es inválida y no aprobada. Este mínimo de 1,000 pedidos válidos por repetición de estrés es un **criterio metodológico adicional propuesto**, no un requisito literal de RNF-008, ni un nuevo umbral del requisito, ni equivalencia con el volumen diario.
- **Tasa HTTP 5xx:** `100 × cantidad de respuestas 500–599 / total de respuestas HTTP recibidas de POST /pedidos en fase estable`. Reportar N y numerador. Las respuestas 4xx **sí** se incluyen en el denominador, pero se informan aparte como fallos funcionales/autorización/validación, no como 5xx.
- **Timeouts y errores de conexión:** cada `POST /pedidos` agota a los **10 s** (parámetro propuesto). Si no hay respuesta HTTP, **no** cuenta como 5xx ni entra en el P95 válido; sí entra en intentos totales y en la tasa separada `fallos_sin_respuesta / intentos_totales`. Reportar 4xx, timeouts, fallos de transporte y respuestas/cuerpo inválidos; **cualquier timeout o error de transporte durante la fase estable impide aprobar esa repetición** hasta investigar y repetir; los 4xx de negocio/autorización tampoco pueden presentarse como registros válidos. No usar la exclusión de fallos del P95 para mejorar artificialmente el resultado.
- **Éxito funcional:** porcentaje de intentos con HTTP 201, `pedido_id` válido y persistencia comprobada. Informar fallos por categoría (4xx, 5xx, timeout, transporte, validación de respuesta, ausencia en DB).
- **Aceptación del perfil de estrés:** en **cada repetición**: (1) concurrencia servidor ≥100 `POST /pedidos` en vuelo sostenida en toda la ventana estable conforme al muestreo definido; (2) P95 **válido** de `POST /pedidos` ≤2 s; (3) respuestas HTTP 5xx / respuestas HTTP de `POST /pedidos` <1 %; (4) todas las respuestas `201` contabilizadas tienen `pedido_id` persistido; (5) sin timeouts/errores de conexión en fase estable; (6) cero respuestas 4xx, cero respuestas 2xx distintas de 201, cero cuerpos incorrectos y cero fallos de persistencia; (7) al menos 1,000 pedidos únicos válidos y persistidos durante los 10 minutos estables. Las reglas de invalidación siguientes son obligatorias. **Aceptación del volumen diario:** completar y persistir exactamente 1,000 pedidos únicos siguiendo la distribución propuesta y conciliar el manifiesto. Reportar por separado lo aprobado o no aprobado en cada perfil; el cumplimiento de un perfil no sustituye al otro.
- **Repeticiones:** informar cada ejecución y el resultado conjunto; ninguna repetición se descarta sin motivo documentado. Conservar exportaciones de Locust, trazas del backend, métricas de ECL-60, manifiesto anonimizado y versión Git.


### 4.1. Reglas objetivas por perfil

Para evitar sesgo de supervivencia, registrar cada intento y conciliar sus IDs, respuesta y persistencia. Un pedido válido requiere HTTP 201, cuerpo conforme al contrato, UUID único, cliente_id esperado y fila persistida coincidente. Un fallo de verificación de BD deja la corrida **NO EVALUABLE/no aprobada** hasta completar la evidencia; no se presume persistencia.

| Condición | Perfil diario | Perfil de estrés, por repetición |
|---|---|---|
| Población mínima | Exactamente 1,000 pedidos únicos válidos y persistidos, conciliados por franja con el manifiesto | Al menos 1,000 pedidos únicos válidos y persistidos en los 10 minutos estables; no contar calentamiento ni auxiliares |
| 4xx | Cualquier 4xx de registro invalida la corrida | Cualquier 4xx de registro en fase estable invalida la repetición |
| Respuesta/cuerpo incorrectos | Cualquier 2xx distinto de 201, cuerpo inválido, UUID duplicado o cliente_id incorrecto invalida | La misma regla, aplicada a fase estable |
| Persistencia | Cualquier 201 sin fila coincidente o discrepancia entre IDs/manifiesto/BD invalida | La misma regla para todos los 201 de fase estable |
| Timeouts y transporte | Cualquier fallo de registro invalida; se conserva el intento y se investiga | Cualquier fallo en fase estable invalida, aunque el P95 válido sea bajo |
| 5xx | Cualquier 5xx de registro invalida este perfil funcional estricto | Se permite únicamente tasa 5xx <1 % de respuestas HTTP de registro; ≥1 % impide aprobar. Deben cumplirse todos los demás criterios |
| Volumen y evidencia | Menos/más de 1,000 pedidos únicos o incumplimiento por franja invalida; una simulación comprimida no acredita horario real | Menos de 1,000 válidos invalida; evidencia insuficiente de concurrencia o saturación del generador invalida. P95 >2 s impide aprobar |

Estas reglas son parámetros metodológicos propuestos y no cambian los umbrales de RNF-008. La tolerancia 5xx del estrés no autoriza tolerar errores funcionales. No emitir reintentos automáticos que oculten errores: registrar por separado cada intento, incluso si después logra un pedido válido; el reintento no revierte una invalidación. Si un 5xx deja una fila persistida, registrarla como discrepancia de conciliación, no como pedido válido.

Los fallos de preparación, login o calentamiento se conservan fuera del P95 estable y obligan a resolver la causa y reiniciar la preparación antes de medir; no se permite continuar con sesiones o datos inválidos. Para aceptar la campaña deben aprobarse las tres repeticiones independientes y el perfil diario, sin seleccionar únicamente las corridas favorables.

### 4.2. Consulta del tablero — cobertura pendiente de RNF-008

RNF-008 exige registrar pedidos **y consultar el tablero**, según [requisitos no funcionales](<../01 Inicio/07. Requisitos no funcionales V_1_1_0.md>). En el estado revisado de la rama, [la aplicación FastAPI](../../backend/app/main.py) registra routers de salud, autenticación, pedidos y vehículos: **no existe un endpoint de consulta del tablero**. GET /vehiculos o GET /health no sustituyen esa función.

La dependencia funcional es **ECL-15 / US-009 — Consultar dashboard de operación y sostenibilidad**, identificada en [la planificación](<../02 Planificación/02 Artefactos Jira V_1_0_0.md>). ECL-61 deberá integrar la consulta real cuando ECL-15 esté implementado y su contrato/permiso estén disponibles; ECL-60 aportará sus métricas. Antes de ejecutar esa cobertura, versionar ruta real, payload/filtros, rol, respuestas esperadas, proporción/cadencia de consultas y duración del escenario. Estos parámetros están pendientes; no se inventa una ruta ni se atribuye una ejecución.

La prueba prevista consultará el tablero durante el escenario de registro, con datos sintéticos conciliados, validando respuesta autorizada y contenido agregado frente a BD. Conservar intentos, respuestas, latencias, errores y comprobaciones por separado; una respuesta/cuerpo incorrecto, fallo de persistencia/consistencia de los datos consultados, 4xx, timeout o error de transporte impedirá aprobar esta cobertura. Informar la tasa 5xx de consulta y exigir <1 %, sin diluir la tasa de POST /pedidos con respuestas del tablero.

El P95 de registro y la evidencia de ≥100 POST /pedidos en vuelo mantienen su población original: las consultas del tablero no cuentan como registros ni reemplazan su concurrencia; publicar sus métricas separadamente. No se introduce un umbral de latencia de tablero que RNF-008 no establece. **Hasta implementar y ejecutar esta cobertura, el cumplimiento integral de RNF-008 permanece PENDIENTE**, aunque aprueben los perfiles de registro.

## 5. Disponibilidad y observación mensual

- **Periodo:** mes calendario completo, zona `America/Lima`, de 05:00 incluido a 22:00 excluido cada día (17 horas operativas diarias), menos únicamente las ventanas de mantenimiento previamente anunciadas que coincidan con ese horario. Una observación parcial no acredita SLA mensual.
- **Frecuencia prevista de sondeo:** una verificación automática **cada 60 segundos** desde una ubicación de monitoreo declarada. Registrar timestamp con zona horaria, latencia, resultado HTTP y estado de conectividad a base.
- **API disponible:** respuesta HTTP 200 de `GET /health` dentro de 5 s **y** comprobación separada de conexión y lectura `SELECT 1` en PostgreSQL dentro de 5 s. El `GET /health` actual solo acredita el proceso; no acredita la base de datos. El comprobador de BD para monitoreo periódico queda pendiente de implementar en ECL-60 o en la herramienta operativa definida por el equipo.
- **Minutos disponibles:** intervalos completos del calendario operativo con ambas comprobaciones exitosas. Si hay fallo de API o BD, contabilizar indisponibilidad. Si un sondeo está ausente o el agente de monitoreo no responde, marcar `SIN_DATOS` y **no** computarlo como disponible; publicar cobertura de observación y evaluar conservadoramente esos intervalos como no disponibles hasta aclaración documentada.
- **Cálculo mensual RNF-007:** `disponibilidad ajustada (%) = 100 × minutos disponibles fuera de mantenimiento anunciado / (minutos operativos del mes - minutos de mantenimiento anunciado dentro del horario)`; tratar intervalos `SIN_DATOS` como no disponibles de forma conservadora hasta aclaración con evidencias. Calcular también `disponibilidad bruta (%) = 100 × minutos disponibles del horario / minutos operativos totales`. Publicar minutos programados, mantenimientos excluidos, minutos evaluables, éxitos, fallos, sin datos, cobertura y justificación de cada corrección. Si el denominador ajustado es cero, informar `NO EVALUABLE`, nunca 100 %.
- **Mantenimientos anunciados (RNF-007):** el requisito **sí establece expresamente su exclusión** del SLA mensual. Para aplicar la exclusión, exigir anuncio **previo** y trazable con inicio/fin, zona horaria, canal, responsable y alcance; el anuncio debe identificar la ventana de mantenimiento. Calcular `minutos_operativos_evaluables = minutos_operativos_totales - minutos_de_mantenimiento_anunciado_que_coincidan_con_el_horario_operativo`; restar esas ventanas **también** del numerador de minutos posibles y publicar la lista/total excluido. Mantenimiento no anunciado o tiempo fuera de la ventana comunicada **no se excluye**. Informar disponibilidad bruta (sin exclusiones) y ajustada según RNF-007 (valor usado para aceptación), cobertura y bitácora. Confirmar con el equipo el procedimiento operativo de anuncio; no inventar anuncios retrospectivos.
- **Criterio objetivo:** disponibilidad mensual ≥99.5 % durante la jornada. No confundir resultados de una corrida de carga o de una jornada con el SLA del mes.

## 6. Trazabilidad y evidencia del PR

- Documento de esta subtarea: **`docs/sprint-2/plan-pruebas-capacidad.md`**, dentro del PR #23 (`docs/ecl-23-st-033`). Actualizar **tanto** la descripción del PR **como** el enlace/evidencia en Jira ECL-59 para que apunten a esta ruta exacta. La carpeta `documentos/sprint-2/` no es la ruta canónica del repositorio.
- En Jira: **ECL-59 / ST-033 → ECL-23 / EN-005**, **RNF-007 Disponibilidad**, **RNF-008 Capacidad**; instrumentación ECL-60 / ST-034 y ejecución ECL-61 / ST-035 quedan explícitamente fuera de este PR.

## 7. Evidencias y entregables

- Script Locust, procedimiento integrado de aprovisionamiento/restauración, dependencias fijadas, configuración de entorno y semilla de datos (**a crear por ECL-61**).
- Contrato real y evidencia de consulta del tablero: dependencia ECL-15; integración de carga/evidencia por ECL-61, aún pendientes.
- Manifiesto de 1,000 pedidos sintéticos/día y 50 vehículos; recuentos y verificación de persistencia.
- Registro de 100 usuarios virtuales frente a solicitudes en vuelo realmente observadas.
- Resultados por repetición y agregados: respuestas HTTP 201, 4xx, 5xx, fallos sin respuesta, percentiles y observaciones.
- Exportaciones del generador, métricas instrumentadas por ECL-60 y registro del SLA mensual, con disponibilidad/cobertura y exclusiones justificadas.
- Enlaces al PR, Jira, versión Git y declaración explícita de limitaciones.

## 8. Responsabilidades y cierre

- **Julio — ECL-59 / ST-033:** definir y revisar esta metodología; no atribuirse instrumentación o mediciones ejecutadas.
- **Antony — ECL-60 / ST-034:** instrumentar y exponer métricas de API/BD y ayudar a verificar solicitudes activas y sondeos operativos.
- **José — ECL-61 / ST-035:** implementar scripts de carga, ejecutar repeticiones y producir evidencia de resultados reales.
- **Julio — ST-036:** documentar SLA, hallazgos y respuesta operativa cuando existan datos comprobados.

**Estado de esta revisión:** únicamente **planificación metodológica**. No se ha ejecutado una campaña de carga, no se ha medido P95 ni se ha demostrado disponibilidad mensual.
