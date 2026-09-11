# Presupuesto del proyecto — EcoLogística Lima

- [Volver ->](</README.md>)

| Metadato | Valor |
|---|---|
| Proyecto | EcoLogística Lima — MVP |
| Versión | 1.0.0 |
| Fecha | 10/09/2026 |
| Moneda de planificación | USD |
| Presupuesto máximo oficial de desarrollo | S/ 500,000 ≈ USD 135,000 |
| OPEX anual oficial posterior | S/ 120,000 para mantenimiento y soporte |

## 1. Supuestos financieros

- El presupuesto de esta fase representa una **línea base empresarial del MVP**, no el desembolso académico personal del equipo.
- Las tarifas por hora son supuestos de planificación compatibles con el rango de desarrollo indicado en la consigna y con roles especializados; no constituyen cotizaciones de proveedores.
- El horizonte de desarrollo considerado para infraestructura es de aproximadamente cuatro meses.
- Los beneficios educativos/gratuitos pueden reducir el gasto real, pero el presupuesto conserva el costo económico de los recursos para fines de gestión.
- La reserva de contingencia es **12%** del subtotal, dentro del rango recomendado de 10%–15%.

## 2. Recursos Humanos — CAPEX

Fórmula: `Costo = Horas asignadas × Tarifa hora (USD)`.

| Rol | Horas | Tarifa USD/h | Subtotal USD | Alcance principal |
|---|---:|---:|---:|---|
| Project Manager | 320 | 40.00 | 12,800.00 | Gobernanza, cronograma, riesgos, comunicaciones y cierre. |
| Software Architect | 240 | 50.00 | 12,000.00 | Arquitectura, integración, decisiones técnicas y revisión transversal. |
| Senior Backend / Optimization Developer | 640 | 50.00 | 32,000.00 | FastAPI, PostGIS, motor VRPTW/Green VRP, seguridad y rendimiento. |
| Frontend Developer | 600 | 35.00 | 21,000.00 | React/TypeScript, mapa, dashboard y experiencia de usuario. |
| Junior / Full-stack Developer | 480 | 25.00 | 12,000.00 | Soporte de módulos, pruebas de integración y mantenimiento del backlog técnico. |
| QA Engineer | 400 | 30.00 | 12,000.00 | BDD, automatización, rendimiento, seguridad y evidencias de aceptación. |
| UI/UX Designer | 240 | 30.00 | 7,200.00 | Flujos, prototipos, accesibilidad y validación de experiencia. |
| **Total RRHH** | **2,920** |  | **109,000.00** |  |

## 3. Licenciamiento y herramientas

| Concepto | Subtotal USD | Supuesto |
|---|---:|---|
| Atlassian Jira/Confluence y colaboración | 700.00 | Reserva de licencias/planes de equipo durante el desarrollo; sujeto a plan académico disponible. |
| Diseño y prototipado (Figma u equivalente) | 300.00 | Plan de diseño/prototipos; puede reducirse con plan educativo. |
| Calidad/SAST/otros plugins | 500.00 | Reserva para SonarCloud/SonarQube gestionado, plugins o servicios equivalentes. |
| **Total licenciamiento** | **1,500.00** |  |

## 4. Infraestructura Cloud y Servicios — OPEX de desarrollo

| Concepto | Subtotal USD | Supuesto |
|---|---:|---|
| Cómputo y servicios cloud base | 2,000.00 | 4 meses × USD 500/mes como referencia de infraestructura. |
| Base de datos, almacenamiento, backups y observabilidad | 600.00 | Reserva para servicios gestionados y retención de evidencias. |
| Mapas/tráfico y servicios externos | 800.00 | Reserva de consumo; prioridad a Leaflet/OSM/OSRM y planes controlados. |
| Dominio, DNS y certificados/operación auxiliar | 100.00 | SSL puede ser gratuito; monto conserva margen para dominio y operación. |
| **Total Cloud/OPEX de desarrollo** | **3,500.00** |  |

## 5. Reserva de contingencia

`Subtotal base = 109,000.00 + 1,500.00 + 3,500.00 = USD 114,000.00`

`Contingencia = USD 114,000.00 × 12% = USD 13,680.00`

La reserva cubre materialización de riesgos de integración externa, rendimiento, seguridad, nube/cuotas y reprocesos de alcance. Su uso requiere registro de causa y aprobación del líder del proyecto.

## 6. Resumen financiero

| Categoría | Costo USD | % del presupuesto total |
|---|---:|---:|
| 1. Recursos Humanos (CAPEX) | 109,000.00 | 85.4% |
| 2. Licenciamiento de Software | 1,500.00 | 1.2% |
| 3. Infraestructura Cloud (OPEX desarrollo) | 3,500.00 | 2.7% |
| **Subtotal de proyecto** | **114,000.00** | **89.3%** |
| 4. Reserva de Contingencia (12% del subtotal) | 13,680.00 | 10.7% |
| **PRESUPUESTO TOTAL ESTIMADO** | **127,680.00** | **100.0%** |

El total estimado de **USD 127,680.00** se mantiene por debajo del límite oficial aproximado de **USD 135,000**, dejando un margen de **USD 7,320.00** frente al techo referencial.

## 7. OPEX anual posterior al MVP

La consigna establece **S/ 120,000 anuales** para mantenimiento y soporte. Ese OPEX de operación posterior se controla como línea presupuestal separada y **no se suma** al presupuesto de desarrollo del MVP presentado arriba, evitando doble contabilización.

## 8. Control presupuestario

- Revisión de costo y forecast en cada Sprint Review.
- Alerta preventiva ante proyección de desviación >5% del subtotal de categoría.
- Solicitud de cambio cuando la desviación esperada supere 10% o consuma la reserva de contingencia.
- Toda variación de tarifa, proveedor, factor de costo o servicio externo debe registrar fecha, fuente y aprobador.
- Los créditos gratuitos/educativos se registran como ahorro real, pero no se eliminan de la estimación económica base hasta confirmar su disponibilidad para todo el periodo.

## 9. Trazabilidad

- Restricción oficial de presupuesto: RES-05 de la consigna del proyecto.
- Riesgos que sustentan contingencia: RSK-01, RSK-02, RSK-05, RSK-06 y RSK-07.
- Detalle de control de cambios: `docs/01. Inicio/02. Acta de constitución V_1_1_0.md`.

[← Volver al README Principal](../../README.md)
