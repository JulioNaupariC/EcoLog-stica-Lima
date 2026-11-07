# Informe 02 — Estándares de ingeniería de software y guía de desarrollo verde

**Proyecto:** EcoLogística Lima — DistriRápido S.A.C.

| Metadato | Valor |
|---|---|
| Ticket | [ECL-118](https://continental-team-il84x39k.atlassian.net/browse/ECL-118), 2 SP |
| Autor | Frank Roy Yupanqui Acevedo — @FrankRoyYA |
| Revisor | Julio Armando Naupari Camarena — @JulioNaupariC |
| Versión del contenido | 0.2.0 — BORRADOR |
| Fecha de elaboración y consulta de fuentes | 06/11/2026, America/Lima |
| Código examinado | `main bb543a0`, después del merge de #91 |
| Commit ANTES de Green IT | `e09dcd80e32431018d4020bb02c89ffae7505705`, medido en ECL-108 |
| Fuente del orden de trabajo | Diagrama del Sprint 4 proporcionado por Frank; no constituye evidencia de implementación ni consulta del estado de Jira |

## 1. Objeto, alcance y estado de la evidencia

El informe relaciona calidad de producto, sostenibilidad y prácticas de
desarrollo con FastAPI, SQLAlchemy/PostgreSQL y React/Vite. Se conserva el
nombre de archivo V_1_0_0 exigido por el ticket; el contenido permanece como
borrador hasta completar su evidencia y revisión.

El flujo recibido identifica seis paquetes técnicos: ECL-109 (consultas y
paginación), ECL-110 (GZip y ETag), ECL-111 (React.lazy y paginación), ECL-112
(fuentes, imágenes, SVG y dependencias), ECL-113 (build y minificación con
Brotli/Gzip) y ECL-114 (green-audit.yml con LHCI). La medición DESPUÉS es
ECL-115; el cálculo SWDM v4 es ECL-116; el Informe 01 es ECL-117.
La disponibilidad en el diagrama indica orden de trabajo, no aceptación técnica.

La rúbrica define ocho optimizaciones individuales, cuyo desglose y asignación
a tickets fueron confirmados por Frank para esta revisión. La sección 6 las
mapea en ocho filas; no se presentan como implementadas. Siguen pendientes
los PR del incremento y las mediciones DESPUÉS de ECL-115. ECL-114 corresponde
al criterio 3 de la rúbrica y no se contabiliza entre las ocho optimizaciones.

La [campaña ANTES válida](<evidencias/antes/run-2026-11-06T23-50-12-524Z/README.md>)
documenta tres corridas de login, tres del itinerario y 60 respuestas API 200.
Inicio y Vehículos de Operador no fueron medibles mediante recarga completa:
la sesión de interfaz se perdía y la navegación terminaba en login. No se
atribuyen cifras de login a esas páginas ni se calculan mejoras sobre datos ausentes.

Las medianas ANTES de Performance fueron 55/100 en las dos páginas medibles;
el registro declara incumplidos los objetivos de FCP, LCP y peso. Son resultados
del servidor Vite en desarrollo, no de producción. Este informe no modifica
esas evidencias ni anuncia resultados DESPUÉS, kWh, g CO₂e o SCI inexistentes.

## 2. ISO/IEC 25010 y calidad de producto

El catálogo oficial identifica ISO/IEC 25010:2023 como edición publicada que
sustituye la edición de 2011. Se emplea como marco de calidad, sin declarar
certificación. Para comprobar públicamente la terminología solicitada se
consulta también el antecedente oficial de 2011; no se trasladan sus numerales
a la edición de 2023. Fuentes: [ISO, edición 2023][iso2023] y
[ISO, terminología pública de 2011][iso2011].

| Subcaracterística solicitada | Interpretación operativa para el proyecto | Ejemplo real y evidencia disponible |
|---|---|---|
| Eficiencia de desempeño: comportamiento temporal | Evaluar latencia y duración bajo condiciones reproducibles. | La [validación ST-038](<../Sprint 02/validaciones/VALIDACION_ST038.md>) registra un cambio de plan de agregación: mediana SQL 8,67 a 3,66 ms. Es evidencia histórica del Sprint 2, no mejora medida en Green IT. |
| Eficiencia de desempeño: utilización de recursos | Examinar transferencias, lecturas y trabajo de procesamiento. | ST-038 registra JSON del Inicio de 35 871 a 347 bytes y buffers de la consulta de pedidos de 721 a 28; no demuestra ahorro energético por sí solo. |
| Eficiencia de desempeño: capacidad | Comprobar límites de operación ante crecimiento de datos. | El [test de consultas de conductores](../../../backend/tests/integration/test_conductor_list_queries.py) limita las sentencias por página. ST-038 documenta 22 a 2 sentencias para 20 filas; no equivale a capacidad máxima acreditada. |
| Mantenibilidad: modularidad | Delimitar cambios entre API, servicios y repositorios. | [IndicadoresRepository](../../../backend/app/repositories/indicadores.py) concentra las agregaciones, separado de [la API](../../../backend/app/api/indicadores.py). La estructura es verificable; su existencia no cuantifica una reducción ambiental. |
| Mantenibilidad: analizabilidad | Poder diagnosticar causas y verificar cambios. | El [instrumento de medición del Inicio](../../../backend/scripts/measure_home_payload.py) y los [resultados ST-038](<../Sprint 02/validaciones/VALIDACION_ST038.md>) permiten contrastar tamaño y consultas. La campaña ECL-108 conserva JSON y CSV originales. |

Cada optimización nueva deberá vincular el fragmento ANTES del commit fijo,
su modificación DESPUÉS, la prueba de equivalencia funcional y la medición
correspondiente. Los antecedentes anteriores demuestran prácticas existentes;
no se contabilizan automáticamente entre las ocho optimizaciones del Sprint 4.

## 3. Principios seleccionados de Green Software Foundation

Se desarrollan los cuatro principios seleccionados por la rúbrica. No se
afirma que constituyan la totalidad del material de GSF.

| Principio | Fundamento y aplicación al proyecto | Evidencia necesaria para afirmar una mejora |
|---|---|---|
| Eficiencia de carbono | Reducir emisiones por servicio útil; no confundir menor CO₂ de reparto con menor huella digital de la aplicación. [Fuente GSF][gsf-carbon]. | Unidad funcional y frontera constantes; cálculo trazable ANTES/DESPUÉS. |
| Eficiencia energética | Reducir energía por trabajo completado, evitando actividad innecesaria. [Fuente GSF][gsf-energy]. | Telemetría energética o modelo identificado; latencia o bytes menores son indicadores indirectos, no kWh medidos. |
| Eficiencia de hardware | Considerar emisiones incorporadas y uso del equipo durante su vida útil. [Fuente GSF][gsf-hardware]. | Datos de asignación y vida útil del hardware; no afirmar prolongación de vida útil solo por obtener un Lighthouse mejor. |
| Medición con SCI | Normalizar emisiones por unidad funcional para comparar la misma prestación. [Medición GSF][gsf-measurement] y [especificación SCI][sci]. | Frontera, energía, intensidad de carbono, asignación de hardware y unidad funcional documentadas. |

### 3.1 Distinción entre SCI y SWDM v4

SCI se expresa como `SCI = (E × I + M) / R`: E es energía operativa (kWh),
I intensidad de carbono (g CO₂e/kWh), M emisiones incorporadas asignadas
(g CO₂e) y R unidades funcionales. La selección de frontera, periodo y fuentes
debe ser explícita; offsets no sustituyen la reducción de emisiones dentro
del cálculo. [Especificación SCI, versión consultada 1.1.0][sci].

SWDM v4 es un modelo de estimación basado en transferencia de datos y
supuestos de centros de datos, redes y dispositivos. Sus resultados no son
lecturas de un medidor eléctrico. Se deben conservar versión, factores,
unidades y supuestos de caché/visitantes; no sumar de nuevo emisiones que el
modelo ya incorpore. Un cálculo SWDM no acredita por sí solo un SCI completo.
[Fuente del modelo v4][swdm].

ECL-116 aportará los cálculos reproducibles requeridos por la rúbrica.
Mientras falten, no se publican cifras ambientales. La comparación futura
mantendrá la misma unidad funcional, por ejemplo una carga válida de la misma
página y rol, sin escoger una unidad que cambie artificialmente el resultado.

## 4. WSG: versión, numeración y correspondencia

La dirección indicada en el ticket, `w3c.github.io/sustyweb`, redirige a la
ubicación del grupo. Se verificó además el [borrador editorial actual][wsg-editor]
y se fija como referencia reproducible la [publicación de 16/10/2026][wsg].
Es un borrador de nota de grupo, no una Recomendación W3C final.

| Número en la publicación fijada | Título exacto | Aplicación propuesta |
|---|---|---|
| 1.2 | WSG (Web Sustainability Guidelines) layers of guidance | Separar orientación, criterios y evidencia; es un apartado introductorio, no una optimización específica. |
| 2.4 | Design efficient and streamlined user journeys | Revisar tareas sin pasos ni recargas evitables; conservar accesibilidad y permisos. |
| 3.1 | Set goals based on performance and energy impact | Fijar presupuestos verificables antes de comparar. |

En la matriz técnica se complementan con los apartados 3.2, 3.3, 3.7, 3.12,
3.16, 4.2, 4.3 y 4.6 de esa misma publicación, según corresponda a código,
datos y automatización. El mapeo es una interpretación del equipo, no una
declaración de conformidad WSG. Si la rúbrica emplea otra versión, debe
registrarse y compararse su numeración sin reemplazar títulos por conjetura.

### 4.1 Equivalencias entre rúbrica y versión oficial fijada

Los rótulos de la primera columna proceden de la rúbrica comunicada por Frank;
no son los títulos oficiales de esos mismos números. La equivalencia es temática.
Los títulos de la segunda columna se verificaron en la [publicación fijada][wsg].

| Pauta según la rúbrica | Pauta oficial equivalente en la versión fijada (número y título exactos) | Correspondencia para el informe |
|---|---|---|
| 1.2 — Formatos de imagen | 2.9 — Optimize media to reduce resource use | Inventario de medios y elección de formatos; sin raster en la aplicación, documentar esa ausencia y el trabajo de fuente de ECL-112, sin fabricar imágenes para justificar una conversión. |
| 2.4 — Caché | 4.2 — Optimize caching and support offline access | Caché de API, cliente y estáticos en ECL-110/113, con vigencia y autorización verificables. |
| 3.1 — Red y compresión | 4.3 — Reduce data transfer with compression | Brotli/Gzip de API y estáticos en ECL-110/113, con transferencia y costo de procesamiento por comprobar. |

La consulta del [borrador editorial][wsg-editor] también permitió localizar
las materias, pero no confirmó los títulos alternativos indicados en la
solicitud para caché y compresión. Se conservan los títulos comprobados de
la versión fechada, sin atribuirle otras redacciones. La tabla oficial 1.2,
2.4 y 3.1 anterior se mantiene para distinguir ambas numeraciones.

## 5. Guía de desarrollo verde para el stack del proyecto

Las reglas siguientes son criterios de revisión. Los ejemplos proceden del
corte de código examinado; no se presenta una regla propuesta como cambio ya
implementado. SOLID/SRP se aplica a responsabilidades; DRY evita duplicar
conocimiento; YAGNI evita funcionalidad especulativa. Ninguno demuestra ahorro
ambiental sin medición. Fuentes de principios: [SRP de Robert C. Martin][srp],
[DRY de Hunt y Thomas][dry] y [YAGNI de Martin Fowler][yagni].

### 5.1 Backend — FastAPI, SQLAlchemy y PostgreSQL

| Regla | Justificación | Ejemplo del repositorio y comprobación |
|---|---|---|
| Seleccionar solo columnas necesarias; usar existencia booleana cuando basta. | SRP: cada consulta responde a una necesidad; YAGNI: no materializar datos que no se utilizan. | [ClienteRepository.exists/search](../../../backend/app/repositories/clientes.py) usa EXISTS y selección de ID/nombre. ST-038 no demuestra aceleración de EXISTS: no atribuirla. |
| Evitar N+1 y paginar con límites y orden estable. | SRP separa acceso a datos de presentación; DRY evita búsquedas repetidas del mismo dato. | [ConductorRepository.list_page](../../../backend/app/repositories/conductores.py) une cuenta/conductor; [su prueba](../../../backend/tests/integration/test_conductor_list_queries.py) comprueba el número de sentencias. |
| Agregar en SQL y justificar índices con planes reales y costo de escritura. | YAGNI evita índices preventivos; SRP conserva el cálculo de agregados en su repositorio. | [IndicadoresRepository](../../../backend/app/repositories/indicadores.py) y ST-038 documentan agregación e índice justificado. Medir también costo de mantenerlo. |
| Aplicar caché y compresión solo con semántica segura y beneficio comprobado. | SRP sitúa políticas HTTP fuera del dominio; YAGNI evita compresión/cachés sin utilidad. | [API de indicadores](../../../backend/app/api/indicadores.py) usa caché privada de 30 s; clientes personales usan no-store. ECL-110 propone GZip y ETag, aún sin implementación/evidencia en este corte. No cachear credenciales ni mezclar usuarios. |

En el equivalente a MERN, una proyección SQLAlchemy de columnas sustituye la
intención de `.select()`/`.lean()`; no existe una equivalencia literal entre
ORM relacional y Mongoose. La compresión HTTP mediante `GZipMiddleware` es
el equivalente previsto a `compression` de Express, no una dependencia de
Node que deba añadirse a FastAPI. Se verificará en ECL-110 el código finalmente
elegido, cabeceras, bytes comprimidos/decodificados y costo de CPU.

### 5.2 Frontend — React y Vite

| Regla | Justificación | Ejemplo del repositorio y comprobación |
|---|---|---|
| Separar componentes de UI, servicios HTTP y sincronización. | SRP/SOLID reduce razones de cambio y permite probar efectos aislados. | [Hook de sincronización](../../../frontend/src/hooks/useIncidentSynchronization.ts) delega el envío a [incidentSync](../../../frontend/src/services/incidentSync.ts); verificar limpieza de listeners y cancelación al desmontar. |
| Reutilizar la misma política mediante componentes/contextos compartidos. | DRY evita duplicar conocimiento de notificaciones y temporizadores. | [ToastProvider](../../../frontend/src/components/ui/Toast.tsx) centraliza el ciclo de notificaciones. useMemo allí no acredita por sí mismo una mejora energética. |
| Cargar recursos cuando su uso lo justifique y mantener la alternativa de error. | YAGNI evita trabajo anticipado no necesario; SRP permite separar rutas/pantallas. | [App.tsx](../../../frontend/src/app/App.tsx) importa pantallas anticipadamente en ANTES. React.lazy de ECL-111 es un cambio previsto: requerirá comparación de red y pruebas de navegación, carga y error. |
| Auditar assets, dependencias y build sin retirar funciones ni accesibilidad. | YAGNI elimina recursos injustificados; DRY favorece assets compartidos sin duplicación. | [package.json](../../../frontend/package.json), [vite.config.ts](../../../frontend/vite.config.ts) y App.tsx son puntos de revisión de ECL-112/113. El material recibido no acredita que ya se hayan optimizado. |

No se prescribe memoización indiscriminada, retirada de validaciones de
seguridad ni reducción de funciones como medio de cumplir un presupuesto.
Un build de producción no se compara como si fuera la misma condición que
Vite en desarrollo sin declarar el cambio de entorno y repetir la referencia
que corresponda.

## 6. Matriz de mapeo directo de las ocho optimizaciones

El inventario siguiente corresponde a la rúbrica y asignaciones comunicadas
por Frank. Cada vínculo normativo es una aplicación propuesta, no prueba de
conformidad ni de implementación. Los apartados WSG corresponden a la versión
fijada en la sección 4. Las tres primeras eficiencias GSF son objetivos cuyo
efecto debe comprobarse; la medición documentará su alcance y sus límites.

| N.º | Optimización de la rúbrica y ticket | ISO/IEC 25010 | GSF seleccionado | WSG | Evidencia DESPUÉS |
|---|---|---|---|---|---|
| 1 | Consultas: columnas mínimas, filas en lugar de entidades e índices PostgreSQL — ECL-109 | Comportamiento temporal, utilización de recursos y analizabilidad | Eficiencia energética y de carbono; medición de consultas/bytes como indicadores, no kWh medidos | 3.16, 3.1 | pendiente: PR y medición ECL-115 |
| 2 | Paginación de 12 — ECL-109 (backend) y ECL-111 (frontend) | Capacidad, utilización de recursos y comportamiento temporal | Eficiencia energética; hardware como objetivo por verificar; medición por página | 3.16, 2.4 | pendiente: PR y medición ECL-115 |
| 3 | Imágenes WebP/AVIF — ECL-112: sin raster en la aplicación, documentar inventario y optimizar la fuente, sin fabricar imágenes | Utilización de recursos y analizabilidad | Eficiencia energética y de hardware como objetivos; medición del inventario y transferencia | 2.9; 2.11 para la fuente | pendiente: PR y medición ECL-115 |
| 4 | Lazy loading y code splitting — ECL-111 | Comportamiento temporal y modularidad | Eficiencia energética; hardware como objetivo por verificar; medición de carga diferida | 3.3, 3.7 | pendiente: PR y medición ECL-115 |
| 5 | Dependencias y APIs nativas — ECL-112 | Modularidad, analizabilidad y utilización de recursos | Eficiencia energética y de hardware como objetivos; medición del trabajo necesario | 3.12, 3.11 | pendiente: PR y medición ECL-115 |
| 6 | Reducción de peticiones HTTP y SVG inline — ECL-112 | Comportamiento temporal y utilización de recursos | Eficiencia energética y de carbono como objetivos; medición de peticiones y bytes | 2.9, 3.1 | pendiente: PR y medición ECL-115 |
| 7 | Caché: Cache-Control, ETag y cliente — ECL-110 (API) y ECL-113 (estáticos) | Utilización de recursos, comportamiento temporal y modularidad | Eficiencia energética y de carbono como objetivos; medición en visitas frías y repetidas | 4.2 | pendiente: PR y medición ECL-115 |
| 8 | Compresión Brotli/Gzip — ECL-110 (API) y ECL-113 (estáticos) | Utilización de recursos y comportamiento temporal | Eficiencia energética y de carbono como objetivos; medición de transferencia y costo de compresión | 4.3 | pendiente: PR y medición ECL-115 |

La tercera fila conserva el criterio de la rúbrica, pero no declara una
conversión WebP/AVIF realizada. Las capturas de evidencias del repositorio no
son imágenes raster servidas por la aplicación y no se alteran para cumplirlo.
El inventario y la optimización de fuente se documentarán en ECL-112.

Para completar cada fila se enlazarán archivos y commits ANTES/DESPUÉS,
pruebas de equivalencia funcional, mediciones y conclusión real. ECL-116
aportará el cálculo ambiental reproducible y ECL-117 el Informe 01. Una
reducción de peticiones no demuestra menor transferencia si el SVG inline
agranda otro recurso; caché y compresión tampoco acreditan ahorro sin comparar
condiciones equivalentes y sus costos.

**ECL-114 es transversal al criterio 3 de la rúbrica:** el workflow
green-audit.yml con LHCI debe conservar ejecuciones y artefactos. Se relaciona
con analizabilidad/modularidad, medición GSF y WSG 3.1/4.6; no es una novena
optimización ni sustituye ninguna de las ocho filas.

## 7. Método de comprobación y condiciones de cierre

1. Conservar el [protocolo y sus límites](<evidencias/antes/README.md>) y
   las [mediciones válidas de ANTES](<evidencias/antes/run-2026-11-06T23-50-12-524Z/README.md>).
   No modificar archivos históricos de evidencias para adaptar cifras.
2. Recibir los commits y la evidencia de las ocho optimizaciones ya identificadas,
   junto con el Informe 01. Completar la matriz con resultados reales y registrar incumplimientos.
3. Comparar condiciones equivalentes, páginas/roles y unidades. La rúbrica
   suministrada exige Performance ≥90, FCP ≤1,0 s, LCP ≤1,4 s, TBT ≤85 ms,
   CLS ≤0,02 y peso ≤1,1 MB; no se presentan como alcanzados en este borrador.
4. Incorporar el cálculo SWDM v4 reproducible de ECL-116 con sus supuestos.
   Mantener SCI y métricas de Lighthouse diferenciados; no inventar factores
   ni medir huella digital a partir del ahorro de combustible de las rutas.
5. Confirmar el glosario de ECL-99 cuando se publique. Deuda técnica no se
   presenta como esfuerzo de remediación, ni velocidad/SP como horas trabajadas.
6. Ejecutar validación documental, auditoría independiente y revisión de Julio.
   Solo cerrar ECL-118 con la matriz completa y evidencia real de sus afirmaciones.

## 8. Referencias verificadas

Las fuentes se consultaron el 06/11/2026. Se fija la edición o fecha cuando
está disponible; una URL de versión actual puede cambiar después de esta consulta.

- ISO: [catálogo de ISO/IEC 25010:2023][iso2023]; [antecedente terminológico oficial de 2011][iso2011].
- GSF: [carbono][gsf-carbon], [energía][gsf-energy], [hardware][gsf-hardware], [medición][gsf-measurement] y [SCI v1.1.0][sci].
- W3C: [nota borrador de 16/10/2026][wsg] y [borrador editorial consultado][wsg-editor].
- [Metodología SWDM v4][swdm].
- Principios de ingeniería: [SRP][srp], [DRY][dry] y [YAGNI][yagni].

[iso2023]: https://www.iso.org/standard/78176.html
[iso2011]: https://www.iso.org/obp/ui/?_escaped_fragment_=iso%3Astd%3Aiso-iec%3A25010%3Aed-1%3Av1%3Aen
[gsf-carbon]: https://learn.greensoftware.foundation/carbon-efficiency/
[gsf-energy]: https://learn.greensoftware.foundation/energy-efficiency/
[gsf-hardware]: https://learn.greensoftware.foundation/hardware-efficiency/
[gsf-measurement]: https://learn.greensoftware.foundation/measurement/
[sci]: https://sci.greensoftware.foundation/
[wsg]: https://www.w3.org/TR/2026/DNOTE-web-sustainability-guidelines-20261016/
[wsg-editor]: https://w3c.github.io/sustainableweb-wsg/
[swdm]: https://sustainablewebdesign.org/estimating-digital-emissions/
[srp]: https://blog.cleancoder.com/uncle-bob/2014/05/08/SingleReponsibilityPrinciple.html
[dry]: https://pragprog.com/tips/
[yagni]: https://martinfowler.com/bliki/Yagni.html

## 9. Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 0.1.0 | 06/11/2026 | Marco de estándares verificado, guía adaptada y matriz preliminar del flujo. Pendientes las ocho optimizaciones individuales y la evidencia DESPUÉS. |
| 0.2.0 | 06/11/2026 | Matriz de ocho optimizaciones confirmadas por Frank y equivalencias WSG verificadas; ECL-114 separado como criterio 3. Evidencia DESPUÉS pendiente, contenido en BORRADOR. |

[Índice del Sprint 4](<../Sprint 04/README.md>) ·
[← Volver al README principal](../../../README.md)
