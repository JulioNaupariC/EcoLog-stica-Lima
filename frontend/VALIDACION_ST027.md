# Validación — ECL-53 / ST-027

Fecha: 09/10/2026, America/Lima.
Ticket: [ECL-53 · Implementar formulario de preferencias de entrega](https://continental-team-il84x39k.atlassian.net/browse/ECL-53).
Rama: `feat/ECL-53-st027-formulario-preferencias`.
Base Git: `63bd5ee` de `main`, con ST-026 integrado.
Trazabilidad: ECL-11 / US-005, RF-005, RN-002, RNF-004 y RNF-010.

## Entrega

Formulario protegido en `/clientes/preferencias`, accesible desde la navegación
de Administrador y Operador. Consulta y actualiza las preferencias de un Cliente
existente mediante la API ST-026, sin crear clientes ni cambiar el backend.

El identificador ingresado se valida antes de consultar. El formulario solo se
habilita después de recuperar el cliente. La respuesta debe corresponder al ID
solicitado; un cuerpo malformado o de otro cliente se rechaza. Al cambiar de
consulta se retiran los datos anteriores y las respuestas tardías no actualizan
una vista desmontada.

Se reutiliza el componente de campo de pedidos, extraído como `FormField`, y los
estilos existentes `order-form`, `submit-button`, `form-alert` y `field-error`.
La lógica se divide entre servicio HTTP, validación de dominio, formulario y
página. Los 27 casos existentes del formulario de pedidos siguen aprobados.

## Contrato y comportamiento

- GET/PATCH `/clientes/{cliente_id}/preferencias`, con cookie de sesión y
  `cache: no-store`; el servicio reutiliza `buildApiUrl`.
- `horario_preferido`: texto descriptivo de hasta 120 caracteres.
- `referencia` y `restriccion_acceso`: texto de hasta 255 caracteres.
- Se conserva exactamente el texto no vacío; no se recortan espacios ni se
  convierten horarios en fechas o ventanas de pedido.
- Casillas “Sin…” generan null explícito al guardar. Desmarcarlas recupera el
  texto en edición. Un texto vacío, compuesto solo por espacios, con NUL o
  demasiado largo se rechaza antes del envío. Se cuentan caracteres Unicode
  como en el backend, incluidos caracteres fuera del plano básico.
- PATCH incluye únicamente los campos modificados; no envía nombre ni datos
  ajenos al contrato. Guardar sin cambios muestra un aviso.
- La confirmación de éxito aparece después de recibir HTTP 200 válido; el
  formulario toma la respuesta persistida como base para ediciones posteriores.
- Guardado y consulta bloquean solicitudes duplicadas. Durante el guardado no
  se permite cambiar de cliente. Cancelar restaura los datos consultados y no
  hace una escritura.
- 401 limpia la identidad de App y vuelve a login. 403 retira datos y bloquea
  acciones. 404 permite corregir el cliente y consultar de nuevo.
- Los errores 422 se asocian solo a campos conocidos. Red, 5xx y respuestas
  inesperadas muestran mensajes locales comprensibles, sin reflejar SQL,
  cuerpos del servidor ni excepciones privadas.
- Un error de red al guardar puede ocurrir después del commit del servidor:
  se conserva la edición y se pide consultar para confirmar el resultado; no
  se anuncia éxito ni se hacen reintentos automáticos.
- Los datos permanecen solo en memoria de la vista; no se guardan preferencias
  ni credenciales en localStorage o IndexedDB.

## Resultados automatizados

Entorno: Windows, Node 22.18.0, npm 10.9.3 y dependencias del lock existente.
La suite usa Vitest/Testing Library y transporte simulado para casos unitarios.

| Verificación | Resultado |
|---|---|
| Pruebas frontend completas | 431 aprobadas, 25 archivos |
| Casos nuevos de ST-027 | 62 aprobados: servicio 21, dominio 10, página/formulario 24, App/RBAC 7 |
| Regresión del formulario de pedidos | 27 aprobados, incluidos en las 431 |
| Typecheck / lint / build | Aprobados |
| Cobertura global statements / branches / functions / lines | 93.70 % / 93.39 % / 94.28 % / 95.52 % |
| Servicio y dominio nuevos | 100 % en las cuatro métricas |
| FormField compartido | 100 % en las cuatro métricas |
| Formulario de preferencias | 100 % statements/lines/functions, 97.56 % branches |
| Página de preferencias | 100 % statements/lines/functions, 97.82 % branches |

JUnit de la ejecución local: [frontend-tests.xml](evidencias/ECL-53/frontend-tests.xml).
Los casos negativos aprobados verifican el rechazo y sus efectos esperados.
Los casos de App verifican permisos para los cinco roles y ausencia de
solicitudes cuando el usuario no tiene acceso.

## Navegador con API real y capturas

Se levantó un servidor temporal exclusivo PostgreSQL 16.15/PostGIS 3.6 en
`127.0.0.1:55453`, base `st027_preview`, con migraciones y datos sintéticos.
API en `127.0.0.1:8053`, Vite en `127.0.0.1:5153` y CORS limitado a ese origen.
Se usó Python 3.12.6 con `requirements-dev.lock`; no se reutilizó la base de
desarrollo. Los servicios y el cluster temporal se detuvieron al terminar.

El script `scripts/verify-preferences.mjs` ejecutó con Playwright 1.64.0:

| Navegador / identidad | Resultado |
|---|---|
| Chrome 155.0.8059.40 / Administrador | Aprobado |
| Firefox 157.0 / Operador | Aprobado |
| Conductor, login real en ambos navegadores | Enlace oculto, ruta denegada y API 403 |

En ambos navegadores se verificaron login, preferencias inicialmente nulas,
guardado real, recuperación por GET, preservación de espacios, validación de
longitud sin cambios en BD, limpieza parcial con null y otro cliente intacto.
Se revisó el formulario a 1280 px y 360 px, sin desbordamiento horizontal; se
comprobó Tab desde el horario hasta su casilla y no hubo errores JavaScript.
También se verificó un cliente inexistente mediante 404 real.

**Caso simulado:** únicamente PATCH 503 fue interceptado en navegador para
registrar el aviso y comprobar conservación de edición/datos. No acredita una
caída real de PostgreSQL. La revisión de teclado y ancho no constituye una
auditoría completa WCAG 2.1 AA ni una matriz de dispositivos físicos.

Las [16 capturas](evidencias/ECL-53/README.md) y
[resultados de navegador](evidencias/ECL-53/resultados.json) incluyen solo datos
sintéticos. No contienen contraseñas ni cookies.

## Límites y revisión

La selección usa UUID porque no existe endpoint de listado de clientes en la
API actual. No se inventa un catálogo ni se crean clientes desde el formulario.
Se mantiene el contrato de ST-026 documentado en
[VALIDACION_ST026.md](../backend/VALIDACION_ST026.md). El BDD ST-025 sigue marcado
como borrador y este trabajo no declara su aprobación.

Esta entrega gestiona preferencias. Proponerlas o copiarlas al crear un pedido,
interpretar horarios y la validación integral de ST-028 son trabajos separados;
no se modifica silenciosamente un pedido ni la planificación aprobada.

**Estado:** implementación, pruebas y capturas locales completadas. El PR,
GitHub Actions/SAST remotos y peer review quedan pendientes del push del usuario.
CI existente ejecuta automáticamente typecheck, lint, pruebas con cobertura y
build al abrir PR a `main`. No se atribuye una ejecución remota que aún no se
ha observado. Guía y texto de PR en [GUIA_JOSE_ST027.md](../GUIA_JOSE_ST027.md).
