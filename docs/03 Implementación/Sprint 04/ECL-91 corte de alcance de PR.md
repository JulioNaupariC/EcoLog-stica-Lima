# ECL-91 — Corte de alcance de PR y seguimiento A12

Responsable: Giancarlo Soto (@GiancarloSE). Revisión: Julio o José para `.github/`; dueño de documentación según CODEOWNERS. Fuente: [acción A12 de la retrospectiva del Sprint 3](<../Sprint 03/02 Retrospectiva del Sprint V_1_0_0.md>) y [ECL-91](https://continental-team-il84x39k.atlassian.net/browse/ECL-91). El registro alimenta [ECL-101](https://continental-team-il84x39k.atlassian.net/browse/ECL-101); no sustituye la retrospectiva ni cambia Jira.

## Regla y coordinación con A10

La regla queda junto a A10 / ECL-89 en la [plantilla de PR](../../../.github/pull_request_template.md) y en el [DoD global](<../../02 Planificación/01 Transformando a ágil V_1_0_0.md>). ECL-89 ya estaba integrado por [PR #123](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/123) en `main` `0658771`; al abrir esta rama no había PR abiertos. Se conserva su tabla de aprobación comentada y la regla de que el autor integra. Esta coordinación se basa en GitHub; no se atribuye una conversación con Frank.

Cuando un PR supera **10 archivos computables o 24 horas abierto**, el autor deja un incremento coherente ya validado, retira el resto y abre/enlaza el ticket que lo continuará, con alcance, responsable y criterio de aceptación. Si no lo hace, el revisor pide el corte. Giancarlo lo aplica al revisar `frontend/`. Un PR por encima del límite sin justificación se divide antes de integrar. La justificación no reemplaza el seguimiento del resto, la auditoría independiente, las aprobaciones comentadas ni los checks del head final.

El revisor deja la solicitud y su decisión en la revisión de GitHub; el autor registra qué entrega, qué retira y el enlace del ticket en la plantilla. Hasta resolver el corte y su trazabilidad no se completa ese checklist ni se integra. La sesión implementadora no aprueba su propio trabajo.

## Cómo contar

- Se cuenta el diff completo del PR contra su base: código, pruebas, configuración, documentación y renombrados. Cada entrada del diff cuenta una vez; no se suman archivos por commit. Un renombrado cuenta una vez.
- Solo se excluyen evidencias identificadas por ruta. En esta medición se revisaron las carpetas `evidencias/`: capturas, informes y registros conservados se excluyen; scripts e instrumentos ejecutables y configuración (`.py`, `.mjs`, `.cjs`, `.ts`, `.tsx`, `.js`, `.ps1`, `.yaml`, `.yml`, `.sh`, `.toml`) siguen computando aunque estén allí. No basta cambiar el nombre o ubicación para excluir trabajo funcional. La lista exacta por PR está en el snapshot.
- Edad: desde `created_at`, incluido Draft, hasta `merged_at`; para cerrados sin merge, `closed_at`; para abiertos, el instante de consulta. Nuevos commits no reinician el reloj. Se compara en segundos, antes de redondear para mostrar horas.
- La condición es **archivos > 10 O segundos > 86400**. Exactamente 10 archivos o 24 horas no activan el corte por sí solos. Se comprueba al abrir, al cambiar el diff y antes del merge; una lectura actual no reconstruye todos los tamaños intermedios de un PR histórico.
- Un ticket principal, una dependencia, una referencia a otra historia o un comentario «OK» no demuestran por sí solos seguimiento del alcance retirado. Se necesita una relación concreta con el trabajo restante y su fuente. Sin acceso a Jira no se afirma existencia, estado ni aceptación dentro de Jira.

## Corte inicial para ECL-101

Consulta: **10/11/2026, 22:59:33, America/Lima** (`2026-11-11T03:59:33.786Z`). `main` de referencia: `0658771d87aa1c95bd94a31efbca69c83bf0b5e3`. No es el cierre final del sprint ni evidencia de aplicación retroactiva de la regla.

GitHub no tenía milestones ni etiquetas de sprint. Se publica una **cohorte operativa, pendiente de ratificar contra Jira**, formada por **#85 y #87–#123**, todos contra `main`: trabajo de Green IT, rutas y acciones del Sprint 4. Se revisaron también #84 (ECL-69, Review del Sprint 3) y #86 (rama de cierre del Sprint 3), excluidos por pertenecer al cierre anterior. El PR de ECL-91 y los posteriores a la captura aún no existían en esa muestra. No se presenta esta selección como asignación oficial de sprint en Jira.

| Medida | PR |
|---|---:|
| Cohorte operativa | 38 |
| Superan alguno de los límites | 17 |
| Por archivos | 16 |
| Por edad | 1 |
| Derivación explícita del resto en el propio PR | 1 |
| Relación posterior parcial con un ticket identificable | 2 |
| Sin seguimiento suficiente verificable en las fuentes consultadas | 14 |

**Comparación conservadora:** 1/17 tiene derivación explícita documentada; otros 2/17 tienen seguimiento posterior parcial. Los tres cuentan como PR con alguna relación identificable de seguimiento, pero **no acreditan 3/17 de cumplimiento completo de A12**, ni que el corte ocurriera antes del merge. Los 14 restantes son «no verificados», no una afirmación de que sus tickets no existan. Todos los 17 ya estaban mergeados al capturar; no se reescribe su historia ni se atribuye una división que no se observó.

| PR | Total | Evidencias excluidas | Computables | Horas | Límite superado | Seguimiento observado |
|---|---:|---:|---:|---:|---|---|
| [#85](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/85) | 13 | 0 | 13 | 1,62 | Archivos | No verificado |
| [#88](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/88) | 17 | 3 | 14 | 2,33 | Archivos | No verificado |
| [#89](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/89) | 20 | 0 | 20 | 3,05 | Archivos | No verificado |
| [#95](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/95) | 51 | 29 | 22 | 0,28 | Archivos | No verificado |
| [#96](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/96) | 21 | 0 | 21 | 0,55 | Archivos | No verificado |
| [#97](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/97) | 3 | 0 | 3 | 43,16 | Edad | No verificado |
| [#102](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/102) | 23 | 0 | 23 | 0,18 | Archivos | No verificado |
| [#104](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/104) | 53 | 32 | 21 | 0,36 | Archivos | No verificado |
| [#107](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/107) | 32 | 4 | 28 | 0,71 | Archivos | No verificado |
| [#109](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/109) | 22 | 0 | 22 | 0,87 | Archivos | No verificado |
| [#110](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/110) | 35 | 0 | 35 | 1,75 | Archivos | No verificado |
| [#111](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/111) | 14 | 0 | 14 | 1,95 | Archivos | Explícito: ECL-21, ECL-79, ECL-15 |
| [#115](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/115) | 19 | 7 | 12 | 0,26 | Archivos | No verificado |
| [#116](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/116) | 21 | 5 | 16 | 0,66 | Archivos | Posterior parcial: ECL-119 |
| [#117](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/117) | 32 | 0 | 32 | 0,32 | Archivos | Posterior parcial: ECL-120 |
| [#118](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/118) | 45 | 22 | 23 | 0,15 | Archivos | No verificado |
| [#119](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/119) | 28 | 11 | 17 | 0,97 | Archivos | No verificado |

Fuentes de los seguimientos:

- **#111:** [constancia del autor](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/111#issuecomment-6717714597) y «Fuera del alcance» del PR derivan lo pendiente a ECL-21, ECL-79 y ECL-15. Esto acredita la relación escrita, no el estado de Jira ni el corte completo.
- **#116:** [#117 / ECL-119](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/117) declara ser el backend que faltaba al dashboard #116. Es trazabilidad posterior y parcial; no cubre todos los pendientes de US-009.
- **#117:** «Fuera de alcance» identifica la pantalla del Operador; [#119 / ECL-120](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/119) implementa esa pantalla sobre ECL-119. No se acredita aquí seguimiento del despacho al conductor, equivalente ambiental o campaña RNF-012 también pendientes en #117.
- **#96:** menciona una posible limpieza en ECL-111, ya entregado por #95; se conserva como candidato a confirmar, sin contarlo como seguimiento suficiente del resto. Las otras referencias a dependencias tampoco se contabilizan automáticamente.

## Evidencia y actualización

[CSV de los 38 PR](evidencias/ECL-91/corte-20261110/prs.csv) y [snapshot de fuentes, archivos y clasificación](evidencias/ECL-91/corte-20261110/snapshot.json). Se consultaron listas paginadas de PR contra `main`, cada `/pulls/{numero}` y `/pulls/{numero}/files` (100 entradas por página, total contrastado con `changed_files`); para los 17 se leyeron descripción, comentarios generales, revisiones y comentarios de código. Las fuentes públicas y los heads consultados quedan registrados. No se versionan credenciales ni los cuerpos completos de conversaciones.

Para ECL-101, el responsable de la retrospectiva ratifica la cohorte contra el Sprint 4 de Jira, añade los PR posteriores y repite el conteo de archivos y edad. Para cada caso comprueba el ticket del resto y anota su fuente, alcance y responsable; cuando haya trabajo pendiente sin ticket, su autor lo registra en Jira y enlaza el PR. No se crean tickets vacíos para aparentar cumplimiento. Si todo se entregó, el autor y revisor dejan la explicación verificable para evaluar ese caso, sin contabilizarla como ticket inexistente. Un ticket genérico ECL-91 o ECL-101 no acredita por sí solo el seguimiento específico de todos los PR.

Las nuevas capturas deben ir en otro directorio fechado, preservando este corte. La instantánea del diff final solo identifica casos observables; no prueba que un PR nunca superase 10 archivos en un estado anterior. No se atribuye a esta sesión acceso a Jira ni modificación de PR históricos.

## Criterios y revisión

| Ruta | Comprobación |
|---|---|
| Dorada | Regla visible en DoD y plantilla, junto a A10; incluye autor, revisor y ticket del resto. |
| Feliz | El autor enlaza el ticket del alcance retirado, el revisor comprueba la relación y deja decisión comentada. El corte histórico distingue evidencia explícita, posterior parcial y no verificada; no acredita el cumplimiento universal. |
| Infeliz | Si supera el límite sin justificación, el revisor solicita dividirlo y no se integra hasta resolver el corte y seguimiento. No se simula un rechazo o división de un PR real. |

Comprobaciones de borde para revisar la regla: 10 archivos y 24 horas exactas no disparan; 11 archivos o 24 horas más un segundo sí; 15 archivos con 5 evidencias excluibles quedan en 10; si una de esas cinco es un script computable, quedan en 11. Son ejemplos de interpretación, no métricas de PR adicionales.

Al ser documentación y plantilla, no cambia comportamiento ejecutable ni requiere nuevas pruebas de aplicación. Se valida navegación con `python scripts/check_docs.py`, ausencia de errores de diff y conservación de A10; CI, alertas CodeQL y auditoría independiente se comprueban en el PR del head final. La aceptación de los casos históricos no verificados corresponde al equipo; este informe no los declara resueltos ni cierra ECL-91/ECL-101 en Jira.

[Índice del Sprint 4](README.md) · [Volver al README principal](../../../README.md)
