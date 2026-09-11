# Artefactos Jira — EcoLogística Lima

| Metadato | Valor |
|---|---|
| Proyecto Jira | EcoLogística Lima (`ECL`) |
| Tipo de proyecto | Company-managed Software |
| Board | `ECL board` — Scrum, Board ID 3 |
| Versión | 1.0.0 |
| Fecha | 10/09/2026 |

## 1. Configuración operativa validada

La configuración del proyecto fue validada directamente en Jira y utiliza el campo **Story Points** como métrica de estimación del Board. El backlog ejecutable contiene **12 Historias (68 SP) + 8 Enablers (47 SP) = 115 SP**.

### Jerarquía de trabajo

| Tipo Jira | Uso en EcoLogística Lima | Regla |
|---|---|---|
| Epic | Módulo o bloque funcional mayor | Contiene Historias o Enablers relacionados. |
| Historia | Funcionalidad con valor para usuario final | Formato Como/quiero/para + BDD. |
| Tarea | Enabler técnico | Arquitectura, seguridad, DevOps, rendimiento o datos. |
| Subtarea | Unidad técnica del Sprint | Duración máxima ≤8 h. |
| Error | Incidencia/defecto | Se registra durante o al cierre de un Sprint. |

### Componentes

| Componente | Alcance |
|---|---|
| Seguridad y Acceso | Autenticación, autorización, RBAC y protección de datos. |
| Gestión Operativa | Flota, conductores, pedidos y clientes. |
| Optimización | VRPTW / Green VRP, worker y benchmarks. |
| Seguimiento y Mapas | Mapa, incidencias, reoptimización y experiencia de conductor. |
| Analítica y Sostenibilidad | Dashboard, reportes, carbono y parámetros. |
| Plataforma / DevOps | Arquitectura, CI/CD, capacidad, observabilidad y Green Software. |

## 2. Product Backlog priorizado

El ranking se definió por dependencia técnica, riesgo y valor de negocio. El orden actual en Jira es:

| Rank | Jira | Elemento | Tipo | SP | Prioridad | Componente | Responsable |
|---:|---|---|---|---:|---|---|---|
| 1 | ECL-19 | EN-001 — Preparar arquitectura reproducible de la plataforma | Enabler | 5 | Alta | Plataforma / DevOps | Julio Armando Naupari Camarena |
| 2 | ECL-20 | EN-002 — Implementar seguridad OWASP y control RBAC | Enabler | 5 | Alta | Seguridad y Acceso | Antony Munive Ríos |
| 3 | ECL-24 | EN-006 — Configurar CI/CD y puertas de calidad | Enabler | 5 | Alta | Plataforma / DevOps | José Samuel Delgadillo Pantoja |
| 4 | ECL-7 | US-001 — Autenticarse y acceder según rol | Historia | 3 | Alta | Seguridad y Acceso | Antony Munive Ríos |
| 5 | ECL-8 | US-002 — Gestionar vehículos de la flota | Historia | 5 | Alta | Gestión Operativa | José Samuel Delgadillo Pantoja |
| 6 | ECL-10 | US-004 — Registrar y validar pedidos | Historia | 5 | Alta | Gestión Operativa | Frank Roy Yupanqui Acevedo |
| 7 | ECL-9 | US-003 — Gestionar conductores y disponibilidad | Historia | 5 | Alta | Gestión Operativa | Frank Roy Yupanqui Acevedo |
| 8 | ECL-11 | US-005 — Gestionar preferencias de entrega de clientes | Historia | 3 | Media | Gestión Operativa | Frank Roy Yupanqui Acevedo |
| 9 | ECL-21 | EN-003 — Desacoplar optimización y automatizar pruebas de rendimiento | Enabler | 8 | Alta | Optimización | Antony Munive Ríos |
| 10 | ECL-12 | US-006 — Generar rutas optimizadas sostenibles | Historia | 13 | Alta | Optimización | Antony Munive Ríos |
| 11 | ECL-23 | EN-005 — Preparar capacidad, disponibilidad y observabilidad | Enabler | 8 | Alta | Plataforma / DevOps | Julio Armando Naupari Camarena |
| 12 | ECL-18 | US-012 — Registrar incidencias de operación y seguridad vial | Historia | 5 | Media | Seguimiento y Mapas | José Samuel Delgadillo Pantoja |
| 13 | ECL-22 | EN-004 — Implementar experiencia accesible, responsive y tolerante a desconexión | Enabler | 8 | Alta | Seguimiento y Mapas | Giancarlo Marcio Soto Escobar |
| 14 | ECL-13 | US-007 — Reoptimizar rutas ante incidencias | Historia | 8 | Alta | Seguimiento y Mapas | Antony Munive Ríos |
| 15 | ECL-14 | US-008 — Visualizar rutas y alertas en mapa | Historia | 8 | Alta | Seguimiento y Mapas | Giancarlo Marcio Soto Escobar |
| 16 | ECL-26 | EN-008 — Versionar parámetros y validar exactitud de cálculos | Enabler | 5 | Alta | Analítica y Sostenibilidad | Antony Munive Ríos |
| 17 | ECL-25 | EN-007 — Optimizar transferencia de datos y consultas | Enabler | 3 | Media | Plataforma / DevOps | Antony Munive Ríos |
| 18 | ECL-15 | US-009 — Consultar dashboard de operación y sostenibilidad | Historia | 5 | Alta | Analítica y Sostenibilidad | Giancarlo Marcio Soto Escobar |
| 19 | ECL-16 | US-010 — Descargar reporte de sostenibilidad | Historia | 5 | Alta | Analítica y Sostenibilidad | José Samuel Delgadillo Pantoja |
| 20 | ECL-17 | US-011 — Proponer compensación de carbono | Historia | 3 | Media | Analítica y Sostenibilidad | Frank Roy Yupanqui Acevedo |

## 3. Roadmap de Épicas

| Épica | Jira | Responsable | Inicio | Fin | Resultado esperado |
|---|---|---|---|---|---|
| EP-01 — Gestión de Acceso y Seguridad | ECL-1 | Antony Munive Ríos | 2026-09-11 | 2026-10-02 | Acceso y controles de seguridad habilitados. |
| EP-02 — Gestión Operativa Logística | ECL-2 | Frank Roy Yupanqui Acevedo | 2026-09-11 | 2026-10-16 | Datos operativos listos para optimización. |
| EP-03 — Optimización Sostenible de Rutas | ECL-3 | Antony Munive Ríos | 2026-09-25 | 2026-11-13 | Optimización sostenible factible y medible. |
| EP-04 — Operación, Seguimiento e Incidencias | ECL-4 | José Samuel Delgadillo Pantoja | 2026-10-09 | 2026-11-27 | Seguimiento, incidencias y reoptimización operativos. |
| EP-05 — Analítica, Reportes y Sostenibilidad | ECL-5 | Giancarlo Marcio Soto Escobar | 2026-10-23 | 2026-12-04 | Indicadores, reportes y sostenibilidad trazables. |
| EP-06 — Plataforma, Calidad y Entrega Continua | ECL-6 | Julio Armando Naupari Camarena | 2026-09-11 | 2026-12-04 | Base técnica, calidad y entrega continua disponibles. |

## 4. Release

| Campo | Configuración |
|---|---|
| Versión | `v1.0.0-MVP` |
| Inicio | 10/09/2026 |
| Fecha objetivo de release | 04/12/2026 |
| Estado | Unreleased / no archivada |
| Alcance | 20 elementos ejecutables: 12 Historias + 8 Enablers |

La Release consolida gestión operativa, optimización VRPTW/Green VRP, seguimiento en mapa, analítica y controles de calidad del MVP.

## 5. Sprint 1 — Base Operativa

| Campo | Valor |
|---|---|
| Sprint ID | 4 |
| Duración | 2 semanas |
| Inicio | 11/09/2026 09:00 (America/Lima) |
| Fin | 25/09/2026 09:00 (America/Lima) |
| Estado al generar este documento | Future / planificado |

**Sprint Goal:** Establecer una base ejecutable y segura de EcoLogística Lima, habilitando autenticación, gestión inicial de flota y pedidos, y controles de CI/CD necesarios para iniciar la optimización sostenible de rutas.

### Ítems comprometidos

| Jira | Elemento | SP | Responsable |
|---|---|---:|---|
| ECL-19 | EN-001 — Preparar arquitectura reproducible de la plataforma | 5 | Julio Armando Naupari Camarena |
| ECL-20 | EN-002 — Implementar seguridad OWASP y control RBAC | 5 | Antony Munive Ríos |
| ECL-24 | EN-006 — Configurar CI/CD y puertas de calidad | 5 | José Samuel Delgadillo Pantoja |
| ECL-7 | US-001 — Autenticarse y acceder según rol | 3 | Antony Munive Ríos |
| ECL-8 | US-002 — Gestionar vehículos de la flota | 5 | José Samuel Delgadillo Pantoja |
| ECL-10 | US-004 — Registrar y validar pedidos | 5 | Frank Roy Yupanqui Acevedo |
|  | **Total Sprint 1** | **28 SP** |  |

### Subtareas técnicas del Sprint 1

| Jira | Padre | ID | Subtarea | Estimación | Responsable |
|---|---|---|---|---:|---|
| ECL-27 | ECL-19 | ST-001 | Bootstrap backend FastAPI y PostGIS | 6 h | Antony Munive Ríos |
| ECL-28 | ECL-19 | ST-002 | Bootstrap frontend React + TypeScript | 5 h | José Samuel Delgadillo Pantoja |
| ECL-29 | ECL-19 | ST-003 | Dockerizar servicios y documentar arranque | 6 h | Julio Armando Naupari Camarena |
| ECL-30 | ECL-20 | ST-004 | Implementar autenticación y hashing seguro | 6 h | Antony Munive Ríos |
| ECL-31 | ECL-20 | ST-005 | Implementar matriz RBAC y auditoría | 6 h | Antony Munive Ríos |
| ECL-32 | ECL-20 | ST-006 | Diseñar pruebas de seguridad y autorización | 4 h | José Samuel Delgadillo Pantoja |
| ECL-33 | ECL-24 | ST-007 | Configurar pipeline CI en GitHub Actions | 5 h | José Samuel Delgadillo Pantoja |
| ECL-34 | ECL-24 | ST-008 | Configurar cobertura mínima y quality gate | 4 h | José Samuel Delgadillo Pantoja |
| ECL-35 | ECL-24 | ST-009 | Configurar CodeQL/SAST y política de PR | 4 h | Julio Armando Naupari Camarena |
| ECL-36 | ECL-7 | ST-010 | Implementar endpoint de login y sesión | 6 h | Antony Munive Ríos |
| ECL-37 | ECL-7 | ST-011 | Diseñar interfaz de acceso y estados de error | 6 h | Giancarlo Marcio Soto Escobar |
| ECL-38 | ECL-7 | ST-012 | Automatizar pruebas BDD de autenticación | 4 h | José Samuel Delgadillo Pantoja |
| ECL-39 | ECL-8 | ST-013 | Modelar entidad y migración de vehículos | 4 h | Antony Munive Ríos |
| ECL-40 | ECL-8 | ST-014 | Implementar CRUD API de vehículos | 6 h | Antony Munive Ríos |
| ECL-41 | ECL-8 | ST-015 | Implementar formulario y listado de vehículos | 6 h | Giancarlo Marcio Soto Escobar |
| ECL-42 | ECL-10 | ST-016 | Refinar reglas y casos BDD de pedidos | 4 h | Frank Roy Yupanqui Acevedo |
| ECL-43 | ECL-10 | ST-017 | Implementar API y validaciones de pedidos | 6 h | Antony Munive Ríos |
| ECL-44 | ECL-10 | ST-018 | Implementar formulario de registro de pedidos | 6 h | José Samuel Delgadillo Pantoja |

> Todas las subtareas son ≤8 horas, cumpliendo la granularidad definida para el trabajo técnico.

## 6. Board Scrum

El flujo configurado en `ECL board` es:

`To Do → In Progress → In Review / QA → Done`

El Board usa `Story Points (customfield_10037)` para estimación y `Rank` para el orden del backlog.

## 7. Evidencias visuales requeridas

> **Regla de entrega:** las evidencias deben ser capturas reales de Jira y recortarse exclusivamente al panel o contenedor que demuestra el requisito. No incluir escritorio, barra de tareas, pestañas del navegador ni espacio vacío innecesario.

### Evidencia 1 — Roadmap del Proyecto

- **Vista Jira:** Roadmap / Timeline del proyecto ECL.
- **Debe mostrar:** las 6 Épicas, sus nombres y barras de fechas.
- **Recorte:** encabezado temporal + lista de Épicas + barras; excluir navegación del navegador.
- **Archivo final sugerido:** `evidencias-jira/01-roadmap.png`.
<!-- INSERTAR AQUÍ LA CAPTURA REAL: evidencias-jira/01-roadmap.png -->

### Evidencia 2 — Backlog Priorizado

- **Vista Jira:** Backlog de `ECL board`.
- **Debe mostrar:** ranking, Story Points y Componentes. Priorizar en el encuadre los primeros elementos: EN-001, EN-002, EN-006, US-001, US-002 y US-004.
- **Recorte:** contenedor del backlog con columnas/campos visibles; sin barra del navegador.
- **Archivo final sugerido:** `evidencias-jira/02-backlog-priorizado.png`.
<!-- INSERTAR AQUÍ LA CAPTURA REAL: evidencias-jira/02-backlog-priorizado.png -->

### Evidencia 3 — Sprint Planning y Sprint Goal

- **Vista Jira:** Sprint 1 dentro del Backlog.
- **Debe mostrar:** nombre `Sprint 1 - Base Operativa`, Sprint Goal, fechas, los 6 ítems padre y **28 SP**.
- **Recorte:** cabecera completa del Sprint y su lista de ítems; no es necesario desplegar las 18 subtareas si impide leer el Goal.
- **Archivo final sugerido:** `evidencias-jira/03-sprint-planning.png`.
<!-- INSERTAR AQUÍ LA CAPTURA REAL: evidencias-jira/03-sprint-planning.png -->

### Evidencia 4 — Tablero Scrum Activo

- **Vista Jira:** Active Sprint / Board, después de iniciar Sprint 1.
- **Debe mostrar:** las cuatro columnas `To Do`, `In Progress`, `In Review / QA`, `Done` y tarjetas reales del Sprint.
- **Momento recomendado:** capturar cuando el equipo tenga trabajo legítimamente distribuido entre estados; no mover tarjetas solo para simular avance.
- **Recorte:** exclusivamente el tablero con encabezados y tarjetas.
- **Archivo final sugerido:** `evidencias-jira/04-board-activo.png`.
<!-- INSERTAR AQUÍ LA CAPTURA REAL: evidencias-jira/04-board-activo.png -->

### Evidencia 5 — Gestión de Versiones / Release

- **Vista Jira:** Releases / Versions.
- **Debe mostrar:** `v1.0.0-MVP`, fechas y work items asociados.
- **Recorte:** panel de la Release y asociación de elementos; excluir navegación externa.
- **Archivo final sugerido:** `evidencias-jira/05-release.png`.
<!-- INSERTAR AQUÍ LA CAPTURA REAL: evidencias-jira/05-release.png -->

## 8. Checklist de evidencia antes de entregar

- [ ] Roadmap real recortado y legible.
- [ ] Backlog con Story Points y Componentes visibles.
- [ ] Sprint 1 con Goal explícito y 28 SP.
- [ ] Sprint iniciado y Board con las cuatro columnas visibles.
- [ ] Release `v1.0.0-MVP` visible con elementos asociados.
- [ ] Ninguna captura incluye escritorio, taskbar, pestañas del navegador o espacio sobrante.
- [ ] Las cinco imágenes se guardan dentro de `docs/02 Planificación/evidencias-jira/` y se insertan en este documento antes de la entrega.

[← Volver al README Principal](../../README.md)
