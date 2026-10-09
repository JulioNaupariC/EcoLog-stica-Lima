# Validación ECL-49 / ST-023 — Formulario y listado de conductores

## Trazabilidad y alcance

ECL-49 / ST-023 → ECL-9 / US-003 «Gestionar conductores y disponibilidad».
Rama de trabajo: `feat/ECL-49-formulario-conductores`.
Base: `main` en `192ae17`, con la API ECL-48/ST-022 integrada.

La pantalla consume la API existente para registrar, listar, consultar y actualizar
perfiles y disponibilidad. No incorpora eliminación, edición de cuentas o roles,
asignación de rutas ni lógica del optimizador.

## Implementación

- Ruta `/conductores` y navegación disponibles para ADMINISTRADOR y OPERADOR.
  Los demás roles reciben acceso denegado. La API conserva la autorización efectiva.
- Listado paginado de diez perfiles, estados de carga, lista vacía, error y reintento.
  El listado muestra nombre, estado, habilitación y disponibilidad; los datos personales
  se consultan al abrir el perfil autorizado.
- Alta con email y contraseña inicial. Edición exclusivamente de los campos del perfil,
  sin campos de credenciales.
- Validación de DNI de ocho dígitos, licencia, fecha válida, experiencia entera no negativa,
  teléfono E.164, longitudes y disponibilidad coherente. Se permite registrar licencia
  vencida y se muestra la habilitación devuelta por el backend.
- Disponibilidad introducida en hora de Lima (UTC−05:00). Retirarla envía ambos extremos
  como null. PATCH contiene únicamente cambios; editar otro campo conserva la precisión
  original de los timestamps del backend.
- Mensajes seguros para validación, duplicados, falta de permisos, sesión vencida y
  errores de red/servidor. Una sesión vencida conduce al login.
- Se impiden envíos repetidos mientras se guarda. Las contraseñas no se persisten en
  almacenamiento del navegador y se vacían al completar o fallar el envío.
- Etiquetas asociadas a controles, errores anunciados, foco visible y gestión del foco.
  Distribución de una columna en móvil y dos columnas en escritorio.

| Acción | API |
|---|---|
| Listar | GET /conductores?page=…&page_size=10 |
| Registrar | POST /conductores |
| Consultar perfil | GET /conductores/{conductor_id} |
| Actualizar perfil/disponibilidad | PATCH /conductores/{conductor_id} |

Los datos mostrados proceden de HTTP; no existe un listado ficticio incorporado a la
pantalla. Los registros de las capturas son datos sintéticos de una base local separada.

## Verificación automatizada

Verificación local del 9 de octubre de 2026:

- `npm run typecheck`: aprobado.
- `npm run lint`: aprobado.
- `npm run test:coverage`: 369 pruebas aprobadas en 21 archivos.
- `npm run build`: aprobado.

| Archivo / ámbito | Sentencias | Ramas | Funciones | Líneas |
|---|---:|---:|---:|---:|
| Frontend completo | 92.50% | 92.51% | 93.45% | 94.74% |
| DriverForm.tsx | 98.33% | 100% | 94.11% | 100% |
| DriversPage.tsx | 97.59% | 89.53% | 100% | 100% |
| driverForm.ts | 100% | 100% | 100% | 100% |
| drivers.ts | 100% | 100% | 100% | 100% |

Las pruebas verifican permisos de navegación, expiración de sesión, validación,
privacidad de resúmenes, errores HTTP, paginación, registro, edición parcial,
disponibilidad y descarte de respuestas tardías.

En dos pruebas existentes se espera el resultado asíncrono antes de comprobarlo:
el aviso del itinerario en App.test.tsx y el foco del error en LoginPage.test.tsx.
Se mantienen las mismas aserciones y no se modifica su comportamiento productivo.

## Verificación funcional en navegadores

Resultado registrado en [resultados.json](evidencias/ECL-49/resultados.json),
con fecha UTC `2026-10-09T07:20:18.898Z`.

| Navegador | Versión | Cuenta autorizada | Resultado |
|---|---|---|---|
| Chrome | 154.0.8037.98 | ADMINISTRADOR | Aprobado |
| Firefox | 157.0 | OPERADOR | Aprobado |

En ambos navegadores se comprobó login real, alta HTTP 201, rechazo de DNI duplicado,
consulta, PATCH de teléfono, conservación de timestamps no editados y retiro de
disponibilidad. Se verificaron el acceso denegado del rol CONDUCTOR y el rechazo HTTP
403 del listado con esa sesión.

Se capturaron escritorio de 1280 px y móvil de 360 px, sin desbordamiento horizontal
en los estados comprobados y sin errores de página. Hay 24 capturas en
[evidencias/ECL-49](evidencias/ECL-49/README.md).

El estado de carga utiliza un retraso controlado de respuesta. El error/reintento
utiliza un GET 503 simulado en el navegador, seguido de una consulta real satisfactoria.
El resto de las operaciones descritas consume el backend local real.

### Reproducción local

Con frontend en http://127.0.0.1:5173 y backend en http://127.0.0.1:8000:

1. Preparar una base de desarrollo y cuentas sintéticas ADMINISTRADOR, OPERADOR y CONDUCTOR.
2. Guardar sus credenciales únicamente en el archivo privado ignorado
   `.env.ecl49-preview`, en la raíz, con las claves
   `ECL49_ADMIN_EMAIL`, `ECL49_ADMIN_PASSWORD`,
   `ECL49_OPERATOR_EMAIL`, `ECL49_OPERATOR_PASSWORD`,
   `ECL49_DRIVER_EMAIL` y `ECL49_DRIVER_PASSWORD`.
3. Disponer de Playwright y sus navegadores fuera de las dependencias publicadas del
   proyecto. `ECL49_PLAYWRIGHT_MODULE` permite indicar su módulo y
   `PLAYWRIGHT_BROWSERS_PATH` su directorio de navegadores.
4. Ejecutar desde frontend: `node scripts/verify-drivers.mjs`.

El script crea registros sintéticos persistentes: usar una base de prueba separada,
con un listado pequeño, para reproducir el recorrido. No elimina registros existentes.

## Estado y límites

El incremento está implementado y verificado localmente. El commit, el Pull Request,
la ejecución de CI y la revisión del equipo corresponden al siguiente paso de entrega;
este documento no afirma que ya se hayan realizado.

Las capturas proceden de navegadores automatizados en modo headless. No constituyen
una auditoría WCAG completa ni pruebas de dispositivos físicos. La validación de gestión
de conductores de ST-024 sigue siendo trabajo del ticket correspondiente.
