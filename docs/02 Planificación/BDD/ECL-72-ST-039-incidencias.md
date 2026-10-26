# ECL-72 / ST-039 — Reglas y BDD de incidencias

> **Estado: APROBADO.** Aprobada por Julio el 25/10/2026 23:29 (America/Lima)
> en el [PR #63](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/63).
> Especifica comportamiento esperado; no acredita implementación ni ejecución
> de pruebas.

| Metadato | Valor |
|---|---|
| Versión | 1.0.0 |
| Fecha de elaboración | 25/10/2026, America/Lima |
| Autor | Frank Roy Yupanqui Acevedo — @FrankRoyYA |
| Revisor requerido | Julio Armando Naupari Camarena — @JulioNaupariC |
| Aprobación de Julio | 25/10/2026 23:29 (America/Lima) en el [PR #63](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/63) |

## Trazabilidad y alcance

| Campo | Referencia |
|---|---|
| Subtarea | [ECL-72 / ST-039](https://continental-team-il84x39k.atlassian.net/browse/ECL-72) — Definir reglas y casos BDD de incidencias |
| Historia padre | [ECL-18 / US-012](https://continental-team-il84x39k.atlassian.net/browse/ECL-18) — Registrar incidencias de operación y seguridad vial |
| Sprint | Sprint 3 |
| Requisitos principales | RF-012; RN-008, RN-010; RNF-006 |
| Controles transversales | RF-001; RN-002, RN-015; RNF-003, RNF-004 |
| Fuente operativa | Ticket y contrato provisional proporcionados por Frank en esta tarea |
| Dependientes | ECL-73: API (Antony); ECL-74: formulario (José); ECL-75: vista de Operación (Giancarlo); ECL-76: pruebas (José) |
| Fuera de alcance | Implementar API, migraciones o pantallas; ejecutar ECL-76; validar incidencias mediante un endpoint nuevo; implementar motor de reoptimización o bloqueos viales |

Las precisiones técnicas de este borrador son propuestas para aprobación, no
modificaciones de la línea base. La clasificación por ruta dorada, feliz,
infeliz y de borde corresponde a caminos del flujo de usuario y de prueba.

## Fuentes consultadas

- [RF-012 y RF-001 — Requisitos funcionales](<../../01 Inicio/06. Requisitos funcionales V_1_0_0.md>).
- [RN-002, RN-008, RN-010 y RN-015 — Reglas de negocio](<../../01 Inicio/09. Reglas de negocio V_1_0_0.md>).
- [RNF-006, RNF-003 y RNF-004 — Requisitos no funcionales](<../../01 Inicio/07. Requisitos no funcionales V_1_1_0.md>).
- [Entidad incidencia — Modelo de datos](<../../01 Inicio/11. Base de datos V_1_1_0.md>).
- [Actores y matriz RBAC](<../../01 Inicio/08. Usuarios V_1_0_0.md>).
- [Definition of Done](<../01 Transformando a ágil V_1_0_0.md#8-definition-of-done-dod-global>).
- [Retrospectiva del Sprint 2 — acción A4](<../../03 Implementación/04 Retrospectiva del Sprint V_1_0_0.md>).
- [Modelo de formato: BDD de conductores](<ECL-47-ST-021-conductores.md>).

## Reglas respaldadas por la línea base

| ID | Regla | Consecuencia |
|---|---|---|
| RF-012 | Registrar tipo, ubicación, hora, severidad y observación; quedar pendiente de validación. | El registro no equivale a una incidencia validada; datos incompletos conservan borrador local e indican faltantes. |
| RNF-006 | Conservar último itinerario y encolar reportes sin red. | La recuperación de conectividad sincroniza la cola; ECL-76 debe verificar 10 pruebas, todas satisfactorias. |
| RN-002 | Autorizar por rol y asignación cuando corresponda. | El servidor deriva al reportante de la sesión y comprueba la pertenencia de la parada si se informa. |
| RN-008 | Ante un incidente validado, reoptimizar solo paradas pendientes. | Crear la incidencia no dispara por sí solo una reoptimización; las paradas atendidas se preservan en el futuro motor. |
| RN-010 | Una alerta no prohíbe automáticamente una vía; aumenta su costo salvo bloqueo configurado por Administrador. | Ni el tipo ni la severidad autorizan un bloqueo automático. Aplicar el costo pertenece a planificación, fuera de ECL-72. |
| RNF-003 / RNF-004 | Control de acceso y minimización de datos. | Errores sin eco del contenido enviado; listado sin DNI, teléfono ni licencia. |
| RN-015 / modelo de datos | Auditoría y conservación de datos operativos. | El alta deja trazabilidad sin copiar observación, coordenadas ni datos personales al detalle de auditoría. |

## Contrato candidato para revisión — no aprobado

### Tipos de incidencia

Se conservan los seis valores del contrato provisional. Las definiciones
siguientes precisan su uso y requieren ratificación de Julio.

| Tipo | Definición |
|---|---|
| `TRAFICO` | Congestión o demora de circulación observada durante la operación. |
| `AVERIA` | Falla mecánica o técnica del vehículo que dificulta o impide continuar. |
| `ACCIDENTE` | Siniestro vial propio o presenciado que afecta la operación. |
| `CLIMA` | Condición meteorológica que afecta la circulación o entrega. |
| `SEGURIDAD` | Riesgo de seguridad vial o personal observado, sin asumir que confirma un delito. |
| `OTRO` | Incidencia operativa que no encaja en los tipos anteriores. |

### Severidades

| Severidad | Criterio de uso |
|---|---|
| `BAJA` | Permite continuar la operación sin interrupción y sin riesgo inmediato observado. |
| `MEDIA` | Dificulta o interrumpe temporalmente la operación y requiere evaluación de Operación, sin peligro inmediato observado. |
| `ALTA` | Impide continuar con seguridad o presenta peligro inmediato para personas o vehículo; requiere atención prioritaria de Operación. |

La severidad la declara el Conductor según lo observado; no es validación de
Operación. Todos los tipos admiten las tres severidades. Ninguna combinación
crea automáticamente un bloqueo de vía, una validación o una reoptimización.

### Campos y validación

| Campo | Obligatorio | Regla propuesta |
|---|:---:|---|
| `operation_id` | Sí | UUID versión 4 generado por el cliente una vez por reporte y conservado durante todos sus reintentos. |
| `tipo` | Sí | Uno de los seis valores exactos del catálogo; sin valores libres. |
| `severidad` | Sí | `BAJA`, `MEDIA` o `ALTA`, en mayúsculas. |
| `ocurrida_en` | Sí | Fecha y hora ISO 8601 con zona u offset; se admite hasta 5 minutos hacia el futuro respecto del reloj del servidor al recibir el primer envío, inclusive, por desfase del reloj del celular. Se compara el instante en UTC. Sin antigüedad máxima para permitir la cola offline. |
| `latitud` | Sí | Número finito entre -90 y 90, inclusive; no cadena, booleano, NaN o infinito. |
| `longitud` | Sí | Número finito entre -180 y 180, inclusive; no cadena, booleano, NaN o infinito. |
| `parada_id` | No | UUID de una parada del itinerario asignado al conductor y jornada del reporte; omitido o `null` significa sin parada. Una referencia mal formada o inexistente recibe 422 genérico; una existente ajena recibe 403 genérico. |
| `observacion` | No | Texto de 0 a 500 puntos de código Unicode, inclusive; sin truncar ni recortar antes de medir. Omitido o `null` se normaliza a cadena vacía. No incluir datos personales reales. |
| Reportante / conductor | Servidor | Se deriva exclusivamente de la sesión; el cuerpo no acepta `reportada_por`, `conductor_id` ni `usuario_id`. |
| `ruta_id` | Servidor | Si existe `parada_id` autorizado, se deriva de su ruta. Sin parada se permite incidencia sin ruta, asociada al conductor autenticado (decisión de Frank, pendiente de Julio). |
| Estado inicial | Servidor | `PENDIENTE_VALIDACION`; el cliente no puede enviarlo ni elegir otro estado. |
| `incidencia_id`, `registrada_en` | Servidor | UUID e instante de registro generados al crear; se conservan en reenvíos. |

Los campos obligatorios omitidos, `null` o con tipo incorrecto son inválidos.
Los campos de entrada no definidos se rechazan con 422; así se impide intentar
suplantar al reportante o fijar el estado. Coordenadas válidas no demuestran
pertenencia a Lima ni precisión GPS. La ubicación se representa en WGS84 /
SRID 4326; si se usa un punto PostGIS, el orden es longitud, latitud.

### Permisos y proyecciones

| Operación | Permiso / alcance | Permitidos | Rechazados con 403 si tienen sesión |
|---|---|---|---|
| `POST /conductor/incidencias` | `incidencias.crear`, propio | Conductor, a su nombre | Administrador, Operador, Analista y Auditor |
| `GET /incidencias?estado=PENDIENTE_VALIDACION&page=1&page_size=20` | `incidencias.consultar`, general | Administrador y Operador | Conductor, Analista y Auditor |

Sin sesión válida ambos endpoints responden 401. La autorización se comprueba
en servidor también durante reenvíos. Ocultar botones no sustituye el control.
Una sesión Conductor sin perfil vinculado no puede crear y recibe 403 genérico.

La matriz global incluye lectura propia del Conductor, agregada del Analista y
lectura del Auditor. Este contrato restringe **este listado operativo**; no
revoca esas capacidades globales ni crea sus endpoints. Cualquier consulta
adicional requiere su propio alcance y proyección. Esta distinción debe
ratificarse en el PR para no interpretar el listado como toda la matriz RBAC.

El listado devuelve exclusivamente `incidencia_id`, `tipo`, `severidad`,
`ocurrida_en`, `registrada_en`, `conductor` (`conductor_id`, `nombre`),
`latitud`, `longitud`, `observacion` y `estado`; metadatos `page`, `page_size`,
`total`. No incluye DNI, teléfono ni licencia. El estado admitido en este
contrato es `PENDIENTE_VALIDACION`; otro valor recibe 422. `page` es entero ≥1;
`page_size` entero entre 1 y 100, por defecto 20. Orden principal:
`ocurrida_en` descendente; desempate propuesto: `incidencia_id` ascendente.
Sin resultados o con página fuera del total: 200, `items: []` y total real.

### Respuestas e idempotencia

| Caso | Respuesta | Efecto |
|---|---|---|
| Primer alta válida | 201 con `incidencia_id`, `operation_id`, `estado`, `registrada_en` | Una incidencia, una traza de alta. |
| Mismo `operation_id` y contenido equivalente del mismo conductor | 200 con la misma respuesta del alta | No crea otra incidencia ni repite la traza de alta. |
| Mismo `operation_id` y contenido distinto del mismo conductor | 409 genérico | Conserva el original; no lo actualiza ni devuelve su contenido. |
| Datos inválidos | 422, códigos/campos a corregir sin valores enviados | No persiste incidencia ni reserva `operation_id`. |
| Falta de sesión / permiso | 401 / 403 genérico | No crea ni entrega datos protegidos. |

La clave idempotente propuesta es `(conductor autenticado, operation_id)`;
otro conductor no puede recuperar el reporte ajeno usando su UUID. El mismo
UUID usado por dos conductores identifica operaciones independientes.
El alta y la reserva de clave deben ser atómicas para cubrir reintentos
concurrentes; la unicidad se conserva mientras exista la incidencia.

Contenido equivalente significa igualdad de `tipo`, `severidad`, instante
`ocurrida_en`, valor numérico de ambas coordenadas, `parada_id` y observación.
Se normalizan UUID a su valor, fechas al mismo instante UTC, y los opcionales
según la tabla anterior. El orden de claves JSON y escribir una coordenada como
`-12.0` o `-12` no cambian el contenido. El texto restante se compara exacto,
incluidos espacios y mayúsculas. Un replay válido no reasigna al conductor ni
altera fecha, estado o vínculo del registro original. La validación del
esquema y los permisos preceden a la comprobación idempotente; esta precede a
revalidar el contexto cambiante de la parada para no invalidar un alta ya hecha.

### Borrador local, cola y sincronización

1. Mientras se completa el formulario se conserva un borrador local del
   conductor. Si faltan campos o hay datos inválidos se muestran los campos a
   corregir, se mantiene lo escrito y no se presenta como registrado.
2. Un reporte completo sin red se almacena de forma persistente en la cola
   local con su `operation_id`, contenido y propietario. La interfaz muestra
   «Pendiente de sincronización», distinto del estado del servidor.
3. Se conserva el último itinerario cargado, incluso al recargar la pantalla
   sin red. Al volver la red, se envía la cola de la cuenta propietaria.
4. Solo 201 o 200 idempotente confirman el envío y retiran el elemento de la
   cola pendiente. La interfaz muestra «Pendiente de validación» y su ID.
5. Un timeout, pérdida de respuesta o 5xx conserva la entrada para reintento
   con la misma clave y contenido. No se genera otra clave automáticamente.
6. Ante 401 se pausa hasta reautenticación de la misma cuenta; 403, 409 o 422
   conservan el reporte con error visible y detienen su reintento automático.
   Corregir un reporte rechazado sin alta conserva su clave; ante 409 se
   requiere resolver el conflicto antes de crear expresamente otro reporte.
7. Cambiar de cuenta nunca envía ni muestra la cola o borrador de otro
   conductor. No se guardan cookies, contraseñas o tokens dentro de la cola.
   Si el navegador no puede persistir, se avisa que no se pudo guardar y no se
   muestra una confirmación de encolado exitosa.

## Datos de prueba previstos

Todos los usuarios, identificadores y textos serán sintéticos. Para pruebas
temporales se fija reloj de servidor en `2026-10-27T09:16:02-05:00` (T0);
es un fixture futuro, no la fecha de ejecución ni un resultado real.

```json
{
  "operation_id": "2d7d7ad5-57e1-4b17-9c8d-5094a6fc7a01",
  "tipo": "AVERIA",
  "severidad": "ALTA",
  "ocurrida_en": "2026-10-27T09:15:00-05:00",
  "latitud": -12.0464,
  "longitud": -77.0428,
  "observacion": "Llanta pinchada: reporte de prueba"
}
```

Conductor A y Conductor B representan perfiles de prueba distintos. Para
casos con parada, José deberá preparar una parada de A y otra de B con su ruta
y jornada; no basta con inventar un UUID sin relación persistida.

## Escenarios Gherkin — ruta dorada

### I01 — Registrar una incidencia válida sin ruta

- **DADO** Conductor A autenticado, con perfil vinculado y el cuerpo válido del fixture sin parada.
- **CUANDO** envía `POST /conductor/incidencias`.
- **ENTONCES** recibe 201 con ID, operación, `PENDIENTE_VALIDACION` y fecha de registro del servidor.
- **Y** se crea una sola incidencia a nombre de A, sin ruta ni parada, con sus datos y una traza de alta sin contenido personal.

## Escenarios Gherkin — ruta feliz

### I02 — Operación consulta los pendientes

- **DADO** incidencias pendientes sintéticas con horas distintas y una sesión Administrador u Operador (ejecutar para cada rol).
- **CUANDO** solicita el listado por defecto y sus páginas.
- **ENTONCES** recibe 200 con la proyección definida, total correcto y orden descendente de ocurrencia.
- **Y** no recibe DNI, teléfono ni licencia; se verifica también el desempate y que páginas consecutivas sobre datos sin cambios no repiten elementos.

### I03 — Registrar con parada propia

- **DADO** Conductor A autenticado y una parada de su itinerario y jornada del reporte.
- **CUANDO** registra una incidencia válida con esa `parada_id`.
- **ENTONCES** recibe 201 y el servidor asocia la ruta de esa parada y el reportante A.
- **Y** no bloquea la vía, no valida automáticamente la incidencia y no modifica paradas atendidas ni dispara reoptimización.

## Escenarios Gherkin — ruta infeliz

### I04 — Datos incompletos conservan el borrador

- **DADO** un formulario de A con cada campo obligatorio ausente por separado y luego varios ausentes.
- **CUANDO** intenta enviar.
- **ENTONCES** la interfaz indica los campos faltantes, conserva el borrador tras recargar y no lo marca encolado ni registrado.
- **Y** si se llama directamente a la API con esos datos recibe 422, sin incidencia, reserva idempotente ni eco de los valores enviados.

### I05 — Hora futura o sin zona

- **DADO** datos válidos salvo `ocurrida_en` igual a T0 + 5 min + 1 s, o una fecha sin zona (casos separados).
- **CUANDO** se envía con el reloj del servidor fijo en T0.
- **ENTONCES** recibe 422 que identifica el campo sin repetir su valor, no persiste y conserva el borrador corregible.

### I06 — Observación de más de 500 caracteres

- **DADO** una observación de 501 puntos de código Unicode y demás datos válidos.
- **CUANDO** intenta enviarla, también mediante llamada directa a la API.
- **ENTONCES** se indica el límite; la API devuelve 422 sin truncar, repetir el texto ni crear el registro, y la interfaz conserva el borrador.

### I07 — Catálogos, coordenadas, UUID y campos ajenos inválidos

- **DADO** datos válidos alterados por un caso de la tabla siguiente.
- **CUANDO** envía el registro directamente a la API.
- **ENTONCES** recibe 422 sin persistencia ni eco del cuerpo; la interfaz conserva el borrador para corregir.

| Variación independiente | Ejemplos de prueba |
|---|---|
| Catálogo inválido | Tipo `DESVIO` o severidad `URGENTE`; cadenas vacías. |
| Coordenadas inválidas | Latitud 90.0001 o -90.0001; longitud 180.0001 o -180.0001; booleano, cadena o no finito. |
| Operación inválida | UUID mal formado o UUID de versión distinta de 4. |
| Parada inválida | UUID mal formado o inexistente (mensaje genérico). |
| Suplantación / estado | Campo extra `conductor_id`, `usuario_id`, `reportada_por`, `ruta_id` o `estado`. |

### I08 — Crear con rol sin permiso

- **DADO** sesión Administrador, Operador, Analista o Auditor (cada rol por separado).
- **CUANDO** intenta crear una incidencia válida.
- **ENTONCES** recibe 403 genérico sin registro, aunque conozca un `operation_id` existente.

### I09 — Analista, Auditor o Conductor consultan pendientes

- **DADO** una sesión Analista, Auditor o Conductor (cada rol por separado).
- **CUANDO** solicita el listado operativo de pendientes.
- **ENTONCES** recibe 403 sin elementos, total ni datos personales.

### I10 — Sin sesión o con parada ajena

- **DADO** una solicitud sin sesión válida.
- **CUANDO** intenta registrar o consultar pendientes (ambos endpoints).
- **ENTONCES** recibe 401 sin datos ni alta.
- **DADO** Conductor A autenticado con `parada_id` existente de B.
- **CUANDO** intenta registrar una incidencia nueva con esa parada.
- **ENTONCES** recibe 403 genérico sin información sobre B ni persistencia.

### I11 — Mismo identificador con otro contenido

- **DADO** una incidencia de A creada con operación O y contenido C.
- **CUANDO** A reenvía O cambiando por separado tipo, severidad, hora, coordenadas, parada u observación por valores válidos distintos.
- **ENTONCES** recibe 409 sin sobrescribir C, crear otra incidencia ni exponer el contenido original en el error.
- **Y** el cliente conserva el conflicto visible sin reintentar automáticamente ni generar otro UUID.

## Escenarios Gherkin — ruta de borde

### I12 — Sin conexión, recarga y sincronización

- **DADO** A con último itinerario cargado y un reporte completo; el dispositivo pierde red.
- **CUANDO** envía, recarga sin red y luego recupera conectividad con sesión de A.
- **ENTONCES** conserva itinerario y reporte con la misma operación, muestra que está pendiente de sincronización y envía al recuperar red.
- **Y** al recibir 201 o 200 de replay retira el pendiente y muestra el ID y estado del servidor.
- **Y** se comprueba conservación y sincronización en 10 de 10 pruebas documentadas para RNF-006.

### I13 — Respuesta perdida, replay y concurrencia

- **DADO** un alta confirmada en servidor cuya respuesta no llega al cliente.
- **CUANDO** A reenvía el mismo contenido y operación, también en dos solicitudes concurrentes.
- **ENTONCES** cada replay recibe 200 con la misma respuesta original y existe una sola incidencia y una sola traza de alta.
- **Y** para dos primeros envíos simultáneos de una operación nueva, se obtiene un 201 y un 200, sin 5xx por la carrera.
- **Y** repetir con JSON reordenado, fecha equivalente en UTC, coordenadas numéricamente iguales y opcionales normalizados mantiene la equivalencia.

### I14 — Límites válidos y selección de catálogos

- **DADO** datos válidos con observación omitida, `null`, vacía o exactamente 500 caracteres; hora T0, T0 + 5 min o pasada sin antigüedad máxima; coordenadas en sus extremos (casos independientes).
- **CUANDO** registra cada caso con una operación nueva.
- **ENTONCES** recibe 201 y los valores se conservan según las reglas, sin rechazar por los límites permitidos.
- **Y** se ejecuta una matriz de los seis tipos por las tres severidades sin bloqueos automáticos.

### I15 — Paginación inválida y lista vacía

- **DADO** un Administrador u Operador autenticado.
- **CUANDO** consulta con `page=0`, `page_size=0`, `page_size=101`, valor no entero o estado distinto (casos independientes).
- **ENTONCES** recibe 422 sin devolver elementos.
- **DADO** un conjunto sin pendientes o una página posterior a la última.
- **CUANDO** consulta con parámetros válidos, incluido `page_size=100`.
- **ENTONCES** recibe 200 con `items: []`, parámetros y total real del filtro.

### I16 — Cambio de cuenta y fallos de sincronización

- **DADO** un pendiente local de A y luego una sesión de B en el mismo navegador.
- **CUANDO** vuelve la conectividad o B intenta usar el mismo UUID.
- **ENTONCES** el cliente no muestra ni envía el pendiente de A como B y la API no devuelve el registro de A; una operación válida de B es independiente.
- **Y** en pruebas separadas de timeout/5xx, 401, 403, 409 y 422 se conserva el pendiente y se aplica la política de reintento definida.
- **Y** si falla el almacenamiento local, se informa el fallo sin confirmar un guardado que no ocurrió.

## Trazabilidad y pruebas previstas — ECL-76

José implementará y ejecutará estas pruebas en ECL-76. Cada ID debe conservarse
en su matriz y evidencia, identificando commit, entorno, fecha real, datos
sintéticos, resultado esperado/obtenido y defecto cuando corresponda. Esta tabla
es un plan; no contiene resultados ejecutados. API/integración verificará
persistencia y permisos; interfaz verificará borrador, cola y mensajes.

| Escenario | RF / RN / RNF | Prueba prevista |
|---|---|---|
| I01 | RF-012; RN-002, RN-015 | API/integración: 201, autor desde sesión, vínculo sin ruta y auditoría mínima. |
| I02 | RF-012; RNF-004 | API/UI: ambos roles, proyección, orden y páginas con dataset fijo. |
| I03 | RF-012; RN-002, RN-008, RN-010 | Integración: parada propia y ausencia de efectos sobre rutas, bloqueos y optimización. |
| I04 | RF-012; RNF-006 | API + UI: faltantes individuales/combinados, recarga y borrador. |
| I05 | RF-012 | Unitarias/API/UI: reloj fijo, futuro y zona ausente. |
| I06 | RF-012; RNF-004 | Unitarias/API/UI: límite Unicode y error sin eco. |
| I07 | RF-012; RN-002; RNF-003 | Unitarias/API: validación parametrizada y campos extra. |
| I08 | RF-001, RF-012; RN-002 | API: matriz de cuatro roles sin alta. |
| I09 | RF-001, RF-012; RN-002; RNF-004 | API: Analista, Auditor y Conductor sin listado ni total. |
| I10 | RF-001, RF-012; RN-002; RNF-003 | API: sesión ausente/inválida, ambos endpoints y parada ajena. |
| I11 | RF-012; RNF-006 | API/UI: cambios de cada campo, 409 y original intacto. |
| I12 | RF-012; RNF-006 | UI/E2E/manual offline: 10/10 con conservación del itinerario, cola y sincronización. |
| I13 | RF-012; RNF-006 | Integración concurrente/UI: respuesta perdida, equivalencia y unicidad atómica. |
| I14 | RF-012; RN-010 | Unitarias/API: límites inclusivos y matriz 6 × 3. |
| I15 | RF-012; RNF-004 | API/UI: filtro, paginación y ausencia de resultados. |
| I16 | RF-001, RF-012; RN-002; RNF-003, RNF-004, RNF-006 | API/UI: aislamiento de cuentas, errores y fallo de persistencia local. |

RN-008 y RN-010 también requieren pruebas del futuro planificador para acreditar
el recálculo solo de pendientes y el aumento de costo frente a bloqueo explícito.
ECL-76 aquí verifica que registrar no ejecuta esos efectos; no acredita el motor.

## Cambios al contrato provisional

Se conservan endpoints, seis tipos, tres severidades, campos de solicitud y
respuesta y códigos principales. Las siguientes precisiones son propuestas
pendientes de Julio; Antony, José y Giancarlo deberán alinear API, pruebas y UI
con la versión que finalmente se apruebe.

| Precisión o diferencia | Motivo / origen | Impacto previsto |
|---|---|---|
| Permitir incidencia sin ruta cuando no hay parada | Decisión ratificada por Julio en el PR #63: permitirla asociada al conductor porque el modelo de rutas aún no existe. El modelo lógico relaciona incidencia con ruta y no define la excepción. | Ratificar nulabilidad de `ruta_id`; reportante obligatorio. Si requiere cambiar la línea base, tramitar control de cambios antes de aprobar; este PR no modifica el modelo aprobado. |
| Hora con tolerancia futura de 5 minutos, con zona y sin antigüedad máxima | Propuesta ratificada por Julio en el PR #63: admitir el desfase del reloj del celular hasta 5 minutos inclusive y permitir retraso offline sin antigüedad máxima. | Reloj controlado en pruebas; T0 + 5 min es válido y T0 + 5 min + 1 s recibe 422; errores de campo y borrador corregible. |
| Límites geográficos, Unicode y opcionales normalizados | El contrato daba máximo 500 y ejemplos, sin precisar unidades o equivalencias. | Validadores y contadores UI coherentes; no truncar silenciosamente. |
| Idempotencia por conductor + operación; equivalencia y carrera atómica | El contrato no definía alcance entre cuentas ni representación equivalente. | Unicidad, respuesta 200 estable y pruebas de concurrencia. |
| Parada propia, campos extra y perfil vinculado | Evitar suplantación y referencias ajenas. | 422/403 según reglas; reportante y ruta derivados por servidor. |
| Desempate del listado, estado permitido, páginas vacías y límites inferiores | El contrato solo fijaba orden principal y tamaño máximo. | Paginación verificable; mismo esquema de respuesta. |
| Listado de pendientes solo para Administrador y Operador, sin revocar la matriz global | Decisión pendiente de ratificación de Julio: restringir este listado operativo; la matriz global conserva las demás modalidades de lectura no incluidas en estos endpoints. | No confundir 403 del listado con revocación general; ratificación explícita en revisión. |
| Política de cola, errores, reautenticación y aislamiento local | RNF-006 y RF-012 exigen conservación; el contrato no detallaba fallos. | Mensajes y reintentos de UI; evita duplicados y envío entre cuentas. |

## Aprobación y entrega a los dependientes

1. Frank revisa el borrador y Julio resuelve las precisiones anteriores,
   incluida la relación opcional con ruta y el alcance del listado.
2. La política de PR exige auditoría técnica independiente antes de marcarlo
   listo para revisión humana. No se declara realizada en este documento.
3. Julio registra su aprobación real del PR. Solo después, por aviso de Frank,
   la cabecera pasa a `APROBADO`, versión 1.0.0 y fecha real de aprobación,
   enlazando la revisión. El cambio de cabecera requiere revalidación del
   nuevo commit y revisión según la política; no hereda automáticamente una
   aprobación del head anterior.
4. Frank comunica al equipo la versión aprobada y el enlace integrado. No se
   dan por desbloqueadas ECL-73/ECL-74/ECL-75/ECL-76 con este borrador.
5. El requisito de aprobación previa de A4 se verifica con fechas reales del
   PR y del inicio de implementación. Si hubo trabajo previo, se registra la
   desviación y se contrasta con la BDD; no se retrofecha la aprobación.

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 0.1.0 | 25/10/2026 | Borrador inicial con reglas, contrato candidato, escenarios y plan de trazabilidad para ECL-76. Aprobación de Julio pendiente. |
| 0.2.0 | 25/10/2026 | Tolerancia de 5 min en ocurrida_en y decisiones pendientes para aprobación de Julio. |
| 1.0.0 | 25/10/2026 | Aprobación de Julio registrada; [PR #63](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/63). |

[↑ Índice del Sprint 3](<../../03 Implementación/Sprint 03/README.md>)

[← Volver al README principal](../../../README.md)
