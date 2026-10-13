# Validación — ECL-48 / ST-022

**Trazabilidad:** ECL-48 / ST-022 → ECL-9 / US-003; RF-003, RN-002 y RNF-004.
**Rama:** `feat/ECL-48-api-conductores`.
**Fecha:** 09/10/2026, America/Lima.

## Alcance y decisiones

Registrar, consultar y actualizar conductores y su disponibilidad sobre el modelo
y la migración existentes de ST-020. No se añade formulario, eliminación,
optimizador, modificación de reglas base ni nuevas migraciones.

El usuario confirmó en esta sesión:
- Alta con email y contraseña inicial; cuenta CONDUCTOR y perfil en una transacción.
- Guardar licencia vencida, devolviendo `habilitado_asignacion: false`.

ST-021 conserva propuestas pendientes de ratificación del equipo. Este contrato
documenta las decisiones de implementación de ECL-48; no cambia ese documento
ni declara aprobaciones de Jira que no se hayan comprobado.

## Contrato HTTP

Todos los endpoints requieren la cookie HttpOnly del login existente.

| Operación | Acceso | Respuesta |
|---|---|---|
| `POST /conductores` | Administrador / Operador | 201, resumen sin DNI, licencia ni teléfono |
| `GET /conductores?page=1&page_size=20` | Administrador / Operador | 200, items y metadatos page/page_size/total |
| `GET /conductores/{conductor_id}` | Administrador / Operador | 200, perfil para mantenimiento |
| `GET /conductores/{conductor_id}` | Conductor propietario | 200, resumen sin DNI, licencia, teléfono ni punto de partida |
| `PATCH /conductores/{conductor_id}` | Administrador / Operador | 200, perfil actualizado |

Conductor no tiene listado ni escritura. Analista y Auditor no acceden a este
contrato individual: sus proyecciones agregadas/anonimizadas requieren endpoints
separados. Se reutiliza la matriz RBAC, sin ampliarla. La consulta por ID verifica
la propiedad real del registro y registra la decisión mediante la auditoría
existente; no confía en un propietario enviado por el cliente.

Errores: 401 sin sesión válida, 403 sin permiso/propiedad, 404 sin registro,
409 DNI o cuenta duplicados, 422 entrada o perfil resultante inválidos,
503 servicio no disponible. Errores de validación no devuelven input, cuerpo
original, contraseña, DNI, teléfono, SQL ni detalles de excepciones.

OpenAPI/Swagger incorpora automáticamente esquemas y rutas.
CORS permite PATCH para que ST-023 pueda actualizar desde el origen autorizado;
no se amplían orígenes ni permisos de usuario.

## Datos y validaciones

Alta: `nombre`, `dni`, `licencia_numero`, `licencia_vigente_hasta`,
`experiencia_anios`, `telefono`, `punto_partida`,
`disponible_desde`, `disponible_hasta`, `email` y `password`.

- DNI: texto de exactamente ocho dígitos ASCII; conserva ceros iniciales.
  Unicidad garantizada por PostgreSQL, también ante escrituras concurrentes.
- Nombre 1–160, licencia 1–20 y punto de partida 1–255 caracteres, tras recortar
  espacios exteriores. Licencia normalizada a mayúsculas; fecha calendario válida.
  No se verifica la licencia en un registro externo.
- Teléfono E.164: + y entre ocho y quince dígitos, sin inferir país.
- Experiencia: entero no negativo compatible con Integer de PostgreSQL;
  no acepta booleanos ni fracciones. El máximo técnico no es un límite de negocio.
- Email con formato básico y hasta 255 caracteres, sin espacios exteriores.
  Se conserva su capitalización para mantener el contrato de login existente.
- Contraseña de solo escritura, no vacía, hasta 1024 caracteres. No se recorta
  ni acepta un hash del cliente. Usa el adaptador Argon2id existente.
- Alta exige un intervalo completo. Timestamps con zona explícita, normalizados
  a UTC; final posterior al inicio. No se limita la disponibilidad a ocho horas:
  RN-005 restringe conducción de una ruta, no la franja disponible.
- PATCH exige al menos un campo; rechaza campos extra y null en datos del perfil.
  Para cambiar disponibilidad deben enviarse ambos extremos. Ambos null permiten
  retirarla; un intervalo parcial o invertido se rechaza antes de mutar el ORM.
- PATCH no cambia email, contraseña, usuario asociado, rol ni estado.
- `habilitado_asignacion` es elegibilidad básica al consultar: usuario CONDUCTOR
  activo, perfil activo, licencia vigente en la fecha local de Lima e intervalo
  completo todavía no terminado. Una licencia es vigente durante su fecha final.
  No acredita factibilidad ni asigna rutas: el optimizador debe verificar licencia
  para la jornada propuesta, ventanas, conducción y descansos.

La cuenta se crea con un UUID independiente del actor. Un fallo de alta del perfil
revierte también la cuenta. PATCH bloquea la fila durante la transacción,
valida el resultado completo y revierte cambios si ocurre un conflicto.

## Evidencia automatizada local

Entorno: Python 3.13.3, dependencias de requirements-dev.lock, PostgreSQL 16 /
PostGIS 3.5 en contenedor exclusivo de ECL-48, puerto local 55448 y base vacía
separada terminada en _test. No se reutilizó la base de desarrollo.

| Comprobación | Resultado |
|---|---|
| Regresión unitaria completa | 407 pruebas aprobadas |
| Cobertura unitaria global | 92.03 % |
| Cobertura de API/repositorio/esquemas/servicio de ECL-48 | 98.13 % |
| Regresión de integración | 102 aprobadas; 1 smoke de PostGIS omitido por ausencia de DATABASE_URL en esa ejecución |
| Smoke PostgreSQL/PostGIS ejecutado por separado con DATABASE_URL aislada | 1 aprobado |
| Ruff check | Aprobado |
| Ruff format --check | Aprobado |

La prueba nueva `tests/integration/test_conductor_http_e2e.py` utiliza sesiones
HTTP reales, hashing real y PostgreSQL. Comprueba:
- Administrador y Operador pueden registrar/consultar/actualizar.
- Nueva cuenta permite login CONDUCTOR y corresponde al perfil creado.
- DNI duplicado después de insertar la cuenta revierte ambos registros.
- Email duplicado no crea perfiles y PATCH con DNI duplicado conserva el original.
- Licencia vencida y disponibilidad retirada muestran no asignable.
- Dos páginas tienen total correcto, orden estable y registros distintos.
- Conductor recibe sólo su resumen; otro perfil devuelve 403.
- Auditor y Analista no reciben datos individuales ni permisos de escritura.
- Entradas inválidas no llegan a persistencia ni exponen la contraseña.
- No existe eliminación de conductores en este contrato.

Las pruebas eliminan sólo la auditoría sintética en la base previamente validada
como aislada para permitir el downgrade protegido existente. Esa limpieza
pertenece al test, no a un endpoint de la aplicación.

## Reproducción

Desde backend/, con entorno virtual y dependencias fijadas:
```powershell
python -m pytest tests/unit --cov=app --cov-report=term --cov-fail-under=80
python -m ruff check .
python -m ruff format --check .
```

Para integración, configurar privadamente TEST_DATABASE_URL hacia PostgreSQL
con PostGIS y esquema público vacío, distinto de desarrollo, nombre terminado
en _test. Los fixtures verifican esos requisitos antes de operar.
```powershell
python -m pytest tests/integration -q
```

No publicar variables, cookies ni archivos .env. La configuración privada usada
en esta sesión quedó fuera de los archivos del incremento.

## Pendientes de entrega

Giancarlo ejecutará add/commit/push y abrirá el PR de ECL-48.
Faltan controles de CI/CodeQL sobre el commit publicado y revisión humana.
No se declara cerrado ECL-48 ni US-003 sólo por esta validación local.
ST-023 puede consumir este contrato para su formulario/listado en su propia rama.
