# ECL-55 / ST-029 — Diseño móvil del conductor

| Campo | Valor |
|---|---|
| Responsable | Giancarlo Marcio Soto Escobar |
| Sprint | Sprint 2 — GestiónOrt y ExpV |
| Ticket | ECL-55 / ST-029 |
| Padre | ECL-22 / EN-004 |
| Estado del entregable | Propuesta para revisión; aprobación del equipo pendiente |
| Rama documental | `docs/ECL-55-diseno-movil-conductor` |
| Fecha de registro | 08/10/2026, America/Lima |

## Alcance

Diseñar la interfaz móvil del conductor para consultar itinerario, siguiente
parada y alertas, desde 360 px, con navegación intuitiva y criterios de diseño
orientados a WCAG 2.1 AA. Se mantiene la identidad visual verde de EcoLogística
Lima. Los ejemplos son ficticios y se identifican como «Datos de demostración».

Este entregable documenta una propuesta de diseño; no acredita implementación,
aprobación ni una auditoría completa de accesibilidad.

## Fuente editable y prototipo

- [Archivo de Figma](https://www.figma.com/design/VhDMfCVBzDfpJWWhbOCbWh/).
- [Mi itinerario](https://www.figma.com/design/VhDMfCVBzDfpJWWhbOCbWh/?node-id=5-125).
- [Detalle de parada](https://www.figma.com/design/VhDMfCVBzDfpJWWhbOCbWh/?node-id=5-163).
- [Sin itinerario asignado](https://www.figma.com/design/VhDMfCVBzDfpJWWhbOCbWh/?node-id=5-194).
- [Guía visual en Figma](https://www.figma.com/design/VhDMfCVBzDfpJWWhbOCbWh/?node-id=5-21).
- [Prototipo navegable](https://www.figma.com/proto/VhDMfCVBzDfpJWWhbOCbWh/?node-id=5-125&starting-point-node-id=5%3A125).

El archivo editable permanece en Figma. Este directorio conserva su referencia,
la [guía visual](guia-visual.md) y el registro de [evidencias](evidencias/README.md).

## Pantallas y navegación propuesta

1. **Mi itinerario:** identificación de la ruta demo, alerta operativa, siguiente
   parada destacada y recorrido con estados. «Ver detalle de parada» abre el
   detalle de la siguiente parada. «Ver ejemplo sin asignación» abre el estado vacío.
2. **Detalle de parada:** pedido, ventana horaria, carga, recepción, alerta e
   indicaciones. «Volver al itinerario» regresa a la pantalla principal.
3. **Sin itinerario asignado:** explica la ausencia de ruta, sin inventar una
   asignación real. «Cargar ejemplo de itinerario» vuelve al ejemplo ficticio;
   ese control pertenece al prototipo de demostración.

La siguiente parada y su alerta son información explícita: no se confunden con
la parada seleccionada, sus indicaciones estáticas o el aviso de demostración.

## Trazabilidad de aceptación

| Criterio de ECL-55/ST-029 | Evidencia propuesta | Validación pendiente |
|---|---|---|
| Visualizar siguiente parada y alertas | Pantallas principal y detalle en Figma | Revisión y aprobación del equipo |
| Adaptarse a 360 px sin desplazamiento horizontal | Frames móviles en Figma; capturas como vistas del diseño | Confirmar dimensiones y reflujo del prototipo en Figma durante la revisión |
| Contraste, legibilidad y navegación accesible | Guía visual, estados, foco y conexiones | Revisión de pares de contraste, lectura y navegación |

El usuario compartió capturas generales de las tres pantallas y la guía visual,
además del resultado de otra sesión conectada a Figma. Esa sesión reportó la
verificación de ancho, desbordamiento, destinos y pares principales de texto
superiores a 4.5:1. Este registro distingue ese reporte de una auditoría propia:
no se ha confirmado aquí la estructura editable ni medido cada par de colores.

## Relación con ST-030

Esta propuesta servirá como referencia visual para la implementación de
**ECL-56/ST-030** en el [PR #24](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/24).
La aprobación del diseño sigue pendiente.

El PR #24 contiene un prototipo parcial con datos demo. No acredita todavía
siguiente parada, alertas operativas, navegación comprobada en Chrome/Firefox ni
integración con itinerarios reales. La aceptación del diseño no demuestra por
sí sola esos comportamientos en React.

La implementación y verificación de accesibilidad de ST-031 y la conservación
de itinerario/sincronización de ST-032 corresponden a sus tickets posteriores.
El prototipo no demuestra persistencia, GPS ni funcionamiento offline.

## Pendientes para cerrar ST-029

- Revisar las vistas PNG incluidas y consultar los frames completos en Figma.
- Registrar revisión, observaciones y aprobación del diseño por el equipo.
- Adjuntar en ECL-55 el enlace de Figma, evidencias y PR documental cuando exista.
- Mantener el estado de propuesta hasta que se confirme la aceptación.
