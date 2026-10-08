# Guía visual — ST-029

Propuesta extraída de las capturas de Figma compartidas por el usuario.
Fuente editable: [guía de componentes](https://www.figma.com/design/VhDMfCVBzDfpJWWhbOCbWh/?node-id=5-21).
La aprobación y la auditoría de accesibilidad siguen pendientes.

## Composición móvil

- Frame de pantalla: 360 px de ancho.
- Márgenes laterales: 16 px; ancho útil: 328 px.
- Distribución en una columna, con texto que puede ocupar varias líneas.
- Escala de espaciado: 8, 12, 16 y 24 px.
- Jerarquía principal: título, alerta operativa, siguiente parada y recorrido.
- La siguiente parada se distingue del resto del recorrido por título y tarjeta.
- Las alertas incluyen texto descriptivo y no dependen únicamente de su color.

## Paleta propuesta

| Uso | Color |
|---|---|
| Verde principal: acciones y foco de tarea | `#166534` |
| Verde suave: siguiente parada | `#EFFBF1` |
| Texto principal: títulos y contenido | `#17251C` |
| Texto secundario: direcciones y horarios | `#526158` |
| Ámbar: advertencias | `#854D0E` |
| Rojo: errores | `#B42318` |
| Azul de foco: contorno de teclado | `#1D4ED8` |

Verificar cada combinación con su fondo efectivo, incluyendo estados y foco:
texto normal ≥4.5:1, texto grande ≥3:1 y elementos de interfaz aplicables ≥3:1.
La paleta por sí sola no demuestra cumplimiento de WCAG 2.1 AA.

## Tipografía

Familia propuesta: Inter, con alternativa sans-serif en la implementación.

| Estilo | Tamaño / altura de línea |
|---|---|
| Título | 24 / 32 px |
| Sección | 18 / 26 px |
| Cuerpo | 16 / 24 px |
| Etiqueta | 14 / 20 px |
| Auxiliar | 12 / 18 px |

Los textos auxiliares necesitan contraste suficiente y deben reservarse para
información complementaria. La siguiente parada y las alertas deben seguir
siendo legibles y prioritarias.

## Componentes y estados

**Botones:** altura de 48 px, texto 14 / 20 px y radio de 12 px. La guía presenta
normal, foco, presionado, deshabilitado y acción secundaria. El foco usa un
contorno exterior azul de 3 px, visible y no dependiente solo del color.

**Tarjetas:** texto y estado explícitos para siguiente parada, completada,
pendiente y demora prevista. El color acompaña el significado, sin reemplazar
las etiquetas. La tarjeta admite direcciones y horarios en varias líneas.

**Alertas operativas:** encabezado descriptivo, información del evento y una
indicación breve. Los ejemplos de demora son ficticios; no son datos de tráfico
verificados ni alertas recibidas de una API.

**Aviso de demostración:** visible en cada pantalla. No sustituye la alerta
operativa ni una indicación de desconexión.

**Estado sin asignación:** explica que no hay itinerario y orienta al conductor
a consultar a su coordinador. El botón para cargar el ejemplo solo sirve para
explorar la demo, no para asignar rutas reales.

## Navegación y transferencia a implementación

El prototipo conecta itinerario → detalle → itinerario y permite explorar el
estado sin asignación. Las conexiones de Figma no acreditan navegación por
teclado del producto. En React se debe comprobar orden de Tab, activación con
Enter/espacio, nombres accesibles, foco visible y ausencia de trampas de teclado.

Validar también reflujo y ampliación de texto, contraste de todos los estados,
lectura con tecnologías de asistencia y navegación en Chrome/Firefox dentro de
los tickets de implementación y pruebas correspondientes.
