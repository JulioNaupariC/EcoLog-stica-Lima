# Registro de riesgos — EcoLogística Lima

- [Volver ->](</README.md>)

| Metadato | Valor |
|---|---|
| Proyecto | EcoLogística Lima |
| Versión | 1.0.0 |
| Fecha | 10/09/2026 |
| Método | Probabilidad × Impacto |

## 1. Escalas de evaluación

- **Probabilidad (P):** 1 Muy baja, 2 Baja, 3 Media, 4 Alta, 5 Muy alta.
- **Impacto (I):** 1 Insignificante, 2 Menor, 3 Moderado, 4 Mayor, 5 Catastrófico.
- **Severidad / exposición:** `P × I`.
- **Low:** 1–6; **Medium:** 8–12; **High:** 15–25. Los valores 7, 13 y 14 no se producen con la matriz 5×5 usada en esta línea base.

## 2. Matriz de evaluación de riesgos

| ID | Descripción del riesgo | Categoría | P | I | Severidad | Plan de Mitigación (Preventivo) | Plan de Contingencia (Reactivo) | Responsable |
|---|---|---|---:|---:|---|---|---|---|
| RSK-01 | Indisponibilidad, límites de cuota o cambios de costo en servicios de mapas/tráfico externos. | Técnica / Integración | 3 | 4 | **12 (Medium)** | Diseñar adaptadores, caché, límites de consumo, fallback OSM/OSRM y datos simulados para pruebas. | Conmutar al proveedor/fuente alterna o al último dato disponible; degradar funciones de tráfico sin bloquear planificación. | Antony Munive Ríos |
| RSK-02 | El optimizador no alcanza los objetivos de rendimiento o no produce solución factible en instancias representativas. | Técnica / Algoritmo | 4 | 5 | **20 (High)** | Prototipar metaheurísticas tempranamente, fijar datasets/semillas, perfilar cuellos de botella y ejecutar benchmarks continuos. | Reducir el espacio de búsqueda, aplicar heurística de respaldo y devolver pedidos no asignados con causa mientras se corrige el motor. | Antony Munive Ríos |
| RSK-03 | Direcciones, coordenadas o puntos de referencia de Lima Este son incompletos o inconsistentes. | Datos / Operación | 4 | 4 | **16 (High)** | Validar formato y geocodificación, permitir referencia + coordenadas, medir calidad de datos y depurar datasets de prueba. | Enviar el pedido a revisión manual, solicitar corrección de ubicación y excluirlo temporalmente de la optimización con motivo explícito. | Frank Roy Yupanqui Acevedo |
| RSK-04 | Curva de aprendizaje en FastAPI/PostGIS/React o herramientas de calidad retrasa tareas del Sprint. | Personas / Capacidades | 3 | 3 | **9 (Medium)** | Pair programming, spikes técnicos acotados, guías de arranque y revisión de PR entre integrantes. | Reasignar temporalmente tareas críticas, reducir WIP y priorizar funcionalidad mínima del Sprint. | Julio Armando Naupari Camarena |
| RSK-05 | Crecimiento de alcance o cambios tardíos provocan desviación del cronograma académico. | Gestión / Alcance | 4 | 4 | **16 (High)** | Backlog priorizado, criterios de aceptación claros, control de cambios y validación quincenal de alcance. | Mover ítems no críticos a iteración posterior, renegociar alcance del incremento sin comprometer el MVP obligatorio. | Julio Armando Naupari Camarena |
| RSK-06 | Vulnerabilidad OWASP o exposición indebida de datos personales de clientes/conductores. | Seguridad / Legal | 3 | 5 | **15 (High)** | RBAC, mínimo privilegio, validación de entradas, SAST/CodeQL, secretos fuera del repositorio y pruebas de autorización. | Bloquear release, revocar credenciales afectadas, corregir la vulnerabilidad, revisar logs y ejecutar regresión de seguridad antes de reanudar. | Antony Munive Ríos |
| RSK-07 | Consumo de cloud o APIs supera el presupuesto o las cuotas planificadas. | Financiero / Infraestructura | 2 | 4 | **8 (Medium)** | Alertas de consumo, entornos apagables, cuotas, uso de software abierto y revisión semanal de gasto. | Suspender recursos no esenciales, migrar a plan/proveedor alterno y usar datasets locales hasta normalizar el gasto. | Julio Armando Naupari Camarena |
| RSK-08 | Conectividad móvil deficiente impide al conductor consultar ruta o reportar incidencias. | Operación / Fiabilidad | 4 | 3 | **12 (Medium)** | Persistir última ruta, cola offline, payloads ligeros y pruebas con conectividad degradada. | Operar con última ruta almacenada y sincronizar eventos al recuperar señal; habilitar registro manual por Operador si fuera necesario. | Giancarlo Marcio Soto Escobar |
| RSK-09 | Datos de prueba insuficientes o poco representativos invalidan métricas de rendimiento y aceptación. | Calidad / Datos | 3 | 4 | **12 (Medium)** | Definir datasets versionados con casos normales, límites y excepciones; conservar semillas y línea base secuencial. | Generar dataset sintético controlado, repetir benchmarks y declarar limitaciones de cualquier resultado no representativo. | Frank Roy Yupanqui Acevedo |
| RSK-10 | Concentración de conocimiento en uno o dos integrantes genera dependencia para componentes críticos. | Personas / Continuidad | 2 | 3 | **6 (Low)** | Rotación de revisión, documentación técnica, PR obligatorios y sesiones breves de transferencia. | Asignar un segundo responsable, reconstruir contexto desde ADR/README/Jira y replanificar la tarea si el titular no está disponible. | Julio Armando Naupari Camarena |

## 3. Priorización de atención

| Nivel | Riesgos | Tratamiento |
|---|---|---|
| High | RSK-02, RSK-03, RSK-05, RSK-06 | Revisión semanal; acciones preventivas deben ejecutarse antes del hito afectado. |
| Medium | RSK-01, RSK-04, RSK-07, RSK-08, RSK-09 | Revisión quincenal y seguimiento dentro de Sprint Planning/Review. |
| Low | RSK-10 | Seguimiento mensual; mantener controles de transferencia de conocimiento. |

## 4. Criterios de activación de contingencia

- Rendimiento: activar contingencia si P95 supera 45 s en optimización o 30 s en reoptimización en el benchmark acordado.
- Seguridad: cualquier vulnerabilidad crítica bloquea integración/release hasta remediación y regresión.
- Costos: revisar consumo al 70% del umbral presupuestado y activar recorte/migración si se proyecta superar el límite.
- Datos: pedidos sin ubicación verificable se excluyen de optimización y quedan con causa registrada.
- Cronograma: una desviación proyectada >10% en hito exige replanificación y decisión de alcance.

## 5. Relación con Jira y presupuesto

Los riesgos High justifican la prioridad temprana de EN-001, EN-002, EN-003 y EN-006. La reserva de contingencia financiera se fija en **12% del subtotal planificado**, dentro del rango sugerido de 10%–15%.

[← Volver al README Principal](../../README.md)
