# Transformando a ágil — EcoLogística Lima

| Metadato | Valor |
|---|---|
| Proyecto | EcoLogística Lima — Optimizador de Rutas Sostenibles para DistriRápido S.A.C. |
| Versión | 1.0.0 |
| Fecha | 10/09/2026 |
| Base documental | RF V_1_0_0; RNF V_1_1_0; reglas de negocio V_1_0_0; configuración Jira ECL |

## 1. Objetivo de la transformación

Transformar la línea base de requisitos en un **Product Backlog ágil, trazable y verificable**, manteniendo la relación entre requisitos, Épicas, Historias de Usuario, Enablers, criterios BDD, Story Points, componentes y responsables. Los RF se descomponen jerárquicamente en Épicas e Historias; los RNF se materializan como Enablers o como controles transversales del Definition of Done.

## 2. Metodología aplicada

1. Cada RF atómico se asigna a una Épica de negocio y a una Historia de Usuario con formato `Como / quiero / para`.
2. Cada RNF se asigna a un Enabler técnico medible o se incorpora como restricción transversal del DoD.
3. Toda Historia y Enabler contiene al menos dos escenarios BDD `Dado / Cuando / Entonces`.
4. La estimación usa Fibonacci `1, 2, 3, 5, 8, 13`; la prioridad combina valor de negocio, dependencia y riesgo técnico.
5. La jerarquía operativa en Jira es `Epic → Historia/Enabler → Subtarea`, donde las subtareas del Sprint no superan 8 horas.

## 3. Épicas del producto

| ID | Jira | Épica | Componente principal | Responsable | Inicio | Fin | Trazabilidad |
|---|---|---|---|---|---|---|---|
| EP-01 | ECL-1 | Gestión de Acceso y Seguridad | Seguridad y Acceso | Antony Munive Ríos | 2026-09-11 | 2026-10-02 | RF-001; RNF-003, RNF-004 |
| EP-02 | ECL-2 | Gestión Operativa Logística | Gestión Operativa | Frank Roy Yupanqui Acevedo | 2026-09-11 | 2026-10-16 | RF-002, RF-003, RF-004, RF-005 |
| EP-03 | ECL-3 | Optimización Sostenible de Rutas | Optimización | Antony Munive Ríos | 2026-09-25 | 2026-11-13 | RF-006; RNF-001, RNF-002, RNF-011 |
| EP-04 | ECL-4 | Operación, Seguimiento e Incidencias | Seguimiento y Mapas | José Samuel Delgadillo Pantoja | 2026-10-09 | 2026-11-27 | RF-007, RF-008, RF-012; RNF-005, RNF-006, RNF-009 |
| EP-05 | ECL-5 | Analítica, Reportes y Sostenibilidad | Analítica y Sostenibilidad | Giancarlo Marcio Soto Escobar | 2026-10-23 | 2026-12-04 | RF-009, RF-010, RF-011; RNF-011, RNF-012 |
| EP-06 | ECL-6 | Plataforma, Calidad y Entrega Continua | Plataforma / DevOps | Julio Armando Naupari Camarena | 2026-09-11 | 2026-12-04 | RNF-007, RNF-008, RNF-010, RNF-012, RNF-013; DoD |

## 4. Mapeo RF → Épica → Historia de Usuario

| RF | Épica | Historia | Jira | SP | Prioridad | Componente |
|---|---|---|---|---:|---|---|
| RF-001 | EP-01 | US-001 — Autenticarse y acceder según rol | ECL-7 | 3 | Alta | Seguridad y Acceso |
| RF-002 | EP-02 | US-002 — Gestionar vehículos de la flota | ECL-8 | 5 | Alta | Gestión Operativa |
| RF-003 | EP-02 | US-003 — Gestionar conductores y disponibilidad | ECL-9 | 5 | Alta | Gestión Operativa |
| RF-004 | EP-02 | US-004 — Registrar y validar pedidos | ECL-10 | 5 | Alta | Gestión Operativa |
| RF-005 | EP-02 | US-005 — Gestionar preferencias de entrega de clientes | ECL-11 | 3 | Media | Gestión Operativa |
| RF-006 | EP-03 | US-006 — Generar rutas optimizadas sostenibles | ECL-12 | 13 | Alta | Optimización |
| RF-007 | EP-04 | US-007 — Reoptimizar rutas ante incidencias | ECL-13 | 8 | Alta | Seguimiento y Mapas |
| RF-008 | EP-04 | US-008 — Visualizar rutas y alertas en mapa | ECL-14 | 8 | Alta | Seguimiento y Mapas |
| RF-009 | EP-05 | US-009 — Consultar dashboard de operación y sostenibilidad | ECL-15 | 5 | Alta | Analítica y Sostenibilidad |
| RF-010 | EP-05 | US-010 — Descargar reporte de sostenibilidad | ECL-16 | 5 | Alta | Analítica y Sostenibilidad |
| RF-011 | EP-05 | US-011 — Proponer compensación de carbono | ECL-17 | 3 | Media | Analítica y Sostenibilidad |
| RF-012 | EP-04 | US-012 — Registrar incidencias de operación y seguridad vial | ECL-18 | 5 | Media | Seguimiento y Mapas |

## 5. Mapeo RNF → Enabler / control transversal

| RNF / control | Enabler | Jira | SP | Tratamiento |
|---|---|---|---:|---|
| RNF-013 | EN-001 — Preparar arquitectura reproducible de la plataforma | ECL-19 | 5 | Trabajo técnico verificable con BDD y DoD global. |
| RNF-003, RNF-004 | EN-002 — Implementar seguridad OWASP y control RBAC | ECL-20 | 5 | Trabajo técnico verificable con BDD y DoD global. |
| RNF-001, RNF-002; soporte a RF-006 y RF-007 | EN-003 — Desacoplar optimización y automatizar pruebas de rendimiento | ECL-21 | 8 | Trabajo técnico verificable con BDD y DoD global. |
| RNF-005, RNF-006, RNF-009 | EN-004 — Implementar experiencia accesible, responsive y tolerante a desconexión | ECL-22 | 8 | Trabajo técnico verificable con BDD y DoD global. |
| RNF-007, RNF-008 | EN-005 — Preparar capacidad, disponibilidad y observabilidad | ECL-23 | 8 | Trabajo técnico verificable con BDD y DoD global. |
| RNF-010 y Definition of Done global | EN-006 — Configurar CI/CD y puertas de calidad | ECL-24 | 5 | Trabajo técnico verificable con BDD y DoD global. |
| RNF-012 | EN-007 — Optimizar transferencia de datos y consultas | ECL-25 | 3 | Trabajo técnico verificable con BDD y DoD global. |
| RNF-011 | EN-008 — Versionar parámetros y validar exactitud de cálculos | ECL-26 | 5 | Trabajo técnico verificable con BDD y DoD global. |

> **Alineamiento de cobertura:** RNF-010 fue actualizado en `V_1_1_0` para que la cobertura mínima de pruebas unitarias sea **≥80%**, eliminando la inconsistencia previa con el Definition of Done exigido para esta fase.

## 6. Historias de Usuario

### US-001 — Autenticarse y acceder según rol

- **Jira:** ECL-7
- **Épica:** EP-01
- **Trazabilidad:** RF-001; RNF-003, RNF-004
- **Story Points:** 3
- **Prioridad:** Alta
- **Componente:** Seguridad y Acceso
- **Responsable:** Antony Munive Ríos

**Como** usuario autorizado, **quiero** autenticarme y acceder únicamente a las capacidades asignadas a mi rol, **para** operar o consultar EcoLogística Lima sin exponer información ni funciones no autorizadas.

**Criterios de aceptación BDD**

**Escenario: Acceso válido**
- **Dado** un usuario activo con rol autorizado.
- **Cuando** ingresa credenciales válidas.
- **Entonces** accede a las funciones permitidas por su rol y el inicio de sesión queda registrado.

**Escenario: Credenciales inválidas**
- **Dado** un usuario presenta credenciales inválidas.
- **Cuando** intenta iniciar sesión.
- **Entonces** el sistema deniega el acceso sin revelar cuál credencial fue incorrecta.

**Escenario: Restricción por rol**
- **Dado** un usuario autenticado carece de permiso de edición.
- **Cuando** intenta modificar información protegida.
- **Entonces** el sistema rechaza la operación y conserva los datos sin cambios.

### US-002 — Gestionar vehículos de la flota

- **Jira:** ECL-8
- **Épica:** EP-02
- **Trazabilidad:** RF-002
- **Story Points:** 5
- **Prioridad:** Alta
- **Componente:** Gestión Operativa
- **Responsable:** José Samuel Delgadillo Pantoja

**Como** Administrador, **quiero** registrar y mantener vehículos con sus atributos operativos y ambientales, **para** disponer de recursos válidos para la planificación sostenible de rutas.

**Criterios de aceptación BDD**

**Escenario: Registro válido**
- **Dado** un Administrador autenticado.
- **Cuando** registra un vehículo con campos obligatorios válidos y placa única.
- **Entonces** el vehículo queda disponible para planificación.

**Escenario: Validación de datos**
- **Dado** una placa está duplicada o la capacidad no es positiva.
- **Cuando** se intenta guardar el vehículo.
- **Entonces** el sistema rechaza el registro e identifica el campo inválido.

**Escenario: Actualización auditada**
- **Dado** existe un vehículo registrado.
- **Cuando** el Administrador actualiza consumo o factor de emisión.
- **Entonces** los cálculos futuros usan el nuevo valor y la modificación queda auditada.

### US-003 — Gestionar conductores y disponibilidad

- **Jira:** ECL-9
- **Épica:** EP-02
- **Trazabilidad:** RF-003
- **Story Points:** 5
- **Prioridad:** Alta
- **Componente:** Gestión Operativa
- **Responsable:** Frank Roy Yupanqui Acevedo

**Como** Administrador u Operador autorizado, **quiero** registrar y mantener conductores con licencia, disponibilidad y punto de partida, **para** asignar únicamente recursos aptos a las rutas.

**Criterios de aceptación BDD**

**Escenario: Conductor habilitado**
- **Dado** un Administrador registra un conductor con licencia vigente y disponibilidad válida.
- **Cuando** guarda el registro.
- **Entonces** el conductor queda habilitado para asignación.

**Escenario: Licencia vencida**
- **Dado** un conductor tiene licencia vencida.
- **Cuando** se intenta habilitarlo para una ruta.
- **Entonces** el sistema impide la asignación e informa la restricción.

**Escenario: Cambio de disponibilidad**
- **Dado** un conductor habilitado modifica su franja disponible.
- **Cuando** el Operador actualiza la disponibilidad.
- **Entonces** la nueva franja se considera en planificaciones posteriores.

### US-004 — Registrar y validar pedidos

- **Jira:** ECL-10
- **Épica:** EP-02
- **Trazabilidad:** RF-004
- **Story Points:** 5
- **Prioridad:** Alta
- **Componente:** Gestión Operativa
- **Responsable:** Frank Roy Yupanqui Acevedo

**Como** Operador de despacho, **quiero** registrar pedidos con ubicación, peso, volumen, ventana horaria, prioridad y tipo de producto, **para** incorporarlos correctamente a la planificación de reparto.

**Criterios de aceptación BDD**

**Escenario: Pedido válido**
- **Dado** un Operador autenticado.
- **Cuando** registra un pedido con ubicación y ventana válidas.
- **Entonces** el pedido queda pendiente de planificación.

**Escenario: Dirección no estandarizada**
- **Dado** una dirección de Lima Este no tiene nomenclatura estándar.
- **Cuando** se registran coordenadas y un punto de referencia.
- **Entonces** el pedido queda utilizable por el optimizador.

**Escenario: Ventana inválida**
- **Dado** la hora final es anterior a la hora inicial.
- **Cuando** se intenta guardar el pedido.
- **Entonces** el sistema rechaza el registro e indica el dato a corregir.

### US-005 — Gestionar preferencias de entrega de clientes

- **Jira:** ECL-11
- **Épica:** EP-02
- **Trazabilidad:** RF-005
- **Story Points:** 3
- **Prioridad:** Media
- **Componente:** Gestión Operativa
- **Responsable:** Frank Roy Yupanqui Acevedo

**Como** Operador de despacho, **quiero** registrar horarios preferidos, puntos de referencia y restricciones de acceso de clientes, **para** contextualizar futuros pedidos y reducir fallos de entrega.

**Criterios de aceptación BDD**

**Escenario: Preferencia válida**
- **Dado** existe un cliente.
- **Cuando** el Operador registra una preferencia válida.
- **Entonces** la preferencia queda asociada al cliente y puede utilizarse en pedidos futuros.

**Escenario: Preferencia inconsistente**
- **Dado** una preferencia contiene datos incompatibles o incompletos.
- **Cuando** se intenta guardar.
- **Entonces** el sistema solicita corrección y no persiste información inválida.

### US-006 — Generar rutas optimizadas sostenibles

- **Jira:** ECL-12
- **Épica:** EP-03
- **Trazabilidad:** RF-006; RNF-001, RNF-011
- **Story Points:** 13
- **Prioridad:** Alta
- **Componente:** Optimización
- **Responsable:** Antony Munive Ríos

**Como** Operador de despacho, **quiero** generar rutas factibles considerando capacidad, ventanas, jornada, descansos, distancia, costo, emisiones y restricciones, **para** reducir recorrido, tardanzas, consumo y CO₂ frente a una planificación secuencial.

**Criterios de aceptación BDD**

**Escenario: Optimización válida**
- **Dado** existen hasta 150 pedidos válidos y 15 vehículos disponibles.
- **Cuando** el Operador solicita la optimización.
- **Entonces** obtiene rutas factibles, métricas comparativas y pedidos no asignados con causa.

**Escenario: Restricciones obligatorias**
- **Dado** los pedidos presentan capacidades y ventanas distintas.
- **Cuando** se genera la solución.
- **Entonces** ninguna ruta viola las restricciones duras configuradas.

**Escenario: Pedido inviable**
- **Dado** un pedido excede la capacidad de toda la flota.
- **Cuando** se optimiza.
- **Entonces** el pedido queda no asignado con motivo explícito sin invalidar el resto de la solución.

### US-007 — Reoptimizar rutas ante incidencias

- **Jira:** ECL-13
- **Épica:** EP-04
- **Trazabilidad:** RF-007; RNF-002
- **Story Points:** 8
- **Prioridad:** Alta
- **Componente:** Seguimiento y Mapas
- **Responsable:** Antony Munive Ríos

**Como** Operador de despacho, **quiero** recalcular rutas y paradas pendientes ante pedidos nuevos, cancelaciones, accidentes o averías, **para** mantener la operación viable sin perder el progreso ya ejecutado.

**Criterios de aceptación BDD**

**Escenario: Avería durante jornada**
- **Dado** una jornada está en curso.
- **Cuando** se registra una avería validada.
- **Entonces** el vehículo afectado se excluye y se proponen rutas para las paradas pendientes.

**Escenario: Pedido urgente**
- **Dado** la operación está en curso y se incorpora un pedido priorizado.
- **Cuando** el Operador solicita reoptimización.
- **Entonces** se recalculan únicamente las entregas pendientes respetando lo ya ejecutado.

**Escenario: Sin alternativa factible**
- **Dado** no existe una alternativa factible.
- **Cuando** finaliza el recálculo.
- **Entonces** el sistema identifica las entregas afectadas y explica la causa.

### US-008 — Visualizar rutas y alertas en mapa

- **Jira:** ECL-14
- **Épica:** EP-04
- **Trazabilidad:** RF-008; RNF-009
- **Story Points:** 8
- **Prioridad:** Alta
- **Componente:** Seguimiento y Mapas
- **Responsable:** Giancarlo Marcio Soto Escobar

**Como** Operador de despacho, **quiero** visualizar rutas, paradas, tiempos estimados, congestión y alertas en un mapa interactivo, **para** monitorear la operación y tomar decisiones informadas.

**Criterios de aceptación BDD**

**Escenario: Visualización de ruta**
- **Dado** existe una solución generada.
- **Cuando** el Operador abre una ruta.
- **Entonces** visualiza el trazado y la secuencia de paradas en el mapa.

**Escenario: Fuente de tráfico no disponible**
- **Dado** la fuente de tráfico no responde.
- **Cuando** se abre el mapa.
- **Entonces** se muestra el último dato disponible con su hora y una advertencia de degradación.

### US-009 — Consultar dashboard de operación y sostenibilidad

- **Jira:** ECL-15
- **Épica:** EP-05
- **Trazabilidad:** RF-009; RNF-011, RNF-012
- **Story Points:** 5
- **Prioridad:** Alta
- **Componente:** Analítica y Sostenibilidad
- **Responsable:** Giancarlo Marcio Soto Escobar

**Como** Analista de sostenibilidad u Operador autorizado, **quiero** consultar distancia, CO₂, combustible ahorrado, cumplimiento de ventanas y ahorro por periodo, **para** evaluar el desempeño económico y ambiental de la operación.

**Criterios de aceptación BDD**

**Escenario: Periodo con resultados**
- **Dado** un periodo contiene rutas cerradas.
- **Cuando** el usuario consulta el dashboard.
- **Entonces** se muestran los indicadores con unidades y periodo aplicado.

**Escenario: Periodo sin datos**
- **Dado** no existen rutas cerradas en el periodo.
- **Cuando** se consulta el dashboard.
- **Entonces** se muestra un estado sin datos y no se inventan valores.

### US-010 — Descargar reporte de sostenibilidad

- **Jira:** ECL-16
- **Épica:** EP-05
- **Trazabilidad:** RF-010; RNF-011, RNF-013
- **Story Points:** 5
- **Prioridad:** Alta
- **Componente:** Analítica y Sostenibilidad
- **Responsable:** José Samuel Delgadillo Pantoja

**Como** Analista de sostenibilidad, **quiero** descargar un reporte PDF con emisiones, costos, ahorro y cumplimiento de metas, **para** evidenciar resultados económicos y ambientales de un periodo.

**Criterios de aceptación BDD**

**Escenario: Reporte con resultados**
- **Dado** existe un periodo con resultados.
- **Cuando** un usuario autorizado solicita el reporte.
- **Entonces** descarga un PDF con fecha, filtros y parámetros utilizados.

**Escenario: Periodo sin resultados**
- **Dado** el periodo no contiene resultados.
- **Cuando** se solicita el reporte.
- **Entonces** el sistema informa que no existe información suficiente para generarlo.

### US-011 — Proponer compensación de carbono

- **Jira:** ECL-17
- **Épica:** EP-05
- **Trazabilidad:** RF-011
- **Story Points:** 3
- **Prioridad:** Media
- **Componente:** Analítica y Sostenibilidad
- **Responsable:** Frank Roy Yupanqui Acevedo

**Como** Analista de sostenibilidad, **quiero** calcular emisiones netas y obtener una propuesta de compensación según parámetros vigentes, **para** planificar acciones ambientales con información trazable.

**Criterios de aceptación BDD**

**Escenario: Factor vigente disponible**
- **Dado** existe un factor de captura vigente.
- **Cuando** se consultan las emisiones del periodo.
- **Entonces** el sistema muestra cálculo, factor utilizado, fecha y propuesta de compensación.

**Escenario: Factor no configurado**
- **Dado** falta el factor de captura requerido.
- **Cuando** se solicita la propuesta.
- **Entonces** el sistema no publica una equivalencia y solicita configurar el parámetro.

### US-012 — Registrar incidencias de operación y seguridad vial

- **Jira:** ECL-18
- **Épica:** EP-04
- **Trazabilidad:** RF-012; RNF-006
- **Story Points:** 5
- **Prioridad:** Media
- **Componente:** Seguimiento y Mapas
- **Responsable:** José Samuel Delgadillo Pantoja

**Como** Conductor, **quiero** registrar una incidencia con tipo, ubicación, hora, severidad y observación, **para** informar a Operación y permitir que la situación sea considerada en la planificación o reoptimización.

**Criterios de aceptación BDD**

**Escenario: Incidencia válida**
- **Dado** un Conductor está autenticado.
- **Cuando** reporta una incidencia con ubicación y tipo.
- **Entonces** la incidencia queda registrada y visible para Operación.

**Escenario: Sin conectividad**
- **Dado** existe una ruta previamente cargada y no hay red.
- **Cuando** el Conductor registra una incidencia.
- **Entonces** el sistema conserva el reporte pendiente y lo sincroniza al recuperar conectividad.

## 7. Enablers / Historias Técnicas

### EN-001 — Preparar arquitectura reproducible de la plataforma

- **Jira:** ECL-19
- **Épica:** EP-06
- **Trazabilidad:** RNF-013
- **Story Points:** 5
- **Prioridad:** Alta
- **Componente:** Plataforma / DevOps
- **Responsable:** Julio Armando Naupari Camarena

**Objetivo técnico:** Establecer la base reproducible de React + TypeScript + FastAPI + PostgreSQL/PostGIS + Redis, con configuración externa, contenedores y documentación de arranque.

**Criterios de aceptación BDD**

**Escenario: Arranque reproducible**
- **Dado** un integrante dispone de un equipo limpio con las dependencias documentadas.
- **Cuando** sigue el README de instalación.
- **Entonces** puede levantar los servicios y acceder a la aplicación y OpenAPI sin configuración implícita.

**Escenario: Configuración externa**
- **Dado** se prepara un entorno diferente.
- **Cuando** se proporcionan las variables documentadas.
- **Entonces** los servicios arrancan sin secretos codificados en el repositorio.

### EN-002 — Implementar seguridad OWASP y control RBAC

- **Jira:** ECL-20
- **Épica:** EP-01
- **Trazabilidad:** RNF-003, RNF-004
- **Story Points:** 5
- **Prioridad:** Alta
- **Componente:** Seguridad y Acceso
- **Responsable:** Antony Munive Ríos

**Objetivo técnico:** Implementar controles de autenticación/autorización, validación de entradas, mínimo privilegio, auditoría y controles OWASP relevantes.

**Criterios de aceptación BDD**

**Escenario: Acceso no autorizado**
- **Dado** un usuario carece de permiso para una operación.
- **Cuando** intenta ejecutar un endpoint protegido.
- **Entonces** la API rechaza la solicitud, conserva los datos y registra el evento.

**Escenario: Exposición mínima de datos**
- **Dado** un usuario tiene acceso limitado.
- **Cuando** consulta información personal restringida.
- **Entonces** recibe únicamente los campos permitidos por su rol y contexto.

### EN-003 — Desacoplar optimización y automatizar pruebas de rendimiento

- **Jira:** ECL-21
- **Épica:** EP-03
- **Trazabilidad:** RNF-001, RNF-002; soporte a RF-006 y RF-007
- **Story Points:** 8
- **Prioridad:** Alta
- **Componente:** Optimización
- **Responsable:** Antony Munive Ríos

**Objetivo técnico:** Ejecutar la optimización mediante cola/worker y disponer de un benchmark reproducible para optimización y reoptimización.

**Criterios de aceptación BDD**

**Escenario: Optimización encolada**
- **Dado** existe una solicitud válida de optimización.
- **Cuando** la API la acepta.
- **Entonces** crea una ejecución reproducible, la encola y permite consultar su estado sin bloquear la API.

**Escenario: Benchmark reproducible**
- **Dado** se dispone de conjuntos de prueba y semilla controlados.
- **Cuando** se ejecutan las corridas definidas.
- **Entonces** se registran tiempos suficientes para verificar P95 ≤45 s en optimización y P95 ≤30 s en reoptimización.

### EN-004 — Implementar experiencia accesible, responsive y tolerante a desconexión

- **Jira:** ECL-22
- **Épica:** EP-04
- **Trazabilidad:** RNF-005, RNF-006, RNF-009
- **Story Points:** 8
- **Prioridad:** Alta
- **Componente:** Seguimiento y Mapas
- **Responsable:** Giancarlo Marcio Soto Escobar

**Objetivo técnico:** Construir la experiencia móvil del conductor con WCAG 2.1 AA, compatibilidad con Chrome/Firefox y conservación del último itinerario ante pérdida de conectividad.

**Criterios de aceptación BDD**

**Escenario: Uso móvil accesible**
- **Dado** un Conductor usa un dispositivo de 360 px.
- **Cuando** consulta su ruta.
- **Entonces** visualiza siguiente parada y alertas sin desplazamiento horizontal y con los criterios de accesibilidad definidos.

**Escenario: Pérdida y recuperación de red**
- **Dado** existe una ruta previamente cargada.
- **Cuando** el dispositivo pierde conectividad y luego la recupera.
- **Entonces** conserva el último itinerario y sincroniza los reportes pendientes.

### EN-005 — Preparar capacidad, disponibilidad y observabilidad

- **Jira:** ECL-23
- **Épica:** EP-06
- **Trazabilidad:** RNF-007, RNF-008
- **Story Points:** 8
- **Prioridad:** Alta
- **Componente:** Plataforma / DevOps
- **Responsable:** Julio Armando Naupari Camarena

**Objetivo técnico:** Instrumentar métricas y pruebas de capacidad para API y base de datos y verificar el SLA operativo.

**Criterios de aceptación BDD**

**Escenario: Prueba de capacidad**
- **Dado** se simula una carga representativa de 1,000 pedidos diarios, 50 vehículos y 100 solicitudes concurrentes.
- **Cuando** se ejecuta la prueba documentada.
- **Entonces** el registro de pedidos mantiene P95 ≤2 s y errores 5xx <1%.

**Escenario: Monitoreo de disponibilidad**
- **Dado** la plataforma está desplegada en ambiente de prueba.
- **Cuando** se observa su operación.
- **Entonces** se registran disponibilidad, errores y latencias suficientes para calcular el SLA objetivo de ≥99.5% entre 05:00 y 22:00.

### EN-006 — Configurar CI/CD y puertas de calidad

- **Jira:** ECL-24
- **Épica:** EP-06
- **Trazabilidad:** RNF-010 y Definition of Done global
- **Story Points:** 5
- **Prioridad:** Alta
- **Componente:** Plataforma / DevOps
- **Responsable:** José Samuel Delgadillo Pantoja

**Objetivo técnico:** Configurar integración continua, pruebas automáticas, cobertura, análisis estático y controles previos a integración.

**Criterios de aceptación BDD**

**Escenario: Pull Request con controles**
- **Dado** se propone un cambio mediante Pull Request.
- **Cuando** se ejecuta el pipeline.
- **Entonces** se ejecutan pruebas y análisis estático antes de permitir la integración.

**Escenario: Incumplimiento de calidad**
- **Dado** un cambio introduce una vulnerabilidad crítica o falla las pruebas obligatorias.
- **Cuando** finaliza el pipeline.
- **Entonces** la integración queda bloqueada e identifica el control incumplido.

### EN-007 — Optimizar transferencia de datos y consultas

- **Jira:** ECL-25
- **Épica:** EP-06
- **Trazabilidad:** RNF-012
- **Story Points:** 3
- **Prioridad:** Media
- **Componente:** Plataforma / DevOps
- **Responsable:** Antony Munive Ríos

**Objetivo técnico:** Aplicar prácticas de Green Software mediante respuestas agregadas, paginación, compresión, caché e índices revisados.

**Criterios de aceptación BDD**

**Escenario: Payload del dashboard**
- **Dado** se realiza una consulta normal del dashboard.
- **Cuando** la API devuelve indicadores agregados.
- **Entonces** la respuesta no supera 250 KB sin incluir datos del mapa.

**Escenario: Consultas críticas**
- **Dado** se revisan las consultas de pedidos, rutas y dashboard.
- **Cuando** se inspecciona su plan de ejecución.
- **Entonces** cuentan con índices o justificación documentada y no transfieren datos innecesarios.

### EN-008 — Versionar parámetros y validar exactitud de cálculos

- **Jira:** ECL-26
- **Épica:** EP-05
- **Trazabilidad:** RNF-011
- **Story Points:** 5
- **Prioridad:** Alta
- **Componente:** Analítica y Sostenibilidad
- **Responsable:** Antony Munive Ríos

**Objetivo técnico:** Implementar parámetros versionados con fuente y vigencia para combustible, mantenimiento, factores de emisión y compensación.

**Criterios de aceptación BDD**

**Escenario: Cálculo reproducible**
- **Dado** existe un conjunto de parámetros vigente.
- **Cuando** se calculan CO₂ y costos para una ruta.
- **Entonces** el resultado conserva la versión de parámetros utilizada y puede reproducirse posteriormente.

**Escenario: Validación contra referencia**
- **Dado** existen casos de referencia documentados.
- **Cuando** el sistema ejecuta los mismos cálculos.
- **Entonces** la diferencia absoluta de cada resultado es ≤0.01 respecto de la referencia.

## 8. Definition of Done (DoD) global

Una Historia de Usuario o Enabler solo puede pasar a **Done** cuando cumple simultáneamente los siguientes criterios:

- Cobertura de pruebas unitarias **≥80%** para el incremento afectado y pruebas obligatorias en verde.
- Análisis estático/SAST ejecutado mediante **SonarQube y/o CodeQL**, sin vulnerabilidades críticas abiertas.
- Pull Request aprobado mediante **Peer Review por al menos un par técnico** distinto del autor.
- Despliegue automatizado ejecutable en ambiente de **Staging / Pruebas**.
- Documentación técnica, README y **OpenAPI/Swagger** actualizados cuando el cambio afecte API, configuración o arquitectura.
- Criterios BDD de la Historia/Enabler aprobados y evidencia adjunta o referenciada.
- Sin defectos bloqueantes asociados y con trazabilidad a RF/RNF, Épica y versión `v1.0.0-MVP`.

## 9. Trazabilidad y control de cambios

Durante la planificación se detectaron dos inconsistencias de la línea base: el presupuesto del Acta V_1_0_0 no coincidía con la restricción oficial del proyecto y RNF-010 definía 70% de cobertura frente al 80% exigido por el DoD. Por control de cambios se conservaron los originales y se generaron versiones `V_1_1_0` corregidas.

### Fuentes internas del repositorio

- `docs/01. Inicio/06. Requisitos funcionales V_1_0_0.md`
- `docs/01. Inicio/07. Requisitos no funcionales V_1_1_0.md`
- `docs/01. Inicio/09. Reglas de negocio V_1_0_0.md`
- `docs/01. Inicio/12. Modelo C4 V_1_0_0.md`

[← Volver al README Principal](../../README.md)
