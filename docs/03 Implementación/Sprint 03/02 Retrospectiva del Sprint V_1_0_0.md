# Retrospectiva del sprint

**Nombre del Proyecto:** EcoLogística Lima

**Líder del Proyecto:** Julio Armando Naupari Camarena

| Metadato | Valor |
|---|---|
| Ticket | [ECL-70 — Documentar la Retrospectiva del Sprint 3](https://continental-team-il84x39k.atlassian.net/browse/ECL-70) |
| Sprint | Sprint 3 — Calidad y Seguridad (Jira, sprint 38) |
| Periodo | 26/10/2026–30/10/2026, America/Lima |
| Objetivo del sprint | Entregar el registro de incidencias del conductor (US-012) y acreditar la calidad de código (SonarCloud), la seguridad (OWASP Top 10 2025) y la accesibilidad (WCAG 2.1 AA), dejando la aplicación ejecutable en una PC de laboratorio sin permisos de administrador para la demostración del 30/10/2026 |
| Versión del documento | 1.0.0 |
| Fecha de corte | 29/10/2026, America/Lima |
| Autor | Frank Roy Yupanqui Acevedo — @FrankRoyYA |
| Base del análisis | Jira del sprint 38, PR #59–#80 de GitHub, checks del CI, SonarCloud y la reunión de retrospectiva del equipo |

El análisis es sin culpables: describe hechos del proceso y sus causas, no desempeños
individuales. Los datos de PR se pueden verificar en la pestaña *Pull requests* del repositorio.

### Reunión de retrospectiva

- Fecha y hora: [COMPLETAR]
- Medio: [COMPLETAR, por ejemplo llamada o WhatsApp]
- Asistentes: [COMPLETAR]
- Acuerdos: el equipo revisó y aceptó el análisis de las 4 dimensiones y las acciones A9–A13.

### Resultado del sprint en cifras

| Indicador | Valor | Fuente |
|---|---|---|
| Elementos del sprint en Jira | 16 reportados: 11 en Finalizada y 5 en Tareas por hacer; solo se identificaron 4 pendientes (ECL-68, ECL-69, ECL-70, ECL-71). Conteo pendiente de conciliación | Jira, sprint 38 |
| Historias completas | US-012 (ECL-18, con ECL-72 a ECL-76) y US-013 (ECL-77) | Jira y `main` |
| PR integrados | 21 (#59–#80, sin contar el #75, que se cerró sin integrar) | GitHub |
| PR integrados con aprobación de una persona distinta del autor | 21 de 21 | GitHub |
| Quality Gate de SonarCloud en `main` | PASSED; cobertura 94,5 %, duplicación 0,0 % | [03 Calidad de código](<03 Calidad de código V_1_0_0.md>) |
| Vulnerabilidades en SonarCloud | De 2 a 1 tras los PR #77 y #78 (queda `S8703`, mitigada; cierre en ECL-84) | [04 OWASP](<04 OWASP V_1_0_0.md>) |
| Accesibilidad | WCAG 2.1 AA evaluada; 1 hallazgo pendiente (2.2.1, ECL-83) | [05 WCAG](<05 WCAG V_1_0_0.md>) |
| Prueba offline real | 10/10 en Chrome y 10/10 en Firefox con API y PostGIS reales | [VALIDACION_US012](<validaciones/VALIDACION_US012.md>) |

## ¿Qué aprendimos?

1. **Avanzar por dependencias, y no por fechas, acorta el camino crítico.** La API de
   incidencias (ECL-73, [#61](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/61))
   llegó a `main` el 26/10. El formulario (ECL-74) y la vista de Operación (ECL-75) se
   empezaron contra un contrato simulado de la API y se conectaron a la API real en cuanto
   estuvo disponible. US-012 quedó completa el 27/10 con las pruebas de ECL-76
   ([#73](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/73)).
2. **El CI con base de datos real detecta lo que las pruebas unitarias no ven.** En el
   [#69](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/69), `pedido.latitud`
   pasó todas las pruebas unitarias porque los dobles de prueba tenían un atributo que el
   modelo real no tiene. El check «Backend / Integration» lo detectó antes de llegar a `main`.
   Los dobles de prueba deben respetar el modelo real.
3. **El análisis de seguridad encontró problemas reales.** SonarCloud, `pip-audit` y
   `npm audit` encontraron una SSRF, un falso positivo, dependencias de desarrollo vulnerables
   y que la demo local ejecuta el servidor de desarrollo de Vite
   ([#77](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/77),
   [#78](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/78)).
4. **Un resultado no se afirma antes de medirlo.** Se previó «0 vulnerabilidades» tras el #78,
   pero el re-análisis mantuvo abierta `S8703`, y los documentos de calidad y seguridad se
   corrigieron con la cifra real.

## ¿Qué estamos haciendo bien?

- **La autoría coincide entre Git y Jira.** Cada integrante programó, abrió y, en casi todos
  los casos, integró sus propios PR.
- **Nada llega a `main` sin aprobación ni CI en verde.** Los 21 PR integrados tienen la
  aprobación de otra persona, y el CI (pruebas, CodeQL, SonarCloud y documentación) quedó en
  verde antes de cada merge.
- **Las limitaciones se declaran en vez de ocultarse:** I03 parcial (ECL-82), ECL-68 validada
  solo en la laptop de desarrollo, la SSRF mitigada pero abierta y el hallazgo WCAG 2.2.1
  (ECL-83).
- **El esqueleto de enlaces del README** (Ítem 6, [#66](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/66))
  permitió que cada documento ocupara su propia línea sin choques de merge.
- **Los hallazgos de las revisiones se corrigieron en PR de seguimiento.** Por ejemplo,
  [#65](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/65) tras la revisión de Frank y
  [#76](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/76) para dejar limpia la guía
  de ECL-68.

## ¿Qué podemos hacer mejor?

### Personas

- **Algunos trabajos crecieron más allá de su alcance cerca de la Review.** El
  [#74](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/74) (ECL-68) pasó de 4 a 12
  archivos, con una guía de 549 líneas, la víspera de la demostración. Requirió el
  [#76](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/76) para separar el
  diagnóstico, y un revert ([#75](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/75))
  que se descartó.
- **La carga se concentró en el camino crítico.** La API de incidencias bloqueaba a tres
  integrantes; en el Sprint 4 el optimizador (US-006) cumple ese papel.

### Relaciones

- **Varias aprobaciones se dieron sin comentario sobre lo revisado** (por ejemplo, #71, #72 y
  #73), lo que deja poca evidencia de la revisión.
- **Algunos acuerdos se tomaron solo de palabra.** El aplazamiento de la validación de jornada
  de I03 a ECL-82 tuvo que pedirse por escrito después del merge del
  [#65](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/65).

### Procesos

- **Hubo tres integraciones fuera de la regla acordada:**
  - el [#62](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/62) se integró con la BDD
    de ECL-72 en BORRADOR, sin la aprobación de Julio (se regularizó en el
    [#63](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/63));
  - el [#61](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/61) se integró entre la
    aprobación y el pedido de cambios de la revisión (se corrigió en el #65);
  - el [#74](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/74) lo integró alguien
    distinto de su autor.
- **Hubo ramas desactualizadas:** el #66 estuvo 39 h abierto y quedó 28 commits detrás de
  `main`, con conflictos en los README.
- **El estado de Jira no siempre acompañó a GitHub:** ECL-71 sigue en «Tareas por hacer»
  aunque el [#64](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/64) está integrado
  desde el 26/10.

### Herramientas

- **No todos los equipos tenían Docker**, así que la integración con base real la validó
  sobre todo el CI. La campaña de ECL-76 requirió instalarlo a mitad del sprint.
- **La protección de `main` exige 1 aprobación**, pero no la revisión de los Code Owners
  ni la rama al día.
- **Las alertas de Dependabot están desactivadas** y las acciones del CI están fijadas por
  etiqueta, no por SHA.
- **Copilot no revisó los PR** por falta de cuota.

### Acciones a realizar

**Seguimiento de las acciones del Sprint 2** (definidas en la
[Retrospectiva del Sprint 2](<../04 Retrospectiva del Sprint V_1_0_0.md>)):

| Acción | Responsable | Estado | Evidencia |
|---|---|---|---|
| A1 — Comprobar el DoD antes de pasar a Finalizada | Julio | Parcial | Las 11 finalizadas tienen PR en `main` con CI en verde; ECL-71 sigue en «Tareas por hacer» con el #64 integrado, y ECL-68 no pasó a «En curso» |
| A2 — Aprobación de una persona distinta del autor | Julio | Cumplida | 21 de 21 PR integrados (#59–#80) con aprobación de otra persona |
| A3 — Autoría alineada con Jira | Antony | Cumplida | El autor de cada PR coincide con el responsable de su ticket; verificación PR por PR, sin el script de cruce |
| A4 — Ratificar las BDD antes de implementar | Frank | Parcial | ECL-47 y ECL-51 se aprobaron en el #64 (26/10, después del 20/10 comprometido); el #61 (ECL-73) se abrió antes de la BDD de ECL-72 (#62) y de su aprobación (#63), con contrato provisional, y se integró después de la aprobación |
| A5 — Story Points en historias y subtareas | Frank | Parcial | Padres y tareas con 26 SP; las subtareas ECL-72 a ECL-76 no tienen SP |
| A6 — Ensayo cronometrado de la demo | Giancarlo | Pendiente de confirmar | Frank lo confirmará con Giancarlo: fecha y duración si se realizó; en caso contrario, no cumplida. |
| A7 — Exigir la revisión de Code Owners en `main` | Julio | No cumplida | La protección solo exige 1 aprobación; el #69 tocó `frontend/` y `backend/` y se integró solo con la aprobación de backend. Continúa como A9 |
| A8 — Rama `sprint-N` protegida y eliminar las ramas de trabajo | Julio | Parcial | Existen `sprint-1` y `sprint-2`, pero `sprint-2` no está protegida y sigue abierta `feat/ECL-57-responsive-accessibility`; las del Sprint 3 se conservan hasta el 30/10 (acuerdo R4) |

**Acciones nuevas del Sprint 3** (creadas en Jira; se revisarán en la retrospectiva del Sprint 4):

| Acción | Dimensión | Qué | Responsable | Fecha | Métrica | Ticket |
|---|---|---|---|---|---|---|
| A9 | Procesos | Exigir en `main` la revisión de Code Owners y la rama al día | Julio | Primer día del Sprint 4 | 0 PR integrados sin la aprobación del dueño de cada carpeta | [ECL-88](https://continental-team-il84x39k.atlassian.net/browse/ECL-88) |
| A10 | Relaciones | Toda aprobación lleva un comentario con lo revisado; el autor es quien integra | Frank | Primera semana del Sprint 4 | 100 % de las aprobaciones con comentario | [ECL-89](https://continental-team-il84x39k.atlassian.net/browse/ECL-89) |
| A11 | Herramientas | Los 5 integrantes pueden levantar la app y correr la integración en su PC | José (con apoyo de Julio) | Primera semana del Sprint 4 | 5/5 integrantes con la app en local | [ECL-90](https://continental-team-il84x39k.atlassian.net/browse/ECL-90) |
| A12 | Personas | Cortar el alcance de un PR de más de 10 archivos o con más de un día abierto, con ticket para el resto | Giancarlo | Sprint 4 | Cada PR que supere el límite tiene su ticket de seguimiento | [ECL-91](https://continental-team-il84x39k.atlassian.net/browse/ECL-91) |
| A13 | Herramientas | Cerrar `S8703` (seguridad de C a A), fijar las acciones por SHA y activar Dependabot | Antony (ECL-84); ECL-85 a confirmar en la planificación | Sprint 4 | 0 vulnerabilidades en SonarCloud; acciones fijadas por SHA | [ECL-84](https://continental-team-il84x39k.atlassian.net/browse/ECL-84), [ECL-85](https://continental-team-il84x39k.atlassian.net/browse/ECL-85) |

## Historial de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 29/10/2026 | Retrospectiva del Sprint 3: cifras del sprint, cuatro dimensiones, seguimiento de A1–A8 y acciones A9–A13. |

[Volver al índice del Sprint 3](README.md) ·
[← Volver al README principal](../../../README.md)
