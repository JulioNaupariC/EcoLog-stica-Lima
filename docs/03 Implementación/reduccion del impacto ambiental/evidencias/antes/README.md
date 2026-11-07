# ECL-108 — Línea base ANTES de Green IT

**Estado: preparación; mediciones pendientes.** Este registro no acredita una
línea base medida ni el cumplimiento de los criterios de aceptación. No hay
resultados Lighthouse, capturas ni muestras de API todavía.

## Trazabilidad y equipo

| Campo | Valor verificado |
|---|---|
| Ticket | [ECL-108](https://continental-team-il84x39k.atlassian.net/browse/ECL-108) |
| Fecha de preparación | 06/11/2026, America/Lima; no es fecha de medición |
| Commit fijo de `main` | `e09dcd80e32431018d4020bb02c89ffae7505705` |
| Rama de documentación | `docs/ECL-108-linea-base-green`, creada desde ese commit |
| Responsable | José Delgadillo, frontend y QA |
| Revisor previsto | @JulioNaupariC |
| Sistema | Microsoft Windows 11 Home Single Language, 10.0.26300 |
| CPU | Intel Core i9-14900HX, consultada con `Get-CimInstance Win32_Processor` |
| RAM física visible al sistema | 15,73 GiB, consultada con `Win32_ComputerSystem.TotalPhysicalMemory / 1GB` |
| Chrome instalado | 156.0.8078.80, según `chrome.exe` ProductVersion; verificar de nuevo al medir |
| Ejecución prevista | Docker Compose del commit base; frontend servido por Vite, puerto 5173 |
| Dataset | Pendiente: registrar cantidades y fecha de siembra de datos ficticios al medir |

## Comprobación inicial y bloqueo

`git pull --ff-only` respondió `Already up to date.`. La comprobación de Docker
falló porque no existe el pipe del motor Linux de Docker Desktop:

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

En esa comprobación tampoco existía `.env` en la raíz. Sin motor y configuración
local no se pudo levantar la aplicación con el protocolo indicado. Iniciar
Docker Desktop y preparar privadamente `.env` según el
[arranque local del proyecto](../../../../../README.md#arranque-local-con-docker-compose--ecl-29).
No publicar la configuración expandida de Compose, cookies ni contraseñas.

En una comprobación posterior el motor respondió con versión `29.9.2`.
Existe un proyecto Compose `ecologistica-lima-ecl29` detenido cuyo archivo de
configuración corresponde a otro clon (`Semana 10 - 2`), junto con su volumen
`ecologistica-lima-ecl29_postgis_data`. Para aislar esta campaña, usar
`docker compose -p ecologistica-lima-ecl108 --env-file .env ...` en los comandos
del arranque. No reutilizar, detener ni eliminar los recursos del otro clon.
La configuración privada de este clon sigue pendiente en esta preparación.

## Protocolo repetible para ECL-108 y ECL-115

### Preparar el entorno

1. Fijar el commit a medir y anotarlo completo. ECL-108 usa el commit anterior;
   ECL-115 debe registrar su propio commit DESPUÉS. No medir un árbol con cambios
   de aplicación sin registrar. Conservar el código ANTES mediante el historial:
   `git show e09dcd80e32431018d4020bb02c89ffae7505705:ruta/del/archivo`.
   Cada optimización posterior debe guardar su fragmento ANTES con ruta, líneas
   y commit para el informe 01, antes de modificar ese código.
2. Levantar la base, migraciones, API y frontend con las instrucciones del README
   principal y `compose.yaml`. Mantener Vite en desarrollo en ambas campañas;
   no sustituirlo por `build`/`preview`. Anotar versiones efectivas, puertos,
   revisión Alembic y cantidades de registros del dataset ficticio.
3. Usar una base de demostración preparada conforme al
   [procedimiento de datos demo](../../../../../backend/README.md#datos-de-demostración--sprint-2).
   No destruir ni recrear una base existente para esta medición. Las credenciales
   se proporcionan solo localmente. No medir páginas protegidas redirigidas a
   `/login` como si fueran la página solicitada.
4. Registrar CPU, RAM, Windows, Chrome y Lighthouse con sus versiones, fecha y
   hora de cada corrida en America/Lima. Cerrar otras cargas de trabajo, mantener
   el mismo equipo y alimentación y documentar cambios entre ANTES y DESPUÉS.

### Lighthouse y Network

1. Abrir Chrome en incógnito, sin extensiones. Usar el origen
   `http://127.0.0.1:5173`. En Lighthouse elegir **Navigation**, **Desktop** y
   categoría **Performance**. Registrar versión de Lighthouse, viewport y
   configuración de throttling; conservarlos en la segunda campaña.
2. Medir `/login` sin sesión; `/` y `/vehiculos` con sesión de Operador;
   `/conductor/itinerario` con la cuenta del conductor demo. Separar las ventanas
   o sesiones de los roles. Para páginas autenticadas, desactivar el borrado de
   almacenamiento que eliminaría la sesión; anotar esta configuración y usarla
   igual en ECL-115. Limpiar la caché HTTP antes de cada corrida.
3. Hacer **3 corridas por página**, una a la vez. Verificar la URL final y el rol
   antes y después de cada corrida; una redirección o error no es una medición
   válida de esa página. Exportar el JSON original de cada reporte Lighthouse.
4. En DevTools > Network, activar **Disable cache**, desactivar **Preserve log**,
   vaciar el listado y hacer una recarga completa por corrida. Registrar el total
   **Transferred**, su unidad y el número total de peticiones cuando la página
   termine su carga inicial. Registrar el intervalo observado si hay sondeo o
   conexiones persistentes. Capturar el resumen y la página, sin credenciales.
   El tamaño de recursos descomprimidos no sustituye al total transferido.
5. Guardar por corrida: Performance (0–100), FCP y LCP (ms), TBT (ms), CLS,
   bytes transferidos y peticiones. Calcular la **mediana de cada columna**:
   ordenar sus tres valores y tomar el central. No escoger una única corrida
   como representante de todas las métricas ni mezclar Lighthouse con Network
   sin identificar la fuente.
6. Usar nombres `login-01.lighthouse.json`, `inicio-operador-01.lighthouse.json`,
   `vehiculos-operador-01.lighthouse.json` e
   `itinerario-conductor-01.lighthouse.json`, repitiendo `02` y `03`.
   Guardar capturas con el mismo prefijo y sufijos `-lighthouse.png` y
   `-network.png`. No exportar HAR con cabeceras de sesión ni almacenamiento del
   navegador. Verificar ausencia de secretos antes de versionar cada artefacto.

### API: 20 peticiones por endpoint

1. Usar la API real `http://127.0.0.1:8000`, sesión de Operador por cookie y el
   mismo dataset que las páginas. Mantener la cookie solo en memoria; no pasarla
   como argumento de consola, escribirla en un script ni guardarla en archivos.
2. Ejecutar secuencialmente 20 GET de cada endpoint exacto:
   `/vehiculos`, `/conductores?page=1` y `/incidencias?page=1`.
   No añadir parámetros ni reemplazar los endpoints por mocks. No incluir
   el login en los tiempos. No añadir calentamientos sin documentarlos.
3. Para cada respuesta medir con reloj monótono desde antes del envío hasta
   terminar de leer el cuerpo. Registrar índice, estado HTTP, duración en ms,
   bytes del cuerpo recibido y `Content-Encoding`. Si hay compresión, distinguir
   bytes recibidos de bytes descomprimidos. Los bytes del cuerpo no incluyen
   cabeceras ni equivalen al total de Network de una página.
4. Guardar muestras sin cuerpos, cookies ni cabeceras sensibles en
   `api-vehiculos.csv`, `api-conductores.csv` y `api-incidencias.csv`.
   Informar media aritmética de los 20 tiempos y de los 20 tamaños, con mínimo y
   máximo de bytes si varían. Registrar errores; una campaña con respuestas
   fallidas no acredita 20 respuestas exitosas y debe repetirse tras resolver
   la causa, conservando el registro original.

## Tabla de medianas por página

**NM = no medido**. No equivale a cero ni a una estimación. El bloqueo inicial
es el entorno Compose sin motor disponible y sin `.env` de arranque.

| Página | Rol | Corridas válidas | Performance /100 | FCP ms | LCP ms | TBT ms | CLS | Transferido bytes | Peticiones | Estado |
|---|---|---:|---|---|---|---|---|---|---|---|
| `/login` | Sin sesión | 0/3 | NM | NM | NM | NM | NM | NM | NM | Pendiente por bloqueo inicial |
| `/` | Operador | 0/3 | NM | NM | NM | NM | NM | NM | NM | Pendiente por bloqueo inicial |
| `/vehiculos` | Operador | 0/3 | NM | NM | NM | NM | NM | NM | NM | Pendiente por bloqueo inicial |
| `/conductor/itinerario` | Conductor demo | 0/3 | NM | NM | NM | NM | NM | NM | NM | Pendiente por bloqueo inicial |

## Tabla de API

| Endpoint GET | Muestras válidas | Tiempo medio ms | Bytes medios del cuerpo | Estado |
|---|---:|---|---|---|
| `/vehiculos` | 0/20 | NM | NM | Pendiente por bloqueo inicial |
| `/conductores?page=1` | 0/20 | NM | NM | Pendiente por bloqueo inicial |
| `/incidencias?page=1` | 0/20 | NM | NM | Pendiente por bloqueo inicial |

## Pendientes para completar el ticket

- Obtener 12 JSON Lighthouse válidos y capturas Lighthouse/Network de las cuatro páginas.
- Registrar mediciones individuales, calcular las medianas y enlazar sus artefactos.
- Obtener las 60 muestras API autenticadas y sus medias reproducibles.
- Completar fecha de medición, versiones efectivas, dataset y configuración aplicada.
- Enlazar desde el índice `Sprint 04/README.md` cuando ECL-99 lo incorpore; ese
  índice y sus marcadores todavía no existen en el commit base. Las evidencias
  permanecen en esta carpeta, fuera de `Sprint 04/`.
- Publicar el PR para auditoría independiente y revisión de @JulioNaupariC.
  No marcar el ticket completo ni integrar sin aprobación humana y checks.

No editar artefactos que ya estén versionados en `evidencias/`. Cada ejecución
posterior debe crear un subdirectorio nuevo con fecha y hora, conservando este
registro inicial. Añadir al README principal el enlace al nuevo registro.

[← Volver al README principal](../../../../../README.md)
