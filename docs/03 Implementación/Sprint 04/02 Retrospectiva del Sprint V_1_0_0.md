# Retrospectiva del sprint

**Nombre del Proyecto:** EcoLogística Lima

**Líder del Proyecto:** Julio Armando Naupari Camarena

| Metadato | Valor |
|---|---|
| Ticket | [ECL-101 — Documentar la Retrospectiva del Sprint 4 y del proyecto](https://continental-team-il84x39k.atlassian.net/browse/ECL-101) |
| Sprint | Sprint 4 «Rutas y Cierre MVP» (Jira, sprint 39) |
| Periodo | 04/11/2026 al 20/11/2026 en Jira; evaluación adelantada al 13/11/2026 (America/Lima) |
| Objetivo del sprint | Entregar el MVP: rutas optimizadas (US-006), mapa (US-008) y dashboard de sostenibilidad (US-009) con parámetros versionados (EN-008); cerrar pendientes de calidad, seguridad y accesibilidad; aplicar la retroalimentación del Sprint 3 y dejar la demo ejecutable en una PC de laboratorio |
| Versión del documento | 1.0.0 |
| Fecha de corte | 12/11/2026, 21:00, America/Lima |
| Redacción | Antony Munive Rios (@ANTONY-MUNIVE), con apoyo de IA (Claude) |
| Revisión y validación con el equipo | Frank Roy Yupanqui Acevedo (@FrankRoyYA), dueño de ECL-101 |
| Base del análisis | Jira del sprint 39, PR #87 a #145 de GitHub, checks del CI y documentos de seguimiento de A9 a A12 |

El análisis es sin culpables: describe hechos del proceso y sus causas, no
desempeños individuales. Todos los datos de PR se pueden verificar en GitHub.

### Reunión de retrospectiva

**Pendiente de realizar.** Este documento reúne los hechos medibles para que la
reunión se dedique a decidir. Frank registra aquí:
- La fecha, el medio y los asistentes.
- Las opiniones del equipo.
- La aceptación o el cambio de las acciones A14 a A19.

Los puntos marcados con *(validar)* son lecturas de los datos que el equipo debe
confirmar o corregir.

### Resultado del sprint en cifras

| Indicador | Valor | Fuente |
|---|---|---|
| Elementos del sprint en Jira | 47: 41 con puntos y 6 subtareas | Jira, sprint 39 |
| Puntos | **95 de 108 SP finalizados (88 %)** al corte; 8 SP más dependen de integrar los documentos de cierre | Jira |
| Historias de usuario completas | US-006 (ECL-12, 13 SP), US-008 (ECL-14, 8 SP), US-009 (ECL-15, 5 SP) | Jira y `main` |
| PR integrados | 42 (#87 a #139, sin Dependabot) | GitHub |
| PR con aprobación de otra persona | 42 de 42 | GitHub |
| Aprobaciones que dicen qué se revisó | **3 de 90** (cuerpo de 40 caracteres o más) | GitHub, reseñas de cada PR |
| PR integrados por alguien distinto del autor | 1 de 42 (#120) | GitHub |
| PR que superan 10 archivos o 24 h | 17 de 38 antes de la regla A12; **0 de 5** después | [ECL-91](<ECL-91 corte de alcance de PR.md>) y GitHub |
| RNF-001 | P95 de 20,18 s (límite de 45 s) en 30 corridas | [ECL-21](<ECL-21 benchmark RNF-001.md>) |
| Pruebas | Backend: 1 329 unitarias y 348 de integración. Frontend: 1 018 en verde. | `pytest --collect-only` y Vitest al corte |

## ¿Qué aprendimos?

1. **Un contrato con datos simulados destraba al equipo antes que el motor real.**
   La API de rutas con datos simulados (ECL-94,
   [#89](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/89)) llegó el 06/11.
   El mapa (#104) y el dashboard (#116) se construyeron sobre ella. El servicio real
   (#111) entró el 08/11 sin cambiar el contrato. Es el mismo aprendizaje del Sprint 3,
   ahora aplicado desde el inicio.
2. **Medir antes de afirmar sigue dando resultado.**
   - El P95 real (20,18 s) se midió en 30 corridas de extremo a extremo.
   - El ahorro de Green IT se midió antes y después con el mismo protocolo
     (ECL-108 y ECL-115).
   - El ensayo de la demo midió cada paso y encontró que la fecha de hoy quedaba
     con 157 pedidos, y el motor rechaza más de 150. Se corrigió en
     [#142](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/142) antes
     de la evaluación.
3. **Una prueba que depende de la fecha es una bomba de tiempo.** `test_seed_demo`
   usaba una hora fija. Desde el 12/11 a las 09:00 rompió el CI de todos los PR. Se
   corrigió en [#139](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/139)
   usando la hora actual.
4. **Activar una herramienta sin preparar su flujo genera ruido.** Al activar
   Dependabot (ECL-85) llegaron 10 PR el mismo día. Los de pip fallaron porque no
   regeneraban los `.lock`. Se cerraron con un comentario y se pausaron las
   actualizaciones de versión hasta el 20/11
   ([#138](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/138)). Las
   alertas de seguridad siguen activas.

## ¿Qué estamos haciendo bien?

- **Nada llega a `main` sin aprobación ni CI en verde.** Los 42 PR tienen la
  aprobación de otra persona. El CI suma la auditoría de dependencias (bloqueante)
  y Lighthouse CI a los checks del Sprint 3.
- **Se cumplieron las tres historias del MVP** y los pendientes de calidad,
  seguridad y accesibilidad del Sprint 3:
  - ECL-83: aviso y renovación de sesión.
  - ECL-84: cabeceras de seguridad y cierre de S8703.
  - ECL-85: cadena de suministro.
  - ECL-86: modelo de amenazas.
  - ECL-87: code smells del frontend.
- **A12 funcionó en cuanto se publicó.** Después del #124 los PR son pequeños: el
  más grande tiene 8 archivos y ninguno estuvo un día abierto.
- **Las limitaciones se declaran:**
  - Casos de RNF-011 vacíos.
  - ECL-68 sin acreditar.
  - 403 con paradas del Sprint 3.
  - «Equivalente ambiental: No disponible» sin un factor con fuente.
  - El 1.3.2 de WCAG por confirmar.
- **El trabajo bloqueado se reasignó en Jira con un comentario** en vez de
  esperar. Fue el caso de ECL-117, ECL-85 y ECL-105.

## ¿Qué podemos hacer mejor?

### Personas

- **El camino crítico dependió de personas con poca disponibilidad en la última
  semana.** Varias tareas asignadas a Julio se reasignaron a Antony en los últimos días
  para no bloquear a Giancarlo y a Frank:
  - ECL-117, el informe Green IT.
  - ECL-85, la cadena de suministro.
  - ECL-105, los datos de la demo.

  ECL-68 (laboratorio) y los casos de RNF-011 de ECL-26 siguen pendientes.
  *(validar las causas con el equipo)*
- **La fecha de evaluación se adelantó del 20/11 al 13/11.** Los cinco documentos
  de cierre (ECL-100 a ECL-104) seguían en «Tareas por hacer» el 12/11 y se
  redactaron esa noche.

### Relaciones

- **A10 no se adoptó.** Después de publicarse la regla (#123, 11/11), las 6
  integraciones siguientes (#124 a #127, #138 y #139) se aprobaron con cuerpos de
  0 a 20 caracteres, como «ok» o un emoji. En todo el sprint, solo 3 de 90
  aprobaciones dicen qué se revisó.
- **Los dueños de carpeta no siempre estuvieron disponibles para aprobar.** Hubo
  que nombrar a Giancarlo dueño suplente temporal de backend, docs y README
  ([#112](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/112)).

### Procesos

- **Jira no acompañó a GitHub.** Hubo tareas con el PR integrado que nadie pasó a
  «Finalizada»; Antony movió a mano las que ya estaban terminadas, y las 5 tareas de cierre
  seguían sin empezar en Jira el 12/11.
- **17 de 38 PR superaron el límite de A12 antes de que se publicara la regla**
  (10/11). Solo 1 dejó explícito el ticket para el resto (#111).
- **El #120 lo integró una persona distinta de su autor** (Frank lo había dejado
  aprobado sin integrar). Fue para no bloquear el sprint, pero rompe la segunda
  mitad de A10.

### Herramientas

- **Las pruebas con hora fija no fallaron hasta que llegó esa hora** (ver
  «Aprendimos», punto 3).
- **Dependabot se activó sin un procedimiento** para regenerar los `.lock` de pip
  (ver «Aprendimos», punto 4).
- **No hay staging.** La excepción del DoD sigue abierta (ECL-107 no entró al
  sprint).
- **El repositorio está en una cuenta personal**, que no admite el rol de
  administrador para colaboradores. Las configuraciones de seguridad
  (Dependabot, protección de `main`) solo las puede hacer el dueño. Hay un
  traspaso previsto después del 13/11.

### Acciones a realizar

**Seguimiento de las acciones del Sprint 3** (definidas en la
[Retrospectiva del Sprint 3](<../Sprint 03/02 Retrospectiva del Sprint V_1_0_0.md>)):

| Acción | Responsable | Estado | Evidencia |
|---|---|---|---|
| A9 — Revisión de Code Owners y rama al día en `main` | Julio | **Cumplida** | La protección de `main` exige la aprobación de los Code Owners, descarta aprobaciones antiguas y exige la rama al día ([captura](<evidencias/ECL-85/ECL-85-proteccion-main-code-owners.png>)). Necesitó un dueño suplente (#112). |
| A10 — Aprobación con lo revisado; el autor integra | Frank | **No cumplida** | 3 de 90 aprobaciones con contenido; 0 de 6 después de publicar la regla. 41 de 42 PR los integró su autor. Continúa como A14. |
| A11 — 5/5 integrantes con la app en local | José | **Parcial** | La [guía de ECL-90](<guias/GUIA_ENTORNO_LOCAL_ECL90.md>) se publicó, pero no declara 5/5 comprobados al 06/11. *(validar con el equipo cuántos la levantaron)* |
| A12 — Cortar PR de más de 10 archivos o 24 h | Giancarlo | **Cumplida desde su publicación** | 0 de 5 PR la superan después del #124. Antes: 17 de 38 ([ECL-91](<ECL-91 corte de alcance de PR.md>)). |
| A13 — Cerrar S8703, fijar Actions por SHA y activar Dependabot | Antony | **Cumplida** | S8703 cerrada en [#87](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/87); 21 `uses:` fijados por SHA y auditoría de dependencias bloqueante en [#126](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/126); alertas de Dependabot activas ([captura](<evidencias/ECL-85/ECL-85-dependabot-alertas.png>)). La cifra de vulnerabilidades del proyecto va en el informe de ECL-102. |

**Acciones nuevas** (propuestas; se crean en Jira cuando el equipo las acepte):

| Acción | Dimensión | Qué | Responsable propuesto | Fecha | Métrica |
|---|---|---|---|---|---|
| A14 | Relaciones | La aprobación sigue una plantilla de 3 líneas: qué se probó, qué se leyó y qué queda fuera. Si no la tiene, no cuenta como aprobación. | Frank | Desde el 14/11 | 100 % de las aprobaciones con las 3 líneas |
| A15 | Procesos | Al integrar un PR, su autor pasa el ticket a «Finalizada» el mismo día. En la daily se revisa el tablero contra la lista de PR integrados. | Cada autor; control de Giancarlo | Desde el 14/11 | 0 tickets con PR integrado fuera de «Finalizada» por más de 24 h |
| A16 | Personas | Cada tarea del camino crítico tiene un suplente nombrado en Jira desde la planificación. Si el responsable no avanza en 48 h, el suplente la toma con un comentario. | Julio (líder) | Próxima planificación | 0 tareas del camino crítico bloqueadas más de 48 h |
| A17 | Procesos | Los documentos de cierre se empiezan en la mitad del sprint con datos parciales, y no la víspera de la evaluación. | Dueños de ECL-100 a ECL-104 | Mitad del próximo sprint | Borradores de los 5 documentos en PR 3 días antes de la evaluación |
| A18 | Herramientas | Ninguna prueba usa una fecha u hora fija del calendario: se calcula desde «ahora» o se inyecta un reloj. | Antony | 20/11 | 0 pruebas con fechas fijas futuras (revisión con `grep`) |
| A19 | Herramientas | Procedimiento para los PR de Dependabot de pip: regenerar `requirements.lock` antes de aprobar. Reactivar las actualizaciones de versión el 20/11. | Antony | 20/11 | 0 PR de Dependabot cerrados por un `.lock` desactualizado |

## Retrospectiva del proyecto (Sprints 1 a 4)

*(validar con el equipo)* Lo que el proyecto deja como práctica:
- **Contrato primero.** Las API simuladas permitieron trabajar en paralelo en
  los Sprints 3 y 4.
- **CI con base de datos real y SAST desde el Sprint 3.** CodeQL, SonarCloud, la
  auditoría de dependencias y la integración con PostGIS detectaron problemas que
  las pruebas unitarias no veían.
- **Medir y declarar límites.** Cada informe distingue lo medido de lo pendiente.
- **Lo que no logramos cerrar en 4 sprints:**
  - La demo en el laboratorio (ECL-68).
  - El staging (ECL-107).
  - La reoptimización (US-007).
  - Que Jira refleje el estado real sin intervención manual.

## Historial de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 12/11/2026 | Borrador con las cifras del Sprint 4, las cuatro dimensiones, el seguimiento de A9 a A13 y las acciones A14 a A19 propuestas. Falta la reunión del equipo. |

[Volver al índice del Sprint 4](README.md) ·
[← Volver al README principal](../../../README.md)
