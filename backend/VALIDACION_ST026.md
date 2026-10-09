# Validación ECL-52 / ST-026 — API de preferencias de entrega

## Trazabilidad y alcance

ECL-52 / ST-026 → ECL-11 / US-005; RF-005 y RN-006.
Rama: `feat/ECL-52-api-preferencias-entrega`.
Base Git: `68ec1fb`.

Se reutilizan las columnas existentes de Cliente, creadas por la migración 0006:
horario_preferido VARCHAR(120), referencia VARCHAR(255) y restriccion_acceso VARCHAR(255),
todas nullable. No se requieren nuevas tablas ni migraciones.

La API consulta e inicializa/actualiza preferencias de clientes ya existentes.
No crea clientes, no cambia su nombre, no elimina clientes, no implementa formulario
ni modifica automáticamente los pedidos.

El documento [ST-025](<../docs/02 Planificación/BDD/ECL-51-ST-025-preferencias-entrega.md>)
está marcado como BORRADOR. La implementación adopta su contrato candidato y la
semántica omitido/null/vacío como decisiones de este incremento, sujetas a la revisión
del equipo; no se atribuye aprobación del borrador ni se modifica ese documento.

## Contrato HTTP

| Método y ruta | Uso | Permiso |
|---|---|---|
| GET /clientes/{cliente_id}/preferencias | Consultar preferencias para preparar un pedido | CLIENTES_CONSULTAR |
| PATCH /clientes/{cliente_id}/preferencias | Inicializar o modificar campos de preferencias | CLIENTES_ACTUALIZAR |

Administrador y Operador activos tienen acceso mediante la matriz RBAC existente.
Conductor, Analista y Auditor no acceden a esta proyección individual: faltan los
contextos de asignación/proyección restringida o el permiso de actualización.
No se amplían sus permisos globales. Se conserva la auditoría del acceso existente.

Respuesta HTTP 200:

```json
{
  "cliente_id": "00000000-0000-4000-8000-000000000001",
  "horario_preferido": "Mañana (preferido)",
  "referencia": "Puerta junto al parque",
  "restriccion_acceso": "Ingreso por puerta lateral"
}
```

El UUID del ejemplo es sintético; no identifica un cliente aprovisionado.
Las respuestas sólo incluyen el ID y las tres preferencias, sin nombre u otros datos.
Las respuestas satisfactorias incluyen Cache-Control: no-store.

| Estado | Significado |
|---|---|
| 200 | Consulta o actualización satisfactoria |
| 401 | Falta sesión, con el servicio de autenticación disponible |
| 403 | Identidad sin autorización para esta operación/proyección |
| 404 | Cliente inexistente, después de comprobar permisos |
| 422 | UUID, JSON o campos inválidos |
| 503 | Autenticación, auditoría o almacenamiento no disponibles |

OpenAPI/Swagger registra ambas operaciones, sus modelos y respuestas de error.
Las validaciones HTTP devuelven ubicación/tipo y un mensaje seguro, sin reflejar
valores de entrada, SQL, credenciales o detalles de excepciones.

## Validación y persistencia

- PATCH debe incluir al menos uno de los tres campos.
- Campo omitido conserva su valor; null limpia sólo el campo incluido.
- Se rechazan campos ajenos, incluido cliente_id en el cuerpo, nombre o credenciales.
  El recurso objetivo se obtiene exclusivamente del UUID de la ruta.
- Valores no nulos deben ser cadenas: no se convierten números, booleanos ni colecciones.
- Se respetan los límites de almacenamiento 120/255/255 caracteres.
- Se rechazan texto vacío, sólo espacios y caracteres NUL incompatibles con PostgreSQL.
- Se preservan espacios alrededor de textos no vacíos; no hay recorte silencioso.
- horario_preferido es texto contextual, no una fecha/ventana de pedido.
  No se impone un formato horario nuevo.
- Se verifica existencia del Cliente. La actualización bloquea su fila FOR UPDATE,
  cambia exclusivamente los campos incluidos y confirma la transacción al terminar.
- Un error de flush o commit produce rollback y una respuesta segura de indisponibilidad.
- No se crea una asociación nueva ni se cambia la FK cliente_id de pedidos existentes.

La API no repara automáticamente valores históricos introducidos por otros mecanismos.

## Recuperación durante el registro de pedidos

El consumidor debe:

1. Seleccionar el cliente existente.
2. Consultar GET /clientes/{cliente_id}/preferencias.
3. Mostrar horario y restricción como información contextual.
4. Si el usuario elige usar la referencia, copiarla explícitamente al campo referencia
   del nuevo pedido y enviarla junto con el mismo cliente_id a POST /pedidos.
5. Enviar una ventana explícita válida del pedido; nunca convertir automáticamente
   el horario_preferido textual.

El endpoint proporciona el contrato backend para ese flujo; su interfaz pertenece
a ECL-53/ST-027. POST /pedidos mantiene su validación RN-006 y no hereda preferencias
implícitamente. Cambiar preferencias después no cambia pedidos ya registrados.

La prueba HTTP integrada consulta la preferencia, crea un pedido con esa referencia
seleccionada, verifica persistencia y comprueba que Cliente y Pedido permanecen
independientes. También comprueba que otro Cliente conserva sus preferencias.

## Resultados locales — 9 de octubre de 2026

- `python -m ruff check .`: aprobado.
- `python -m ruff format --check .`: aprobado.
- Suite unitaria completa: 506 pruebas aprobadas.
- Cobertura global de sentencias: 93.22%.
- Módulos nuevos: API aproximadamente 98%; repositorio, servicio y schemas 100%
  en la medición unitaria. El incremento supera el 80% requerido.
- Suite de integración completa: 110 pruebas aprobadas, incluidas seis nuevas pruebas
  HTTP de preferencias con PostgreSQL 16/PostGIS.
- Entorno local Python 3.13.3; CI usa Python 3.12.10 según su configuración existente.
  CI y revisión del equipo siguen pendientes del Pull Request.

Las seis pruebas de integración nuevas cubren Administrador y Operador, los tres roles
denegados y una transacción que falla después de flush, demostrando rollback real.
Comprueban también ausencia de sesión, campos inválidos sin persistencia parcial,
404, consulta posterior, conservación de omitidos, limpieza con null y uso en pedidos.

Se utilizó una base nueva y aislada, ecologistica_ecl52_preferences_test, en el contenedor
PostGIS de desarrollo existente. No se modificó la base preview ni se borraron otras bases
o volúmenes. La limpieza de migraciones y auditoría se limita a esa base descartable
mediante los fixtures de seguridad existentes.

Hay avisos de deprecación de Starlette/httpx/AnyIO existentes en la suite.
No se actualizaron dependencias de otros tickets.

## Archivos y reproducción

Producción:
- app/api/preferencias.py
- app/schemas/preferencias.py
- app/repositories/preferencias.py
- app/services/preferencias.py
- app/main.py (registro del router)

Pruebas:
- tests/unit/test_preferencias_api.py
- tests/unit/test_preferencias_schemas.py
- tests/unit/test_preferencias_service.py
- tests/integration/test_preferencias_http_e2e.py

Desde backend, con sus dependencias de desarrollo instaladas:

```powershell
python -m pytest tests/unit -q --cov=app --cov-report=term-missing --cov-fail-under=80
python -m pytest tests/integration -q
python -m ruff check .
python -m ruff format --check .
```

Integración requiere TEST_DATABASE_URL privada, explícita, terminada en _test,
separada de desarrollo y con el esquema público vacío antes de iniciar los fixtures.
Nunca publicar credenciales ni ejecutar migraciones destructivas sobre una base compartida.

## Estado de entrega

Backend implementado y verificado localmente. El usuario realiza commit, push y PR.
No se declara CI, revisión o aprobación ya realizadas.
El formulario de preferencias (ST-027) y la validación posterior del equipo (ST-028)
mantienen su alcance independiente.
