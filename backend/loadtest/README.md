# ST-035 / ECL-61 — ejecución reproducible

Este paquete ejecuta HTTP real contra FastAPI y PostgreSQL/PostGIS locales.
No modifica servicios, pools, permisos ni reglas de negocio de la aplicación.
Referencia: [plan ST-033](../../docs/sprint-2/plan-pruebas-capacidad.md).

## Requisitos

Python 3.12, dependencias de `requirements-load.lock`, PostgreSQL 16 con PostGIS
instalado y sus binarios `initdb`/`pg_ctl`. En Windows la ejecución verificada
usa PostgreSQL 16.15/PostGIS 3.6; esta diferencia frente a PostGIS 3.5 del plan
debe mantenerse visible en cualquier comparación con Docker/producción.
No se requiere Docker. El script verifica que sus dos puertos estén libres.

Desde `backend`, con el entorno virtual activado:

```powershell
python -m pip install -r requirements-load.lock
python -m pip check
python -m loadtest.campaign --pg-bin "C:/Program Files/PostgreSQL/16/bin" --output "evidencias/ECL-61/mi-campana"
python -m loadtest.report "evidencias/ECL-61/mi-campana"
python -m loadtest.audit "evidencias/ECL-61/mi-campana"
```

Usar una carpeta de salida nueva: el comando rechaza sobrescribir evidencia.
En Linux `--pg-bin` debe apuntar a los binarios PostgreSQL de la instalación;
no ejecutar `initdb` como root. La ejecución Linux no ha sido validada aquí.

## Aislamiento y ciclo de vida

El comando crea un clúster nuevo en `.tmp-st035-pg/<timestamp>` dentro del
repositorio, con escucha exclusiva en `127.0.0.1:55455`. Usa autenticación
`trust` **solo para este clúster local descartable**, con datos sintéticos;
otro proceso del equipo podría acceder mientras está activo. No es una
configuración de despliegue ni debe ejecutarse en un equipo compartido.
No lee DATABASE_URL para seleccionar una base compartida.
Se puede cambiar `--pg-port` y `--api-port` si esos puertos están ocupados.

Cada perfil crea una base nueva sin eliminar ni restaurar bases existentes.
Habilita PostGIS, aplica Alembic y compara la revisión con `head`. Crea mediante
CredentialService un usuario OPERADOR por cliente virtual, 100 clientes y,
mediante POST /vehiculos, 20 CAMIONETA, 20 FURGON y 10 MOTO.
Antes de medir verifica identidades, roles, conteos, cero pedidos y cero
sesiones. Se retiran únicamente sesiones de preparación de esa base nueva.
La contraseña aleatoria permanece en memoria/entorno de procesos; nunca se
exportan cookies, hashes ni credenciales. Los clientes de carga hacen POST /login.

El comando detiene los procesos API, sondeo y clúster al finalizar. Conserva
las bases en la carpeta ignorada para inspección posterior. Si se mata el
proceso desde el administrador de tareas, verificar los logs y los procesos
propios antes de iniciar otra corrida. No borrar ni detener servicios ajenos.
En Windows solicita impedir la suspensión automática mientras dura la campaña
y libera esa solicitud al terminar, sin cambiar el plan de energía ni mantener
la pantalla encendida. La suspensión manual puede interrumpir una prueba;
esa corrida debe conservarse como inválida y repetirse.

Para repetir únicamente una medición interrumpida en otra base y carpeta:

```powershell
python -m loadtest.campaign --pg-bin "C:/Program Files/PostgreSQL/16/bin" --output "evidencias/ECL-61/recuperacion" --profiles stress2
```

`--profiles` selecciona perfiles aislados; no convierte un subconjunto en una
campaña completa de tres repeticiones. Conservar y enlazar ambas ejecuciones.

Para consolidar una recuperación después de completar las otras dos ventanas:

```powershell
python -m loadtest.consolidate evidencias/ECL-61/campaign-20261009 evidencias/ECL-61/recovery-20261009
python -m loadtest.audit evidencias/ECL-61/campaign-20261009
python -m loadtest.report evidencias/ECL-61/campaign-20261009
```

Esto crea `campaign-consolidated.json` y conserva los `campaign.json` nativos.
La auditoría y el reporte prefieren el consolidado si existe. El archivo
conserva la corrida interrumpida y sus incidencias; su población se excluye
del agregado y se sustituye por la ventana repetida completa. Esto no cambia
los umbrales ni convierte una carga no acreditada en aprobada.

## Perfiles y límites de interpretación

- Jornada: exactamente 1,000 intentos, horarios y semilla 35061 del plan,
  comprimidos a 180 segundos. Las marcas programadas y reales quedan en JSONL.
  El envío es secuencial; si el servidor se atrasa, el registro conserva el
  retraso. `--daily-seconds 61200` permite programar las 17 horas reales,
  pero esa ejecución no se realizó en esta entrega. El perfil largo requiere
  ampliar TTL y añadir renovación de sesión antes de una corrida de 17 h;
  el perfil ejecutado dura menos de los 60 minutos de sesión configurados.
- Estrés: 100 clientes sin pausa artificial, subida de 60 s, calentamiento de
  120 s y medición de 600 s; tres bases/repeticiones independientes. Cada
  cliente mantiene como máximo un POST /pedidos activo. `--users` permite
  ajustar el generador hasta 300, sin alterar el requisito de concurrencia
  real de 100 peticiones en el servidor.
- Cada POST registra inicio, fin, fase, latencia, status, UUID y correlación.
  No hay reintentos ocultos. El timeout HTTP es de 10 s; el generador de estrés
  añade un deadline con gevent de 10 s. Login y auxiliares usan timeout 5 s.
- P95 usa rango más próximo `ceil(0.95*N)` sobre 201 válidos conciliados por
  UUID, cliente y referencia contra BD. Se publican también fallos y P95 de
  respondidos; nunca se promedian percentiles por repetición.
- 5xx usa únicamente respuestas HTTP de POST /pedidos en fase estable como
  denominador. 4xx, cuerpos inválidos, IDs duplicados, discrepancias SQL y
  fallos sin respuesta se informan aparte e invalidan la corrida.
- El muestreador consulta la métrica ST-034 por segundo. Muestras ausentes,
  lentas o inferiores a 100 no acreditan concurrencia sostenida. Los tiempos
  de muestreo y retrasos se conservan. Un retraso >1 s invalida el resultado
  operativo del generador; es un criterio conservador de esta herramienta.
  La CPU porcentual del proceso usa como base un núcleo, y también se registra
  CPU/memoria del equipo. API, BD y generador comparten recursos: no representa
  una infraestructura de producción ni un generador independiente.
- Disponibilidad usa los sondeos existentes de ST-034 a `/health` y
  `/health/ready` cada segundo, durante cada corrida. Se publica la ventana,
  muestras correctas/fallidas y huecos estimados. No se extrapola continuidad
  entre sondeos ni se acredita el SLA mensual 99.5%. Los huecos entre perfiles
  quedan fuera de observación, sin anuncios de mantenimiento inventados.
- La API actual no expone el tablero ECL-15. Esta cobertura de RNF-008 queda
  pendiente: no se sustituyó por `/health` ni por `/vehiculos`.

Para pruebas breves del generador se pueden ajustar duraciones y repeticiones.
Los valores diferentes de 60/120/600/3 son diagnóstico y no acreditan la
metodología completa. Los directorios `smoke*` conservan esos diagnósticos.

## Evidencia y verificación

Por perfil: manifiesto, baseline, JSONL gzip de intentos y filas persistidas,
sondeos, muestras de concurrencia, exportaciones Prometheus, CSV/HTML Locust,
logs de API y resumen. La raíz de campaña contiene entorno, agregado y SHA256.
Los percentiles aproximados de Locust incluyen nombres separados por fase;
el resultado de aceptación es el cálculo exacto de `summary.json`.
`loadtest.audit` vuelve a calcular percentiles, poblaciones, franjas,
correlaciones y consistencia de los archivos exportados sin conexión a BD/API.
Un resultado consistente no implica que se hayan cumplido los umbrales.

```powershell
python -m pytest tests/unit/test_loadtest_analysis.py -q --cov=loadtest.analysis --cov-fail-under=80
python -m ruff check .
python -m ruff format --check .
```

CI ejecuta los casos negativos del analizador y conserva JUnit/cobertura.
La campaña de 40 minutos se ejecuta localmente, no se dispara por cada PR.
El código de salida 0 del comando significa que terminó y exportó evidencia;
**no significa que pasó los umbrales**: consultar `campaign.json` y el informe.
