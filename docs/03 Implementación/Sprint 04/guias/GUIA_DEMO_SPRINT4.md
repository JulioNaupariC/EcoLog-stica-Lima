# ECL-105 — Guía de la demostración del MVP (Sprint 4)

| Metadato | Valor |
|---|---|
| Ticket | [ECL-105](https://continental-team-il84x39k.atlassian.net/browse/ECL-105) |
| Autor | Antony Munive Rios (@ANTONY-MUNIVE), con apoyo de IA (Claude) |
| Fecha | 12/11/2026 |
| Duración objetivo | 8 a 10 minutos de demostración, más preguntas |
| Datos | `backend/scripts/seed_demo_mvp.py` (150 pedidos, 15 vehículos, 4 distritos), ver el [README del backend](<../../../../backend/README.md#datos-de-la-demostración-final-del-mvp--ecl-105>) |

Esta guía recorre el MVP de punta a punta:

1. Optimizar.
2. Ver las rutas en el mapa.
3. Registrar resultados y cerrar una ruta.
4. Consultar el dashboard de sostenibilidad.
5. Reportar una incidencia desde el móvil del conductor.
6. Validarla como Operador.

Cada paso tiene un tiempo **medido** y lo que se debe ver en pantalla.

## 1. Tiempos medidos

Los tiempos se midieron el 12/11/2026 con el build de producción del frontend,
la API local y PostgreSQL 16 con PostGIS, en un contenedor Linux de 2 CPU, sobre
una base nueva sembrada con `--fecha 2026-11-12`. El recorrido se automatizó con
Playwright, que mide el tiempo del sistema sin el tiempo de quien escribe o hace
clic. En la PC de la demo hay que repetirlo y anotar los tiempos reales en la
tabla de la sección 6.

| Paso | Qué se mide | Tiempo medido | Tiempo previsto en la exposición |
|---|---|---:|---:|
| 1 | Inicio de sesión del Operador | 0,5 s | 20 s |
| 2 | Optimización de 150 pedidos y 15 vehículos (`POST /optimizaciones`) | **20,1 s** | 1 min, incluye explicar mientras corre |
| 3 | Cargar el plan y el mapa de la fecha | 0,3 s | 1 min 30 s, recorrer rutas y la lista accesible |
| 4 | Registrar el resultado de las 3 paradas de una ruta | 1,6 s | 1 min |
| 5 | Cerrar la ruta (confirmación en la página) | 1,0 s | 20 s |
| 6 | Dashboard de sostenibilidad con las rutas cerradas | 0,1 s | 1 min 30 s |
| 7 | Inicio de sesión del Conductor (vista móvil) e itinerario | 0,6 s | 40 s |
| 8 | Reportar una incidencia | 2,7 s | 1 min |
| 9 | Validar la incidencia como Operador | 2,1 s | 40 s |
| | **Total** | | **≈ 8 min** |

Resultado de la corrida medida:
- La optimización terminó `COMPLETADA` con 10 rutas.
- La ruta más corta fue `MVP-010`, con 3 paradas.
- El dashboard mostró las rutas cerradas. El ahorro frente a la ruta secuencial
  salió 0 %, porque con 3 paradas el orden secuencial coincidió con el
  optimizado.

En una corrida anterior del mismo día se cerró una ruta de 5 paradas
(`DEMO-004`) y el ahorro de distancia fue de **34,01 %**. Por eso la guía pide
cerrar una ruta de 4 a 5 paradas.
- La incidencia quedó «validada».

Capturas: [mapa](../evidencias/ECL-105/03-mapa-rutas.png), [ruta cerrada](../evidencias/ECL-105/05-ruta-cerrada.png),
[dashboard](../evidencias/ECL-105/06-dashboard.png) y [validación](../evidencias/ECL-105/10-validacion.png).

## 2. Preparación (la noche anterior o 30 minutos antes)

1. Levantar la aplicación como de costumbre (ver la
   [guía de entorno local de ECL-90](GUIA_ENTORNO_LOCAL_ECL90.md)). Comprobar
   `http://127.0.0.1:8000/health` y la aplicación en `http://127.0.0.1:5173`.
2. Usar una base **exclusiva** cuyo nombre termine en `_demo`. Si ya se usó para
   otra demo, recrearla: `dropdb`/`createdb`, extensión PostGIS y
   `alembic upgrade head`.
3. Definir **en la consola, sin escribirlas en archivos**, las contraseñas de la
   demo (mínimo 12 caracteres) y sembrar para **el día de la demo**:

   ```powershell
   cd backend
   $env:DATABASE_URL = "postgresql+psycopg://USUARIO:CONTRASENA@127.0.0.1:5432/ecologistica_demo"
   foreach ($rol in "ADMINISTRADOR","OPERADOR","CONDUCTOR","ANALISTA","AUDITOR") {
     Set-Item "Env:SEED_DEMO_PASSWORD_$rol" (Read-Host "Contraseña demo $rol")
   }
   .venv/Scripts/python -m alembic upgrade head
   .venv/Scripts/python -m scripts.seed_demo_mvp --fecha 2026-11-13
   ```

   Debe terminar con «**150 pedidos PENDIENTE y 15 vehículos ACTIVO**».
   Requiere el arreglo del PR #142: sin él, con la fecha de hoy quedaban 157
   pedidos y el motor los rechaza. El script no está dentro de la imagen Docker
   del backend (solo copia `app/` y `alembic/`), así que se ejecuta con el
   entorno virtual local, apuntando al puerto de la base.
4. Abrir y dejar listas cuatro pestañas:
   - Swagger: `http://127.0.0.1:8000/docs`.
   - La aplicación como Operador.
   - Una ventana de incógnito con la vista móvil (F12, modo dispositivo) para el
     Conductor.
   - El tablero de Jira del sprint.
5. **Ensayar una vez** el recorrido completo. Luego, como el ensayo cierra una
   ruta, repetir los pasos 2 y 3 para empezar limpio. Si no da tiempo, el
   dashboard simplemente muestra una ruta cerrada más.

## 3. Guion de la demostración

> Al hablar, distinguir siempre **estimado** (plan, ETA, CO₂ de planificación) de
> **real** (hora de atención que registra el Operador).

### Paso 1–2 · Optimizar (US-006, RNF-001)

1. En Swagger, **POST `/login`** → *Try it out* →
   `{"email": "operador.demo@ecologistica.example", "password": "…"}` →
   *Execute*. Debe responder 200; la cookie de sesión queda en el navegador.
2. **POST `/optimizaciones`** → `{"fecha_operacion": "2026-11-13"}` → *Execute*.
   Mientras corre (unos 20 s), explicar:
   - El motor es OR-Tools VRPTW.
   - Respeta capacidad, ventanas, jornada y descansos.
   - RNF-001 pide 45 s o menos; el P95 medido en ECL-21 fue de 20,18 s en 30 corridas.
3. Respuesta esperada: `201` con `"estado": "COMPLETADA"`.

**Decirlo con honestidad:** la optimización todavía se solicita por la API
(Swagger). La pantalla de rutas consulta y opera el plan, pero no tiene un botón
para generarlo. Está registrado como pendiente en la Revisión del sprint.

### Paso 3 · Mapa y lista accesible (US-008)

1. En la aplicación, Operador → **Rutas y alertas** → fecha de la demo →
   **Actualizar optimizaciones** → elegir la optimización recién creada.
2. Mostrar la lista de rutas: vehículo, paradas, km y minutos, y si tienen o no
   conductor. Abrir una ruta y señalar:
   - El mapa Leaflet con OpenStreetMap.
   - El enlace «Ir a la lista accesible de paradas», que es la alternativa
     textual al mapa (WCAG).
   - Que las ETA son de planificación y no de tráfico en vivo.
3. Mencionar que hay 2 pedidos **no asignados con motivo**: uno excede la
   capacidad de toda la flota y otro tiene la ventana antes de la jornada. Son
   inviables a propósito y prueban el escenario E3 de US-006. Se ven en la
   respuesta del paso 2 o en `GET /optimizaciones/{id}`.

### Paso 4–5 · Registrar paradas y cerrar la ruta (ECL-119, ECL-120)

1. Elegir una ruta de **4 a 5 paradas**. Con 3 o menos, el orden secuencial suele
   coincidir con el optimizado y el ahorro sale 0 %.
2. Por cada parada: **Registrar resultado** → *Atendida* → **escribir una hora
   dentro de la ventana de esa parada**, que se ve en la lista → **Guardar**.
   Si se deja la hora actual propuesta, la parada cuenta como atendida **fuera
   de ventana** y el cumplimiento sale 0 %. Eso es correcto, pero no es lo que
   se quiere mostrar.
3. **Cerrar ruta** → **Confirmar cierre**. El estado pasa a *Cerrada*.

### Paso 6 · Dashboard de sostenibilidad (US-009, EN-008)

1. **Indicadores de sostenibilidad** → periodo que incluya el día de la demo →
   **Consultar periodo**.
2. Mostrar:
   - Rutas cerradas.
   - Distancia, CO₂, combustible y costo.
   - **Ahorro frente a la ruta secuencial**, calculado sobre las rutas cerradas.
   - Cumplimiento de ventanas.
   - La versión de parámetros usada (EN-008).
3. Explicar «Equivalente ambiental: No disponible». No se inventa una
   compensación sin un proyecto, un factor y una fuente registrados.

### Paso 7–9 · Incidencia del conductor y validación (US-012)

1. En la ventana móvil, iniciar sesión con `conductor.demo@ecologistica.example`
   → **Abrir mi itinerario** (5 paradas de `seed_demo` para hoy).
2. **Reportar incidencia** → Tipo *Tráfico* → Severidad *Media* → en Ubicación
   usar **Usar mi ubicación** (permitir la ubicación en el navegador) →
   observación sin datos personales → **Enviar incidencia**.
   **No elegir «Parada actual»:** las paradas de `seed_demo` vienen del modelo
   del Sprint 3 y no pertenecen a una ruta del Sprint 4, así que la API rechaza
   el reporte con 403 (regla I03 de ECL-82, «jornada de la parada»). Está
   registrado como pendiente.
3. En la ventana del Operador → **Incidencias pendientes** → la nueva incidencia
   aparece arriba → **Validar**. Debe aparecer «Incidencia validada».

## 4. Video de respaldo

Grabar el recorrido de la sección 3 una vez, con el build final, para tenerlo de
respaldo si falla la red o la PC del laboratorio:
- Herramienta: Xbox Game Bar (`Win + Alt + R`) u OBS.
- Duración: 8 a 10 minutos, a 1080p.
- Guardarlo fuera del repositorio (Drive del curso) y enlazarlo en ECL-105.
- No mostrar contraseñas en pantalla: escribirlas antes de empezar a grabar o
  pausar la grabación.

## 5. Si algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `POST /optimizaciones` responde 422 «La fecha tiene más de 150 pedidos PENDIENTE» | La fecha tiene pedidos de una siembra anterior | Recrear la base y sembrar de nuevo (sección 2) |
| `POST /optimizaciones` responde 401 | No se hizo `POST /login` en Swagger, o la sesión venció (60 min) | Repetir el login en Swagger |
| La página pide iniciar sesión al recargar | La sesión del Operador vive en memoria; al recargar se pierde | Navegar con el menú, sin recargar |
| No se puede registrar una parada como atendida | La hora es futura o anterior al día de la ruta | Usar una hora pasada del mismo día |
| La incidencia queda «Pendiente de envío» | Se eligió una parada del Sprint 3 (403) o no hay conexión | Enviar con «Usar mi ubicación» |
| El dashboard dice «Sin datos» | El periodo no incluye el día del cierre | Ampliar el periodo |

## 6. Registro en la PC de la demo (completar)

| Paso | Tiempo en la PC de la demo | Observación |
|---|---:|---|
| 2 · Optimización | | |
| 3 · Mapa | | |
| 4–5 · Paradas y cierre | | |
| 6 · Dashboard | | |
| 8–9 · Incidencia y validación | | |
| PC / sistema / navegador | | |

[Índice del Sprint 4](../README.md) · [← Volver al README principal](../../../../README.md)
