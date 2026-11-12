# Matriz de trazabilidad del MVP

**Nombre del Proyecto:** EcoLogística Lima

| Metadato | Valor |
|---|---|
| Ticket | [ECL-104 — Matriz final de trazabilidad del MVP](https://continental-team-il84x39k.atlassian.net/browse/ECL-104) |
| Versión | V_1_0_0 |
| Fecha de corte | 12/11/2026, `main` en `8cf6258` |
| Redacción | Antony Munive Rios (@ANTONY-MUNIVE), con apoyo de IA (Claude) |
| Revisión | Frank Roy Yupanqui Acevedo (@FrankRoyYA), dueño de ECL-104 |
| Fuentes | [Requisitos funcionales V_1_2_0](<../../01 Inicio/06. Requisitos funcionales V_1_2_0.md>), [requisitos no funcionales V_1_2_0](<../../01 Inicio/07. Requisitos no funcionales V_1_2_0.md>), Jira, BDD de `docs/02 Planificación/BDD`, pruebas de `backend/tests` y `frontend/src`, documentos de validación de cada sprint |

Recorre cada requisito hasta su historia, la BDD, las pruebas automatizadas y la
evidencia de validación. Los conteos de pruebas del backend son los casos que
recoge `pytest --collect-only` en los archivos de cada área (unitarias e
integración). Una prueba puede cubrir más de un requisito. En el frontend se
listan los archivos de prueba; la suite completa tiene 1 018 pruebas en 65
archivos, todas en verde al corte.

**Estado:**
- **Cumplido:** integrado en `main`, con pruebas y validación.
- **Parcial:** integrado, pero con una parte pendiente que se nombra.
- **No implementado:** queda en el backlog.

## 1. Requisitos funcionales

| RF | Historia / Jira | Sprint | BDD | Pruebas backend | Pruebas frontend | Evidencia de validación | Estado |
|---|---|---|---|---|---|---|---|
| RF-001 Autenticación y permisos por rol | US-001 · [ECL-7](https://continental-team-il84x39k.atlassian.net/browse/ECL-7) | 1 (+ ECL-83 en el 4) | Criterios de US-001 en Jira | 182 casos en 19 archivos (`test_auth_*`, `test_rbac`, `test_session*`, `test_security_*`, `test_usuario*`) | `LoginPage`, `auth`, `App`, `SessionExpiryNotice`, `App.sessionExpiry` | [Revisión del Sprint 1](<../Sprint 01/03 Revisión del Sprint V_1_0_0.md>), [ECL-83](<ECL-83 aviso de sesion.md>) | Cumplido |
| RF-002 Vehículos | US-002 · [ECL-8](https://continental-team-il84x39k.atlassian.net/browse/ECL-8) | 1 | Criterios de US-002 en Jira | 114 casos en 10 archivos (`test_vehiculo*`) | `VehiclesPage`, `vehicles` | [Revisión del Sprint 1](<../Sprint 01/03 Revisión del Sprint V_1_0_0.md>) | Cumplido |
| RF-003 Conductores y disponibilidad | US-003 · [ECL-9](https://continental-team-il84x39k.atlassian.net/browse/ECL-9); [ECL-79](https://continental-team-il84x39k.atlassian.net/browse/ECL-79), [ECL-80](https://continental-team-il84x39k.atlassian.net/browse/ECL-80), [ECL-81](https://continental-team-il84x39k.atlassian.net/browse/ECL-81), [ECL-123](https://continental-team-il84x39k.atlassian.net/browse/ECL-123) | 2 y 4 | [ECL-47 / ST-021](<../../02 Planificación/BDD/ECL-47-ST-021-conductores.md>) | 182 casos en 11 archivos (`test_conductor*`, `test_elegibilidad_conductores`) | `DriversPage`, `driverForm`, `drivers`, `App.drivers` | [ST-022](<../Sprint 02/validaciones/VALIDACION_ST022.md>), [ST-023](<../Sprint 02/validaciones/VALIDACION_ST023.md>), [ST-024](<../Sprint 02/validaciones/VALIDACION_ST024.md>), [ECL-79](<ECL-79 elegibilidad conductores.md>), [ECL-80/81](<ECL-80-81 decisiones BDD conductores.md>) | Cumplido |
| RF-004 Pedidos | US-004 · [ECL-10](https://continental-team-il84x39k.atlassian.net/browse/ECL-10) | 1 | Criterios de US-004 en Jira | 101 casos en 10 archivos (`test_pedido*`, `test_clientes*`, `test_cliente_existence`) | `OrderCreatePage`, `orders`, `clients`, `ClientCombobox` | [Revisión del Sprint 1](<../Sprint 01/03 Revisión del Sprint V_1_0_0.md>) | Cumplido |
| RF-005 Preferencias de entrega | US-005 · [ECL-11](https://continental-team-il84x39k.atlassian.net/browse/ECL-11) | 2 | [ECL-51 / ST-025](<../../02 Planificación/BDD/ECL-51-ST-025-preferencias-entrega.md>) | 64 casos en 5 archivos (`test_preferencias*`) | `DeliveryPreferencesPage`, `deliveryPreferencesForm`, `deliveryPreferences`, `ClientPreferencesProposal`, `App.preferences` | [ST-026](<../Sprint 02/validaciones/VALIDACION_ST026.md>), [ST-027](<../Sprint 02/validaciones/VALIDACION_ST027.md>), [ST-028](<../Sprint 02/validaciones/VALIDACION_ST028.md>) | Cumplido |
| RF-006 Rutas optimizadas | US-006 · [ECL-12](https://continental-team-il84x39k.atlassian.net/browse/ECL-12) (ECL-93 a ECL-96); EN-003 [ECL-21](https://continental-team-il84x39k.atlassian.net/browse/ECL-21); EN-008 [ECL-26](https://continental-team-il84x39k.atlassian.net/browse/ECL-26) | 4 | [ECL-12 / US-006](<../../02 Planificación/BDD/ECL-12-US-006-rutas-optimizadas.md>) | 274 casos en 13 archivos (`test_optimizacion*`, `test_optimizaciones*`, `test_rutas_api`, `test_ruta_repository`, `test_modelo_rutas`, `test_benchmark_optimizacion`, `test_calculos_parametros`, `test_parametros*`, `test_casos_referencia_rnf011`) | `operationRoutes` (dominio y servicio), `OperationRoutesPage` | [ECL-96](<ECL-96 servicio de optimizacion.md>), [ECL-21](<ECL-21 benchmark RNF-001.md>), [ECL-26](<ECL-26 parametros versionados y casos de referencia.md>). No hay botón en la interfaz para generar la optimización: se solicita por la API. | Cumplido |
| RF-007 Reoptimización ante incidencias | US-007 · [ECL-13](https://continental-team-il84x39k.atlassian.net/browse/ECL-13) | Backlog | [ECL-13 / US-007](<../../02 Planificación/BDD/ECL-13-US-007-reoptimizacion.md>) | — | — | La BDD está definida; la cola con worker y RNF-002 pasan a [ECL-121](https://continental-team-il84x39k.atlassian.net/browse/ECL-121) | No implementado |
| RF-008 Mapa de rutas y alertas | US-008 · [ECL-14](https://continental-team-il84x39k.atlassian.net/browse/ECL-14) | 4 | [ECL-14 / US-008](<../../02 Planificación/BDD/ECL-14-US-008-mapa.md>) | 73 casos en `test_rutas_api` y `test_ruta_repository` (contrato del mapa) | `OperationRouteMap`, `OperationRoutesPage`, `App.operationRoutes`, `App.lazy` | [ECL-14](<ECL-14 mapa rutas.md>), evaluación WCAG de ECL-103 | Cumplido |
| RF-009 Indicadores de operación y sostenibilidad | US-009 · [ECL-15](https://continental-team-il84x39k.atlassian.net/browse/ECL-15); [ECL-119](https://continental-team-il84x39k.atlassian.net/browse/ECL-119), [ECL-120](https://continental-team-il84x39k.atlassian.net/browse/ECL-120) | 4 | [ECL-15 / US-009](<../../02 Planificación/BDD/ECL-15-US-009-dashboard.md>) | 59 casos en 5 archivos (`test_indicadores*`, `test_cierre_rutas*`) | `SustainabilityPage`, `sustainability`, `indicators`, `routeOutcomes`, `OperationRoutesPage.execution`, `App.sustainability` | [ECL-15](<ECL-15 dashboard sostenibilidad.md>), [ECL-119](<ECL-119 cierre de rutas y sostenibilidad.md>), [ECL-120](<ECL-120 registro y cierre de rutas.md>) | Cumplido |
| RF-010 Reporte de sostenibilidad descargable | US-010 · [ECL-16](https://continental-team-il84x39k.atlassian.net/browse/ECL-16) | Backlog | — | — | — | — | No implementado |
| RF-011 Compensación de carbono | US-011 · [ECL-17](https://continental-team-il84x39k.atlassian.net/browse/ECL-17) | Backlog | — | El cálculo existe sin factor (`test_calculos_parametros`) | El dashboard muestra «Equivalente ambiental: No disponible» | [ECL-26](<ECL-26 parametros versionados y casos de referencia.md>): `CAPTURA_CO2_ARBOL_ANIO` sin un valor con fuente | No implementado |
| RF-012 Incidencias | US-012 · [ECL-18](https://continental-team-il84x39k.atlassian.net/browse/ECL-18); [ECL-82](https://continental-team-il84x39k.atlassian.net/browse/ECL-82), [ECL-98](https://continental-team-il84x39k.atlassian.net/browse/ECL-98) | 3 y 4 | [ECL-72 / ST-039](<../../02 Planificación/BDD/ECL-72-ST-039-incidencias.md>) | 301 casos en 8 archivos (`test_incidencias*`, `test_driver_reports*`, `test_driver_offline_details`, `test_driver_stop_order`) | `IncidentCreatePage`, `OperationIncidentsPage`, `incident`, `incidentSync`, `incidentList`, `incidentResolution`, `useIncidentSynchronization` | [Validación US-012](<../Sprint 03/validaciones/VALIDACION_US012.md>), [I03 con ECL-82](<VALIDACION_US012_ECL82_V_1_1_0.md>), [ECL-98](<ECL-98 resolucion incidencias.md>) | Cumplido |
| RF-013 Restablecer contraseña | US-013 · [ECL-77](https://continental-team-il84x39k.atlassian.net/browse/ECL-77) | 3 | Criterios por ruta en la validación | 85 casos en 4 archivos (`test_reset_password*`, `test_restablecimiento`, `test_password_reset`) | `ChangePasswordPage`, `LoginPage.forgotPassword`, `passwordChangeGuard`, `App.passwordReset`, `UsersPage` | [Validación US-013](<../Sprint 03/validaciones/VALIDACION_US013.md>) | Cumplido |

**Resumen:** 10 de 13 requisitos funcionales cumplidos. RF-007, RF-010 y RF-011
no están implementados y quedan en el backlog con su historia en Jira.

## 2. Requisitos no funcionales

| RNF | Verificación | Evidencia | Estado |
|---|---|---|---|
| RNF-001 Optimización ≤ 45 s (150 pedidos, 15 vehículos) | Benchmark de 30 corridas: P95 de 20,18 s | [ECL-21](<ECL-21 benchmark RNF-001.md>), `test_benchmark_optimizacion` | Cumplido |
| RNF-002 Reoptimización | Sin implementar | [ECL-121](https://continental-team-il84x39k.atlassian.net/browse/ECL-121) | No implementado |
| RNF-003 Seguridad frente a ataques | CodeQL, SonarCloud, cabeceras de seguridad, 422 saneados y modelo de amenazas | [OWASP del Sprint 3](<../Sprint 03/04 OWASP V_1_0_0.md>), [ECL-86](<ECL-86 modelo de amenazas.md>), [ECL-85](<ECL-85 cadena de suministro.md>), informe OWASP de ECL-102 | Cumplido |
| RNF-004 Datos personales | Consulta anonimizada para el Auditor y permisos por rol | [ECL-80/81](<ECL-80-81 decisiones BDD conductores.md>), `test_rbac`, `test_security_exposure` | Cumplido |
| RNF-005 Accesibilidad | WCAG 2.1 AA en los Sprints 3 y 4 | [WCAG del Sprint 3](<../Sprint 03/05 WCAG V_1_0_0.md>), evaluación de ECL-103 | Parcial: el 1.3.2 de las vistas nuevas espera la prueba con lector |
| RNF-006 Operación sin conexión | Cola offline del conductor sin duplicados | [ST-030](<../Sprint 02/validaciones/VALIDACION_ST030.md>), [validación US-012](<../Sprint 03/validaciones/VALIDACION_US012.md>) | Cumplido |
| RNF-007 / RNF-008 Disponibilidad y capacidad | Pruebas de carga del Sprint 2 | [ST-034](<../Sprint 02/validaciones/VALIDACION_ST034.md>), [ST-035](<../Sprint 02/validaciones/VALIDACION_ST035.md>) | Parcial: ST-035 no acredita la carga sostenida y el tablero de RNF-008 ya existe, pero no se volvió a medir |
| RNF-009 Compatibilidad | Chrome y Firefox a 360 y 1280 px | [ECL-14](<ECL-14 mapa rutas.md>), [ECL-15](<ECL-15 dashboard sostenibilidad.md>), [ECL-120](<ECL-120 registro y cierre de rutas.md>) | Cumplido en las vistas evaluadas |
| RNF-010 Mantenibilidad (cobertura ≥ 80 %) | Umbral de cobertura bloqueante en el CI | `.github/workflows/ci.yml`; informe de calidad de ECL-102 | Cumplido |
| RNF-011 Exactitud de CO₂ y costo | Fórmulas sin redondeo intermedio y prueba de casos de referencia | [ECL-26](<ECL-26 parametros versionados y casos de referencia.md>), `test_casos_referencia_rnf011` | Parcial: el CSV de casos de referencia solo tiene la cabecera |
| RNF-012 Sostenibilidad del software | Ocho optimizaciones medidas antes y después | [Informe 01 Green IT](<../reduccion del impacto ambiental/01 Informe de reduccion del impacto ambiental V_1_0_0.md>) | Cumplido |
| RNF-013 Portabilidad y documentación | Guía de entorno local; demo en PC de laboratorio | [Guía ECL-90](<guias/GUIA_ENTORNO_LOCAL_ECL90.md>); [ECL-68](https://continental-team-il84x39k.atlassian.net/browse/ECL-68) | Parcial: falta la ejecución en laboratorio |
| RNF-014 a RNF-017 Credencial temporal, cambio obligatorio, sesiones y auditoría | Pruebas por ruta de US-013 | [Validación US-013](<../Sprint 03/validaciones/VALIDACION_US013.md>) | Cumplido |

## 3. Cómo se mantiene

- Un requisito nuevo o cambiado, por control de cambios, agrega o corrige su
  fila aquí en el mismo PR.
- Cuando un pendiente marcado como «Parcial» se cierra, se actualiza su fila con
  la evidencia nueva.

[Índice del Sprint 4](README.md) · [← Volver al README principal](../../../README.md)
