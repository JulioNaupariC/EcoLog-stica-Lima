# Validación local — ECL-57 / ST-031

Fecha: 08/10/2026, America/Lima.

Trazabilidad: **ECL-57 / ST-031 → ECL-22 / EN-004 → RNF-005 y RNF-009**.

## Incremento

- Se incorporó un enlace visible al recibir foco para saltar directamente al
  contenido principal y evitar recorrer repetidamente la navegación.
- Se reforzaron tarjetas y listas del itinerario para permitir reducción y
  corte de textos largos sin provocar desplazamiento horizontal.
- Se mantuvieron objetivos táctiles de 48 px, etiquetas de formulario,
  navegación mediante teclado y foco visible de 3 px.
- Se añadió una adaptación para colores forzados del sistema operativo.
- Se creó un verificador reproducible para Chrome y Firefox que comprueba
  reflow, foco, nombres accesibles, contraste y errores de ejecución.

## Checklist WCAG 2.1 AA aplicable

| Criterio | Evidencia | Estado |
|---|---|---|
| 1.3.1 Información y relaciones | Landmarks, encabezados, etiqueta del filtro y listas semánticas | Aprobado en revisión automatizada del flujo |
| 1.4.3 Contraste mínimo | Cuatro muestras críticas entre 6.07:1 y 7.13:1 | Aprobado para las muestras |
| 1.4.10 Reflow | Sin desbordamiento horizontal a 320, 360, 768 y 1280 px | Aprobado |
| 2.1.1 Teclado | Apertura, regreso, filtro y enlace de salto accesibles por teclado | Aprobado |
| 2.4.1 Evitar bloques | Enlace `Saltar al contenido principal` | Aprobado |
| 2.4.3 Orden del foco | Orden lógico desde navegación hacia acciones del itinerario | Aprobado en el recorrido verificado |
| 2.4.7 Foco visible | Indicador de 3 px comprobado con navegación `Tab` | Aprobado |
| 3.3.2 Etiquetas o instrucciones | Filtro con `label`; botones con nombre accesible | Aprobado |
| 4.1.2 Nombre, función y valor | 0 controles sin nombre en el recorrido | Aprobado |

## Resultados técnicos

| Comprobación | Resultado |
|---|---|
| `npm run typecheck` | Aprobado |
| `npm run lint` | Aprobado |
| `npm test` | 264 pruebas aprobadas en 10 archivos |
| `npm run build` | Aprobado |
| Chrome 155.0.8059.40 | Flujo responsive y accesible aprobado |
| Firefox 157.0 | Flujo responsive y accesible aprobado |

Las capturas y resultados estructurados están en
[`evidencias/ECL-57/`](evidencias/ECL-57/README.md).

## Repetir la prueba de navegadores

Con Vite disponible en `http://127.0.0.1:5173` y
`VITE_API_BASE_URL=http://127.0.0.1:8000`, instalar Playwright únicamente en la
subcarpeta ignorada:

```powershell
npm install --prefix node_modules/.ecl57-browser-check --no-audit --no-fund --ignore-scripts playwright@1.64.0
node node_modules/.ecl57-browser-check/node_modules/playwright/cli.js install firefox
node scripts/verify-st031-accessibility.mjs
```

El script intercepta solo la respuesta de login y utiliza datos ficticios. No
acredita autenticación del backend ni debe ejecutarse con credenciales reales.

## Pendientes que impiden afirmar conformidad WCAG total

- Revisión manual completa de todos los criterios WCAG 2.1 AA.
- Pruebas con lector de pantalla y combinaciones de zoom del sistema operativo.
- Validación con usuarios y dispositivos móviles físicos.
- Repetición sobre datos reales cuando exista el endpoint autorizado de
  itinerarios del conductor.

Estos pendientes no contradicen los criterios concretos de ECL-57 ya medidos;
evitan presentar la verificación parcial como una certificación WCAG completa.
