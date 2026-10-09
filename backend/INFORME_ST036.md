# Informe técnico ECL-62 / ST-036 — Resultados, SLA y operación

**Fecha de consolidación:** 9 de octubre de 2026, America/Lima.  
**Trazabilidad:** ECL-62 / ST-036 → ECL-23 / EN-005; RNF-007 y RNF-008.  
**Rama:** docs/ECL-62-resultados-sla-operacion. **Base revisada:** 8035345.  
**Responsable previsto de esta entrega en Jira:** Julio Armando Naupari Camarena.
La autoría efectiva del commit/PR debe corresponder a quien lo realice.

## 1. Dictamen

Los registros disponibles muestran P95 inferior a 2 s y 0% de HTTP 5xx en las
tres poblaciones de estrés finalizadas. **No se acredita RNF-008 integral**:
no se observaron 100 solicitudes activas sostenidas en todos los segundos,
el observador presentó retrasos y falta la consulta del tablero ECL-15.

**SLA mensual ≥99.5%: NO MEDIDO.** Los sondeos de corridas breves no cubren un
mes operativo y sus porcentajes no son un SLA mensual.

Se recalcularon los resultados desde los archivos crudos sin ejecutar carga nueva
ni modificar evidencias anteriores. Las 40 comprobaciones de contenido/población
coinciden; la comprobación adicional de hashes no pasa completamente.
Persisten cuatro discrepancias de logs PostgreSQL. No se certifica integridad
de bytes del conjunto completo mientras no se aclaren.

## 2. Fuentes y entorno

- [Plan ST-033](../docs/sprint-2/plan-pruebas-capacidad.md): objetivos y metodología.
- [Validación ST-034](VALIDACION_ST034.md) y [evidencia de instrumentación](evidencias/ECL-60/README.md).
- [Validación ST-035](VALIDACION_ST035.md) y [registro de incidencias](evidencias/ECL-61/INCIDENCIAS.md).
- [Consolidación de campaña](evidencias/ECL-61/campaign-20261009/campaign-consolidated.json):
  incluye la recuperación y conserva la corrida interrumpida.
- [Auditoría original](evidencias/ECL-61/campaign-20261009/audit.json), manifiestos,
  JSONL comprimidos de intentos/persistencia y series de sondeos.
- [Verificación derivada de ST-036](evidencias/ECL-62/verificacion-fuentes.json).

Las mediciones ST-035 declaran base Git 468e4167c165f540668abaa5c04f0b292ef78c77
con cambios locales aún sin commit. Las fuentes exportadas documentan ese estado:
no afirmar que se midió exactamente el HEAD actual.

Entorno registrado: Windows 11, Python 3.12.6, PostgreSQL 16.15, PostGIS 3.6.2,
FastAPI 0.141.1, Uvicorn 0.53.0, SQLAlchemy 2.0.54 y Locust 2.46.7.
32 CPU lógicas/24 físicas y 16,890,322,944 bytes de RAM.
Una réplica/worker; pools de negocio y auditoría separados, cada uno 5+10.
API, BD, generador y observador comparten host y red local; no representa producción.
PostGIS 3.6.2 difiere del 3.5 fijado en Compose; la equivalencia no se presupone.

Por perfil: 100 usuarios OPERADOR, 100 clientes y 50 vehículos sintéticos
(20 CAMIONETA, 20 FURGON, 10 MOTO); cero pedidos y sesiones antes del login.
Semilla 35061, bases independientes. Jornada comprimida a 180 s.
Estrés: 60 s de subida +120 s de calentamiento +600 s estables.
Se mantiene declarada la tolerancia de cierre de 1 s de ST-035; no modifica umbrales.

## 3. Resultados y comparación

P95 exacto por rango más próximo: posición ceil(0.95 × N) de las duraciones
ordenadas de respuestas 201 válidas conciliadas con PostgreSQL por UUID,
cliente y referencia. Login, calentamiento y auxiliares quedan fuera.
Los percentiles aproximados de Locust no sustituyen este cálculo.
El porcentaje 5xx usa respuestas HTTP de POST /pedidos del perfil como denominador;
4xx, timeouts, transporte y errores funcionales se publican aparte.

| Perfil | Intentos / válidos persistidos | P95 válido (s) | HTTP 5xx | Segundos ≥100 / 600 | Huecos de concurrencia | Dictamen |
|---|---:|---:|---:|---:|---:|---|
| Jornada comprimida | 1,000 / 1,000 | 0.023460 | 0/1,000 = 0% | No aplica | No aplica | Volumen/franjas conciliados; no jornada real de 17 h |
| Estrés 1 | 55,414 / 55,414 | 1.751248 | 0/55,414 = 0% | 114 (19%) | 26 s | Latencia/error favorables; carga sostenida no acreditada |
| Estrés 3 | 70,395 / 70,395 | 1.219589 | 0/70,395 = 0% | 117 (19.5%) | 5 s | Latencia/error favorables; carga sostenida no acreditada |
| Estrés 2 recuperado | 77,989 / 77,989 | 1.098492 | 0/77,989 = 0% | 126 (21%) | 6 s | Latencia/error favorables; carga sostenida no acreditada |
| Estrés 2 interrumpido | 100 / 0 en fase etiquetada estable | No evaluable | 0/100 = 0%; 100 respuestas 401 | No evaluable | Ventana inválida | Excluido del agregado; conservado como incidencia |

**Agregado diagnóstico:** 203,798 pedidos válidos persistidos;
P95 **1.497054 s**, calculado sobre todas sus duraciones, sin promediar percentiles.
Sólo incluye estrés 1, estrés 3 y la recuperación independiente.
La jornada y la corrida interrumpida quedan fuera.

| Objetivo | Evidencia medida | Conclusión |
|---|---|---|
| 1,000 pedidos/día | 1,000 pedidos y 17 franjas conciliados en simulación de 180 s | Volumen sintético verificado; jornada real pendiente |
| 50 vehículos | Baselines verifican 50 activos por perfil | Dimensión de datos verificada; no implica asignación de rutas |
| P95 de registros válidos ≤2 s | 1.751248 /1.219589 /1.098492 s | Cumple numéricamente en estas poblaciones; no certifica carga sostenida requerida |
| HTTP 5xx <1% | 0% en las tres corridas finalizadas | Cumple numéricamente; no oculta 401 de la corrida inválida |
| 100 POST en vuelo sostenidos | 19% /19.5% /21% de segundos ≥100 | No acreditado; objetivo operativo del plan es 100% de segundos completos |
| Consulta del tablero | No existe cobertura ECL-15 en esta evidencia | Pendiente; salud/flota no la sustituyen |
| SLA mensual ≥99.5% | Sin mes operativo completo observado | NO MEDIDO |

Las tres corridas terminadas registran cero errores funcionales/transporte y
cero discrepancias de persistencia en su población estable.
La interrupción del segundo perfil presenta un salto compatible con suspensión
del host de aproximadamente 6 h 45 min, sesiones vencidas y 37 filas sin respuesta
válida conciliada en todas sus fases. La causa exacta no está diagnosticada;
no atribuirlo a capacidad normal de la API ni eliminar la corrida desfavorable.

La jornada conserva 55 adelantos de hasta 1.297 ms y retraso máximo de 99.643 ms;
los conteos por franja coinciden con el plan. Esto no convierte la simulación en
una observación de demanda real.

## 4. Sondeos observados y cobertura

Sondeos ST-035 cada 1 s desde el mismo host. Cada muestra comprueba /health y
/health/ready (SELECT 1), con sus estados/latencias. Se agrupan intervalos de
1 s desde la primera observación, deduplicando ráfagas; cualquier fallo marca
el intervalo como fallido. No se interpolan éxitos sobre huecos.

Todas las horas de la tabla corresponden al **9 de octubre, America/Lima (UTC−05)**.
Se convierten desde los timestamps UTC originales; se muestran segundos truncados.

| Perfil | Ventana local | Muestras correctas/total | Intervalos correctos/esperados | Fallidos | Sin datos | Proporción conservadora de intervalos |
|---|---|---:|---:|---:|---:|---:|
| Jornada | 04:07:34–04:11:04 | 211/211 | 211/211 | 0 | 0 | 100% |
| Estrés 1 | 04:11:14–04:24:15 | 782/782 | 756/782 | 0 | 26 | 96.675% |
| Estrés 3 | 11:10:39–11:23:40 | 782/782 | 764/782 | 0 | 18 | 97.698% |
| Recuperación | 11:25:12–11:38:14 | 783/783 | 780/783 | 0 | 3 | 99.617% |
| Interrumpida | 04:24:26–11:10:26 | 151/152 | 147/24,361 | 1 | 24,213 | 0.603% |

Éxito de muestras, cobertura de intervalos y concurrencia son poblaciones diferentes.
Por ejemplo, estrés 3 tiene 5 s sin muestra válida de concurrencia y 18 intervalos
sin datos de disponibilidad. No intercambiar denominadores.

La jornada y estrés 1 ocurrieron antes de 05:00; los perfiles restantes cubren
ventanas cortas o interrumpidas, no toda la operación del mes.
Los espacios entre corridas son tiempo sin observación, no disponibilidad ni
mantenimiento anunciado. No convertir estos porcentajes en un SLA mensual.

## 5. Fórmula, calendario y procedimiento del SLA

Periodo: mes calendario completo en America/Lima, cada día desde **05:00 incluido
hasta 22:00 excluido**, 17 h/día. Sondeo previsto cada 60 s desde una ubicación
de monitoreo identificada. Guardar timestamp con zona, latencia, HTTP de API,
lectura de BD, estado y cobertura, según ST-033.

Definir:
- T: minutos operativos del mes (días ×17 ×60).
- M: minutos de mantenimiento anunciado previamente, intersectados con el horario
  operativo y deduplicados; 0 ≤ M ≤ T.
- E = T − M: minutos evaluables.
- V: minutos disponibles observados fuera de M.
- F: minutos fallidos fuera de M.
- S: minutos SIN_DATOS fuera de M, tratados conservadoramente como no disponibles.

Conciliación: **E = V + F + S**. API y BD deben responder correctamente dentro de 5 s
para clasificar un intervalo como disponible. El sondeo discretiza disponibilidad:
no garantiza continuidad perfecta entre observaciones.

**SLA ajustado (%) = 100 × V / E**, si E >0; de lo contrario **NO EVALUABLE**.
**Disponibilidad bruta (%) = 100 × V_bruta / T**, con V_bruta contando éxitos
observados en todo el horario, sin excluir mantenimiento.
Publicar ambos porcentajes, cobertura observada (V+F)/E y minutos de cada categoría.
Objetivo de aceptación: SLA ajustado **≥99.5%**; indisponibilidad admisible **≤0.005 × E**.
Cero datos o un último gauge positivo no significan 100% de disponibilidad.

Para octubre de 31 días, **T =31 ×17 ×60 =31,620 min**.
Sin mantenimientos excluidos, el presupuesto objetivo es **158.1 min**.
Estos valores de calendario no son resultados medidos de octubre.

**Ejemplo didáctico, no medición:** T=31,620; M=120; E=31,500;
V=31,380; F=90; S=30. SLA ajustado=99.619%, cobertura=99.905%.
Si durante los 120 min de mantenimiento tampoco se observó disponibilidad,
V_bruta=31,380 y disponibilidad bruta=99.241%.
El ejemplo ilustra la fórmula; no acredita cumplimiento del proyecto.

Para cerrar cada mes:
1. Construir el calendario operativo y convertir todos los timestamps a America/Lima.
2. Unir y recortar las ventanas anunciadas; conservar anuncio previo, responsable,
   canal, alcance, inicio/fin y zona horaria. No crear exclusiones retrospectivas.
3. Clasificar todos los intervalos esperados: disponible, fallido o SIN_DATOS.
   Sondeos duplicados no compensan huecos; intervalos fallidos prevalecen sobre éxitos.
4. Restar M también de los minutos posibles del numerador; reconciliar E=V+F+S.
5. Calcular bruta/ajustada, cobertura, presupuesto y desviaciones; conservar series.
6. Julio revisa el informe con evidencia y el equipo valida correcciones y conclusiones.

Mantenimiento no anunciado o fuera de su ventana no se excluye.
Confirmar con el equipo el canal/procedimiento de anuncios antes de aplicarlo.
El mes de esta entrega carece de la observación necesaria: **SLA NO MEDIDO**.

## 6. Procedimientos de diagnóstico y respuesta

La asignación siguiente es **propuesta operativa basada en los roles del proyecto**,
pendiente de ratificación del equipo. No introduce tiempos contractuales nuevos.

| Responsable | Función propuesta |
|---|---|
| Julio — líder | Coordinar incidencia, comunicar impacto, autorizar mantenimiento y consolidar resultados/SLA |
| Antony — backend/optimización | Diagnosticar API, sesiones, PostgreSQL, pools y métricas; proponer correcciones |
| José — frontend/QA | Revisar generador/observador, reproducir fallos y verificar recuperación/carga |
| Giancarlo — UX/UI | Comprobar impacto visible y mensajes al usuario en Chrome/Firefox |
| Frank — requisitos | Confirmar impacto funcional, criterios y prioridad con el equipo |

### A. API o base de datos no disponibles

1. Registrar hora/zona, entorno, versión, alcance y primer síntoma.
2. Comprobar /health y /health/ready desde el observador; guardar estados y latencias.
   /health=200 con readiness=503 indica fallo de lectura/tiempo BD, no proceso caído.
3. Revisar servicios y logs sin publicar secretos:

```powershell
docker compose --env-file .env ps
docker compose --env-file .env logs --since 10m --tail 200 backend db
docker compose --env-file .env exec -T backend python -m app.db.check
docker compose --env-file .env exec -T backend python -m alembic current
docker compose --env-file .env exec -T backend python -m alembic heads
```

Los comandos son para el despliegue Compose existente; la campaña ST-035 utilizó
procesos locales aislados y requiere sus propios logs, no estos contenedores.
No imprimir docker compose config expandido ni compartir .env, cookies o dumps.
Revisar logs antes de adjuntarlos; pueden contener información sensible.

4. Antony distingue conectividad, permisos, saturación, migraciones y fallo del proceso.
   No ejecutar migraciones, reinicios o restauraciones sin diagnóstico y alcance claros.
5. Julio coordina mitigación y comunicación. No borrar volúmenes ni detener servicios
   de otros equipos; un reinicio no equivale a reparación de datos.
6. Verificar proceso y SELECT 1 dentro de 5 s, y una operación funcional sintética
   autorizada. José conserva nuevas muestras; no rellena el periodo fallido con éxitos.

### B. Latencia alta, errores 5xx o concurrencia insuficiente

1. Comparar las mismas rutas, fases, respuestas y poblaciones; separar 4xx, transporte
   y errores funcionales. Cero tráfico no acredita un percentil ni tasa de errores.
2. Consultar /metrics con sesión autorizada y conservar series: duraciones, conteos
   HTTP/5xx, solicitudes en vuelo, operaciones SQL y última lectura BD.
   Un 401/403 de métricas no demuestra caída de API; comprobar sesión/permisos.
   Con BD caída la autenticación de métricas puede fallar: usar también sondeos externos.
3. Antony revisa API/BD/pools; José revisa lag, huecos, CPU/RAM y capacidad del generador.
   API y carga compartiendo host impiden atribuir la causa exclusivamente a un componente.
4. Registrar hipótesis y decisión antes de cambiar pools o arquitectura.
   Ajustar clientes/tasa o separar observador sólo como nueva corrida documentada;
   conservar la evidencia anterior y repetir las tres repeticiones y conciliación.
5. No dar por aprobado RNF-008 hasta sostener 100 POST en vuelo y cubrir el tablero real.

### C. Suspensión del host, sesiones expiradas o huecos del observador

1. Guardar timestamps UTC/local, lag y estados; verificar reloj y eventos del equipo.
2. Marcar SIN_DATOS y declarar inválida una ventana alterada; no atribuir causa exacta
   sin registros del sistema ni confundir 401 con 5xx.
3. Julio coordina la disponibilidad de un host dedicado; José verifica configuración
   de suspensión y estado del generador. Antony revisa expiración normal de sesiones.
4. Repetir preparación/login fuera de medición sobre una base nueva; no concatenar
   fragmentos favorables para fabricar una repetición completa.

### D. Discrepancias de integridad de evidencia

1. Comparar SHA256 de bytes contra el manifiesto original, sin regenerarlo para ocultar diferencias.
2. Separar diferencias CRLF/LF demostrables de cambios de contenido no explicados.
3. Conservar original/copia revisada y solicitar al productor de ST-035 su log cerrado
   y la hora en que calculó el manifiesto. El crecimiento posterior del log es hipótesis,
   no causa demostrada.
4. José verifica exportación y Julio revisa la cadena de evidencias.
   No certificar integridad global hasta aclarar las cuatro discrepancias.
5. ST-036 no altera fuentes, manifiestos ni logs de ST-035.

### Registro y cierre de una incidencia

Registrar ID, inicio/detección/fin con zona, impacto, responsables, versión, evidencia,
hipótesis frente a causa comprobada, acciones autorizadas, resultado y minutos
disponibles/fallidos/SIN_DATOS/mantenimiento. Adjuntar una comparación antes/después.

Cerrar cuando la causa o mitigación esté documentada, se verifique recuperación
funcional y de sondeos y Julio revise el impacto. Una corrección no borra la
indisponibilidad ya ocurrida. Los hallazgos pendientes conservan su estado.

## 7. Integridad y verificación de esta consolidación

La nueva auditoría offline deshabilitó la escritura del audit.json de ST-035:
**40/40 comprobaciones de contenido y cálculo coinciden; files:sha256 falla**.
El audit.json original registra consistencia en su momento; ese resultado histórico
no sustituye la verificación actual.

Manifiesto global evidence-sha256.json: **186 entradas**, 177 hashes exactos,
5 diferencias explicadas por CRLF/LF y 4 discrepancias sin resolver.
Los archivos comprimidos de intentos/persistencia contrastados mantienen sus hashes.
Ver valores esperados/actuales y comprobaciones en
[verificacion-fuentes.json](evidencias/ECL-62/verificacion-fuentes.json).

Logs pendientes:
- campaign-20261009/postgres.log
- recovery-20261009/postgres.log
- smoke2/postgres.log
- smoke3/postgres.log

Los cinco textos equivalentes al normalizar CRLF/LF también coincidieron con sus
bytes versionados en HEAD. La normalización fue sólo para comparar; no se modificaron.
La inconsistencia de logs limita el respaldo completo del entorno, aunque los cálculos
numéricos pueden reproducirse desde los registros conservados.

ST-036 no vuelve a ejecutar carga ni atribuye como nuevas las pruebas unitarias de
ST-034/ST-035. La verificación de esta entrega cubre recálculo offline, fuentes,
enlaces, fórmulas y diff de documentación.

## 8. Conclusiones y próximos pasos

1. Se dispone de resultados reales comparables con umbrales; las latencias y 5xx
   observados son favorables, con sus poblaciones y limitaciones declaradas.
2. Capacidad integral pendiente por concurrencia, observación y tablero; repetir
   en entorno objetivo y con generación/sondeo adecuados.
3. SLA mensual no medido; preparar observación del calendario completo y anuncios
   de mantenimiento trazables antes de emitir un porcentaje de cumplimiento.
4. Resolver integridad de logs y ratificar responsables/procedimientos con el equipo.
5. Esta entrega queda preparada para commit/PR y revisión; su versionado en GitHub
   se acredita cuando el usuario publique y el equipo revise, no por este archivo.
