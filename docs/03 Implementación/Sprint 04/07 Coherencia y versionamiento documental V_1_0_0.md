# Ítem 7 — Coherencia y versionamiento documental del Sprint 4

| Metadato | Valor |
|---|---|
| Proyecto | EcoLogística Lima |
| Sprint / consigna | Sprint 4, ítem 7 |
| Versión del informe | 1.0.0 |
| Fecha | 12/11/2026, America/Lima |
| Redacción | Antony Munive Rios (@ANTONY-MUNIVE), con apoyo de IA (Claude) |
| Revisión | Frank Roy Yupanqui Acevedo y Julio Naupari, dueños de los documentos de Inicio y Planificación |
| Base de trabajo | `main` en `8cf6258` |
| Antecedente | [Ítem 7 del Sprint 3](<../Sprint 03/07 Coherencia y versionamiento documental V_1_0_0.md>) |

## Alcance y método

Se revisó con `git log` cada cambio hecho del 03/11 al 12/11/2026 en
`docs/01 Inicio` y `docs/02 Planificación`, para comprobar dos cosas:
- Que todo cambio de contenido normativo tenga una versión nueva o una fila de
  historial con fecha y origen.
- Que los enlaces apunten a la versión vigente.

El comprobador del CI (`scripts/check_docs.py`) valida que no haya enlaces rotos
en todo el repositorio.

## Versionamiento formal del Sprint 4

| Documento anterior (conservado en Git) | Versión vigente | Cambio del Sprint 4 | Origen |
|---|---|---|---|
| `06. Requisitos funcionales V_1_1_0.md` | [RF V_1_2_0](<../../01 Inicio/06. Requisitos funcionales V_1_2_0.md>) | RF-003: la licencia vencida permite guardar el perfil, pero no asignarlo; formato ASCII alfanumérico con guion para `licencia_numero` | Control de cambios [ECL-81](https://continental-team-il84x39k.atlassian.net/browse/ECL-81), 10/11/2026; implementado en código en [ECL-123](https://continental-team-il84x39k.atlassian.net/browse/ECL-123) |
| `11. Base de datos V_1_1_0.md` | V_1_2_0 (07/11/2026) | Modelo de rutas: `optimizacion`, `ruta`, `parada_ruta`, `pedido_no_asignado` | ECL-95 / ST-046 |
| `11. Base de datos V_1_2_0.md` | V_1_3_0 (07/11/2026) | Parámetros versionados: `parametro_version` y `parametro` | ECL-26 / EN-008 |
| `11. Base de datos V_1_3_0.md` | [BD V_1_4_0](<../../01 Inicio/11. Base de datos V_1_4_0.md>) (08/11/2026) | Cierre de rutas: referencia secuencial por ruta e índice de rutas cerradas | ECL-119 |
| BDD de US-006, US-008 y US-009 | Versión 1.0.0 del 07/11/2026 en cada archivo de `02 Planificación/BDD` | Ratificación de Julio | [ECL-97](https://continental-team-il84x39k.atlassian.net/browse/ECL-97) |
| BDD de ST-021 (conductores) | Versión 1.2.0 del 10/11/2026 | Decisiones de ECL-80 y ECL-81 | [ECL-80/81](<ECL-80-81 decisiones BDD conductores.md>) |

Cada versión nueva conserva el nombre anterior en Git (`git mv`) y agrega su
fila de historial.

Hubo además cambios editoriales que no cambian ninguna regla:
- La actualización de enlaces de las BDD al renombrar la base de datos
  (`d637583`).
- La nota «implementado en ECL-123» en RF-003 y en ST-021 (`96b71ec`).

## Coherencia entre documentos

| Concepto | Referencias | Comprobación |
|---|---|---|
| Formato de licencia | RF-003 V_1_2_0; BDD ST-021 1.2.0; `backend/app/schemas/conductor.py`; `frontend/src/domain/driverForm.ts` | El mismo patrón `^[A-Za-z0-9-]{1,20}$` en el documento, la BDD, el backend y el frontend |
| Límite de optimización | RNF-001; BDD US-006; `MAX_PEDIDOS` del servicio | 150 pedidos y 15 vehículos; la API responde 422 si hay más pedidos PENDIENTE en la fecha |
| Parámetros de cálculo | RN-011 a RN-014; BD V_1_4_0; [ECL-26](<ECL-26 parametros versionados y casos de referencia.md>) | Los códigos y unidades coinciden. `CAPTURA_CO2_ARBOL_ANIO` sin valor en todos: por eso el dashboard muestra «No disponible» |
| Jornada de la incidencia (I03) | RF-012; BDD ECL-72; [validación ECL-82](<VALIDACION_US012_ECL82_V_1_1_0.md>) | Cerrada en el Sprint 4. En el Sprint 3 figuraba como pendiente. |
| Sesión de 60 minutos | RNF-003; WCAG 2.2.1; [ECL-83](<ECL-83 aviso de sesion.md>) | Aviso 2 minutos antes y tope absoluto de 12 h |

## Hallazgo de versionamiento

**`01 Transformando a ágil V_1_0_0.md` cambió de contenido normativo sin versión
nueva.**
- Los commits `e731acd` (ECL-89, regla A10) y `500f385` (ECL-91, regla A12)
  agregaron reglas de revisión y de corte de PR al proceso.
- El archivo mantiene la versión 1.0.0 y no tiene fila de historial para esos
  cambios.

**Propuesta para los dueños (Julio y Frank):**
1. Renombrar con `git mv` a `01 Transformando a ágil V_1_1_0.md`.
2. Agregar la fila 1.1.0 con fecha 10/11/2026 y origen ECL-89 y ECL-91.
3. Actualizar los enlaces activos: 7 archivos lo citan.

No se hace en este PR para no chocar con los documentos de cierre abiertos
(#145 lo enlaza).

## Documentos nuevos del Sprint 4

Los informes de cierre siguen la convención `NN Nombre V_1_0_0.md` de los
sprints anteriores:
- 01 Revisión.
- 02 Retrospectiva.
- 03 Calidad.
- 04 OWASP.
- 05 WCAG.
- La matriz de trazabilidad.

Los documentos técnicos por ticket (`ECL-NN …`) conservan la convención
acordada en [ECL-99](<CONVENCIONES_Y_GLOSARIO_ECL99.md>).

[↑ Índice del Sprint 4](README.md)

[← Volver al README principal](../../../README.md)
