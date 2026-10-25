# Sprint 2 — Documentación técnica de implementación

Esta carpeta reúne la documentación técnica del Sprint 2 (08/10/2026–23/10/2026):
validaciones de subtareas, informes de rendimiento y guías de integración.
Los entregables de la rúbrica (informe de estado, impedimentos, revisión y
retrospectiva) están un nivel más arriba, en
[`docs/03 Implementación/`](<../>).

Las evidencias ejecutables (JSON, XML, registros y capturas) permanecen en
[`backend/evidencias/`](<../../../backend/evidencias/>) y
[`frontend/evidencias/`](<../../../frontend/evidencias/>), porque los scripts
`verify-*.mjs` y `verify_metrics.py` escriben en esas rutas.

## Índice

### Validaciones

| Documento | Subtarea Jira | Tema |
|---|---|---|
| [VALIDACION_ST022.md](<validaciones/VALIDACION_ST022.md>) | ECL-48 / ST-022 | API de conductores |
| [VALIDACION_ST023.md](<validaciones/VALIDACION_ST023.md>) | ECL-49 / ST-023 | Formulario y listado de conductores |
| [VALIDACION_ST024.md](<validaciones/VALIDACION_ST024.md>) | ECL-50 / ST-024 | Pruebas de conductores |
| [VALIDACION_ST026.md](<validaciones/VALIDACION_ST026.md>) | ECL-52 / ST-026 | API de preferencias de entrega |
| [VALIDACION_ST027.md](<validaciones/VALIDACION_ST027.md>) | ECL-53 / ST-027 | Interfaz de preferencias de entrega |
| [VALIDACION_ST028.md](<validaciones/VALIDACION_ST028.md>) | ECL-54 / ST-028 | Matriz de validación de preferencias y clientes |
| [VALIDACION_ST030.md](<validaciones/VALIDACION_ST030.md>) | ECL-56 / ST-030 | Interfaz móvil del conductor |
| [VALIDACION_ST031.md](<validaciones/VALIDACION_ST031.md>) | ECL-57 / ST-031 | Responsive y accesibilidad |
| [VALIDACION_ST032.md](<validaciones/VALIDACION_ST032.md>) | ECL-58 / ST-032 | Almacenamiento offline y sincronización |
| [VALIDACION_ST034.md](<validaciones/VALIDACION_ST034.md>) | ECL-60 / ST-034 | Métricas de API y base de datos |
| [VALIDACION_ST035.md](<validaciones/VALIDACION_ST035.md>) | ECL-61 / ST-035 | Carga y disponibilidad |
| [VALIDACION_ST038.md](<validaciones/VALIDACION_ST038.md>) | ECL-64 / ST-038 | Optimización de consultas |

### Informes

| Documento | Subtarea Jira | Tema |
|---|---|---|
| [plan-pruebas-capacidad.md](<informes/plan-pruebas-capacidad.md>) | ECL-59 / ST-033 | Plan de pruebas de capacidad y disponibilidad |
| [INFORME_ST036.md](<informes/INFORME_ST036.md>) | ECL-62 / ST-036 | Resultados, SLA y operación |
| [INFORME_ST037.md](<informes/INFORME_ST037.md>) | ECL-63 / ST-037 | Medición inicial de payload y consultas críticas |

### Diseño

| Documento | Subtarea Jira | Tema |
|---|---|---|
| [README de ST-029](<diseno/ST-029/README.md>) | ECL-55 / ST-029 | Diseño móvil del conductor (Giancarlo Marcio Soto Escobar) |
| [guia-visual.md](<diseno/ST-029/guia-visual.md>) | ECL-55 / ST-029 | Paleta, tipografía, componentes y estados |
| [Evidencias visuales](<diseno/ST-029/evidencias/README.md>) | ECL-55 / ST-029 | Vistas PNG de los frames de Figma |

La guía se integró desde la rama `docs/ECL-55-diseno-movil-conductor` en el
cierre del Sprint 2 (25/10/2026), conservando los commits de su autor. La
implementación del rediseño (PR #53) siguió sus decisiones de diseño móvil.

### Guías de integración

| Documento | Subtareas |
|---|---|
| [GUIA_JOSE_ST024.md](<guias/GUIA_JOSE_ST024.md>) | ST-024 |
| [GUIA_JOSE_ST027.md](<guias/GUIA_JOSE_ST027.md>) | ST-027 |
| [GUIA_JOSE_ST031_ST032.md](<guias/GUIA_JOSE_ST031_ST032.md>) | ST-031 y ST-032 |
| [GUIA_JOSE_ST035.md](<guias/GUIA_JOSE_ST035.md>) | ST-035 |

Las guías conservan los comandos `git add` con las rutas vigentes cuando se
escribieron; son un registro histórico de cómo se integró cada subtarea.

## Mapa de reubicación

El 25/10/2026, en el cierre del Sprint 2, la carpeta `Sprint 2` se renombró a
`Sprint 02` para alinearla con la carpeta `Sprint 03` que exige la consigna del
Sprint 3, y la guía ST-029 pasó de `frontend/diseno/ST-029/` a
`docs/03 Implementación/Sprint 02/diseno/ST-029/`. Las rutas de la tabla ya
reflejan la ubicación actual.

Los archivos se movieron con `git mv`; `git log --follow <ruta nueva>` recorre
su historial completo.

| Ruta anterior | Ruta nueva | Commit |
|---|---|---|
| `backend/VALIDACION_ST022.md` | `docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST022.md` | `15c083e` |
| `frontend/VALIDACION_ST023.md` | `docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST023.md` | `15c083e` |
| `backend/VALIDACION_ST024.md` | `docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST024.md` | `15c083e` |
| `backend/VALIDACION_ST026.md` | `docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST026.md` | `15c083e` |
| `frontend/VALIDACION_ST027.md` | `docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST027.md` | `15c083e` |
| `backend/VALIDACION_ST028.md` | `docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST028.md` | `15c083e` |
| `frontend/VALIDACION_ST030.md` | `docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST030.md` | `15c083e` |
| `frontend/VALIDACION_ST031.md` | `docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST031.md` | `15c083e` |
| `frontend/VALIDACION_ST032.md` | `docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST032.md` | `15c083e` |
| `backend/VALIDACION_ST034.md` | `docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST034.md` | `15c083e` |
| `backend/VALIDACION_ST035.md` | `docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST035.md` | `15c083e` |
| `backend/VALIDACION_ST038.md` | `docs/03 Implementación/Sprint 02/validaciones/VALIDACION_ST038.md` | `15c083e` |
| `backend/INFORME_ST036.md` | `docs/03 Implementación/Sprint 02/informes/INFORME_ST036.md` | `15c083e` |
| `backend/INFORME_ST037.md` | `docs/03 Implementación/Sprint 02/informes/INFORME_ST037.md` | `15c083e` |
| `docs/sprint-2/plan-pruebas-capacidad.md` | `docs/03 Implementación/Sprint 02/informes/plan-pruebas-capacidad.md` | `15c083e` |
| `GUIA_JOSE_ST024.md` | `docs/03 Implementación/Sprint 02/guias/GUIA_JOSE_ST024.md` | `15c083e` |
| `GUIA_JOSE_ST027.md` | `docs/03 Implementación/Sprint 02/guias/GUIA_JOSE_ST027.md` | `15c083e` |
| `GUIA_JOSE_ST031_ST032.md` | `docs/03 Implementación/Sprint 02/guias/GUIA_JOSE_ST031_ST032.md` | `15c083e` |
| `GUIA_JOSE_ST035.md` | `docs/03 Implementación/Sprint 02/guias/GUIA_JOSE_ST035.md` | `15c083e` |
| `docs/03 Contribucion/01. Politica de pull requests V_1_0_0.md` | `docs/04 Contribución/01. Politica de pull requests V_1_0_0.md` | `e6435b5` |

### Auditoría de registros de hashes históricos

Dos registros de evidencia citan rutas anteriores. No se modifican: son
registros fechados. El hash corresponde al contenido del archivo en el commit
indicado, con finales de línea CRLF (copia de trabajo en Windows):

| Registro | Ruta citada | Commit cuyo contenido coincide |
|---|---|---|
| [`backend/evidencias/ECL-54/resultados.json`](<../../../backend/evidencias/ECL-54/resultados.json>) | `backend/VALIDACION_ST028.md` | `df55c72` |
| [`backend/evidencias/ECL-64/verificacion.json`](<../../../backend/evidencias/ECL-64/verificacion.json>) | `backend/VALIDACION_ST038.md` | `87f7821` |

Para comprobarlo:

```bash
git show df55c72:backend/VALIDACION_ST028.md \
  | python -c "import sys,hashlib;print(hashlib.sha256(sys.stdin.buffer.read().replace(b'\n',b'\r\n')).hexdigest())"
```

El contenido actual difiere de esos hashes porque, tras la reubicación, se
actualizaron los enlaces relativos y se añadieron los enlaces de navegación.

[← Volver al README principal](<../../../README.md>)
