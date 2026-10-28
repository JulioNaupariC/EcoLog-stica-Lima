# Ítem 7 — Coherencia y versionamiento documental

| Metadato | Valor |
|---|---|
| Proyecto | EcoLogística Lima |
| Sprint / consigna | Sprint 3, ítem 7 |
| Versión del informe | 1.0.0 |
| Fecha | 26/10/2026, America/Lima |
| Responsable | Frank Roy Yupanqui Acevedo — @FrankRoyYA |
| Rama | `docs/sprint3-item7-requisitos` |
| Estado | Preparado para revisión de Julio; no se atribuye aprobación de estas nuevas versiones |
| Base de trabajo | `main` en `72bffb6` |

## Alcance y fuentes

Se actualizan los requisitos y reglas afectados por US-013 y US-012, sin cambiar
los identificadores previos, el código o los documentos de arquitectura y datos.
El versionamiento es menor por ampliación compatible del catálogo; Git conserva
el contenido y nombre anteriores a los renombres con `git mv`.

- [US-013 / ECL-77 — validación](<validaciones/VALIDACION_US013.md>) y
  [contrato backend](../../../backend/README.md): temporal de 24 h, cambio
  obligatorio, política de contraseña, roles, sesiones y auditoría.
- [ECL-72 / ST-039 — BDD de incidencias](<../../02 Planificación/BDD/ECL-72-ST-039-incidencias.md>):
  registro propio, consulta de pendientes, catálogos, validación, cola e idempotencia.
- [ECL-82](https://continental-team-il84x39k.atlassian.net/browse/ECL-82):
  seguimiento de la jornada de la parada de I03, que sigue parcial.

## Versionamiento formal

| Documento anterior (conservado en Git) | Versión vigente | Cambio del Sprint 3 |
|---|---|---|
| `06. Requisitos funcionales V_1_0_0.md` | [RF V_1_1_0](<../../01 Inicio/06. Requisitos funcionales V_1_1_0.md>) | RF-013 y BDD por ruta; RF-012 refinado; catálogo, diagrama y trazabilidad actualizados. RF-001 explicita el cambio obligatorio pendiente y RF-007 la incidencia validada. |
| `07. Requisitos no funcionales V_1_1_0.md` | [RNF V_1_2_0](<../../01 Inicio/07. Requisitos no funcionales V_1_2_0.md>) | RNF-014 a RNF-017 con escenarios de seguridad medibles; RNF-002 requiere incidencia validada y RNF-006 precisa sincronización sin duplicados ni mezcla de cuentas. |
| `09. Reglas de negocio V_1_0_0.md` | [RN V_1_1_0](<../../01 Inicio/09. Reglas de negocio V_1_1_0.md>) | RN-016 a RN-018 para recuperación/cambio; RN-019 a RN-022 para incidencias; matriz RF/RNF y control de cambios. |

Cada versión incluye metadatos e historial con fecha y origen del cambio. Los
enlaces vigentes se actualizan al nuevo nombre, también los codificados con
`%20` y las rutas de fuentes de `AGENTS.md`. Los nombres antiguos de esta tabla
son referencias históricas, no enlaces activos.

## Coherencia y trazabilidad

| Concepto | Referencias | Comprobación documental |
|---|---|---|
| Temporal de 24 h, entrega una vez y hash | RF-013; RNF-014/RNF-017; RN-016 | Vencimiento en T + 24 h; se entrega una vez y se conserva solo hash. |
| Cambio obligatorio y uso único | RF-001/RF-013; RNF-015; RN-017 | Nueva distinta y mínimo 12 caracteres. La temporal deja de servir al completar el cambio; no se afirma que el primer login la consuma. |
| Mínimo privilegio, sesiones y auditoría | RF-013; RNF-016/RNF-017; RN-018 | Administrador restablece a otro usuario existente no inactivo; revoca sesiones. Al cambiar se conserva la actual y se revocan las demás, sin secretos en logs/errores/auditoría. |
| Incidencia pendiente y decisión operativa | RF-007/RF-012; RN-008/RN-010/RN-019 | Registrar no valida, reoptimiza ni bloquea automáticamente. La reoptimización corresponde a incidencias validadas y a paradas pendientes. |
| Reporte sin ruta y parada propia | RF-012; RN-002/RN-019; BDD I01/I03 | Se admite ausencia de ruta/parada; la propiedad se verifica y la jornada sigue pendiente en ECL-82. |
| Hora, errores e idempotencia | RF-012; RNF-006; RN-020/RN-021 | Tolerancia futura inclusiva de 5 min, sin antigüedad máxima; errores sin eco; misma operación y contenido no duplican. |
| Consulta operativa y privacidad | RF-012; RNF-003/RNF-004; RN-022 | Administrador/Operador consultan pendientes paginados; no se revoca la matriz global ni se exponen DNI, teléfono o licencia. |

## Límites y revisión

Este incremento documental no es una ejecución nueva de las pruebas de producto
ni una certificación de cobertura o seguridad. Las medidas de los RNF son
criterios de aceptación; las validaciones enlazadas conservan sus fechas y
límites reales. El borde temporal exacto de 24 h debe verificarse con reloj
controlado si la evidencia histórica citada no lo incluye.

No se modifican los documentos 11 (Base de datos) y 12 (Modelo C4), las
evidencias versionadas ni las reglas pendientes de ECL-79/ECL-80/ECL-81.
No se declara completada la jornada de I03 ni el flujo offline de interfaz
ECL-74/ECL-76. La aprobación de este PR por Julio sigue pendiente; no se
confunde con la aprobación anterior de la BDD ECL-72.

[↑ Índice del Sprint 3](README.md)

[← Volver al README principal](../../../README.md)
