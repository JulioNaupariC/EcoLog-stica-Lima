# Plan de pruebas de capacidad y disponibilidad — Sprint 2

**Proyecto:** EcoLogística Lima
**Jira:** ECL-23 / ST-033
**Responsable:** Julio Armando Naupari Camarena
**Estado:** Planificación

## 1. Objetivo

Definir escenarios, métricas y criterios de aceptación para evaluar el rendimiento y la disponibilidad de la API y la base de datos de EcoLogística Lima.

## 2. Escenario de carga

- 1,000 pedidos diarios.
- 50 vehículos.
- 100 solicitudes concurrentes.
- Horario operativo: 05:00 a 22:00.
- Ambiente de pruebas con datos sintéticos o anonimizados.

## 3. Métricas y umbrales

| Indicador | Objetivo |
|---|---|
| Latencia P95 del registro de pedidos | <= 2 segundos |
| Errores HTTP 5xx | < 1 % |
| Disponibilidad objetivo | >= 99.5 % |
| Horario de evaluación | 05:00 a 22:00 |

## 4. Procedimiento de pruebas

1. Preparar datos representativos de pedidos y vehículos.
2. Verificar disponibilidad de la API y la base de datos.
3. Ejecutar una prueba controlada con 100 solicitudes concurrentes.
4. Registrar los tiempos de respuesta del registro de pedidos.
5. Calcular la latencia P95.
6. Calcular el porcentaje de respuestas HTTP 5xx.
7. Registrar intervalos de disponibilidad e indisponibilidad.
8. Comparar los resultados obtenidos con los objetivos definidos.

## 5. Fórmulas

**Errores 5xx (%):** (respuestas HTTP 5xx / total de solicitudes) x 100.

**Disponibilidad (%):** (tiempo disponible / tiempo operativo observado) x 100.

**P95:** percentil 95 de los tiempos de respuesta registrados.

Una medición breve no demuestra por sí sola el cumplimiento del SLA de un periodo completo.

## 6. Criterios de aceptación

- La prueba representa la carga definida.
- El P95 del registro de pedidos es menor o igual a 2 segundos.
- La tasa de errores 5xx es inferior al 1 %.
- Se dispone de registros para evaluar el objetivo de disponibilidad del 99.5 %.
- Los resultados y limitaciones quedan documentados.

## 7. Evidencias requeridas

- Scripts y configuración de pruebas.
- Registros de ejecución.
- Resultados de latencia P95 y errores HTTP 5xx.
- Registros de disponibilidad.
- Informe comparativo con los umbrales.
- Enlaces a Jira y Pull Requests.

## 8. Responsables

- **Julio:** definir metodología, métricas y criterios.
- **Antony:** instrumentar métricas de API y base de datos.
- **José:** ejecutar pruebas y recopilar evidencias.

## 9. Estado actual

Este documento establece la planificación. Las pruebas todavía no se consideran ejecutadas ni aprobadas; sus resultados se registrarán después de las verificaciones técnicas.
