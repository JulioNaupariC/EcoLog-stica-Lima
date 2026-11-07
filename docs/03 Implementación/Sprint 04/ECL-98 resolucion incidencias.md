# ECL-98 — Validar o descartar incidencias pendientes

Alcance: decisión desde Operación, RF-007 y RN-019. Estimación del ticket:
3 Story Points, según el [glosario ECL-99](CONVENCIONES_Y_GLOSARIO_ECL99.md).
No se inicia reoptimización ni se altera la ubicación de las incidencias.

## Contrato y persistencia

`PATCH /incidencias/{incidencia_id}` admite exclusivamente Administrador y
Operador. El actor se obtiene de la sesión; el cliente no puede fijarlo.

```json
{"accion": "DESCARTAR", "motivo": "Reporte revisado por Operación"}
```

`accion`: `VALIDAR` o `DESCARTAR`. `motivo`: cadena opcional, vacía por defecto,
máximo 300 puntos de código Unicode; `null` y propiedades extra se rechazan.
Respuesta 200: `incidencia_id`, `estado` (`VALIDADA`/`DESCARTADA`),
`resuelta_por` (UUID de usuario) y `resuelta_en` (fecha con zona horaria).
OpenAPI se genera desde los esquemas y el router; disponible en `/docs`
y `/openapi.json`.

| Caso | Respuesta |
|---|---|
| Sin sesión | 401 |
| Conductor, Analista o Auditor | 403 antes del servicio |
| UUID válido inexistente | 404 |
| Incidencia ya resuelta, incluso misma acción | 409 |
| Acción, motivo, UUID o campos extra inválidos | 422 sin eco del contenido |
| Fallo de almacenamiento o auditoría | 503 sin detalles internos |

La revisión `0014_resolver_incidencias`, posterior a `0013_incidencias`, añade
`resuelta_por` con FK a usuario, `resuelta_en`, `motivo` y el evento de auditoría
`INCIDENCIA_RESUELTA`. Los registros anteriores conservan campos nulos.
`SELECT … FOR UPDATE` serializa las decisiones: el segundo operador lee el
estado confirmado por el primero y recibe conflicto. La decisión y la
auditoría comparten transacción; un fallo revierte ambas. El detalle auditado
contiene solo estado y `con_motivo`, sin el texto libre, nombres o ubicación.
El downgrade se rechaza si hay resoluciones o sus eventos de auditoría.

Se verificó un solo head antes de crear la revisión. No se encontró en el clon
una reserva adicional de «Choques de merge». Antes de integrar, actualizar
con `origin/main` y comprobar `alembic heads`; si apareció una revisión paralela,
coordinar la numeración y el `down_revision` de esta migración.

## Interfaz y accesibilidad

`OperationIncidentsPage` ofrece Validar/Descartar y usa el componente `Dialog`
existente, con título, descripción, motivo etiquetado y contador Unicode.
El diálogo contiene el foco; Escape y Cancelar devuelven el foco al botón
inicial. Mientras se guarda se bloquean cierre y confirmaciones duplicadas.
Después de éxito o 409 se anuncia el resultado, se recarga el listado y se
lleva el foco al resultado. La paginación vuelve a una página válida si
desaparece la última. Los fallos de red/servidor conservan el diálogo y avisan
que se debe actualizar antes de reintentar; 401 usa el flujo de sesión existente.

## Evidencia automatizada

| Criterio | Prueba |
|---|---|
| Dorada: validar con actor, reloj y auditoría | `test_resolver_con_actor_autenticado`, `test_resolver_persiste_actor_reloj_motivo_y_auditoria_sin_texto`, `test_ECL98_resolver_http_persiste_y_sale_del_listado` |
| Feliz: descartar con motivo | Mismas pruebas parametrizadas para `DESCARTAR` |
| Infeliz: 409 y roles denegados | `test_resolver_segunda_decision_es_conflicto_sin_auditar`, `test_resolver_denegado_antes_del_servicio` |
| Borde: dos decisiones concurrentes | `test_ECL98_dos_operadores_una_decision_y_un_conflicto` (PostgreSQL real) y prueba de 409 en la pantalla |
| Atomicidad de auditoría | `test_ECL98_fallo_auditoria_revierte_estado` (PostgreSQL real) |
| Contrato y privacidad | `test_resolver_openapi`, `test_resolver_entrada_invalida_sanitizada`, `incidentResolution.test.ts` |
| Teclado, foco, límites y doble envío | Casos ECL-98 de `OperationIncidentsPage.test.tsx` |

La suite de integración de incidencias pasó: **77 pruebas**, incluidas las
cuatro de ECL-98 y los ciclos de migración, sobre PostgreSQL 16/PostGIS aislado
en `127.0.0.1:55498`, base exclusiva `ecl98_test`, con datos sintéticos.
Frontend: **771 pruebas**, 52 archivos; cobertura de líneas **97,75 %**,
ramas **93,07 %**, funciones **94,96 %**, sentencias **95,48 %**.
Typecheck y lint pasaron. La revisión con lector de pantalla real, auditoría
independiente, aprobación humana, CI y alertas de CodeQL quedan pendientes.

Backend completo: **1019 pruebas unitarias**, cobertura **94,10 %**, con Python
3.12.16 y las versiones de `requirements-dev.lock`. Ruff y formato pasaron.
El Python 3.14 del host no tenía OR-Tools; se usó un entorno temporal separado
para ejecutar la suite completa sin alterar dependencias del proyecto.
El build de producción del frontend pasó. Tras añadir la protección del
downgrade se repitieron las cuatro pruebas ECL-98 de integración, todas en verde.
`alembic heads` muestra solo `0014_resolver_incidencias`.

## Reproducción

Con Python 3.12 y `requirements-dev.lock` instalados, desde `backend/`:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest tests/unit --cov=app --cov-fail-under=80
python -m alembic heads
# TEST_DATABASE_URL debe señalar una base *_test exclusiva y vacía.
python -m pytest tests/integration/test_incidencias.py -q
```

Desde `frontend/`:

```powershell
npm.cmd ci
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run test:coverage
```

Desde la raíz: `python scripts/check_docs.py`.

Revisión solicitada al publicar: GiancarloSE (frontend), ANTONY-MUNIVE
(backend) y JulioNaupariC (documentación). El PR debe permanecer Draft hasta
la auditoría técnica independiente y la validación de los controles pendientes.

[Índice del Sprint 4](README.md)

[← Volver al README principal](../../../README.md)
