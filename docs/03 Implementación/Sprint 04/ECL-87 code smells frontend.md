# ECL-87 Corrección de code smells del frontend

## Alcance

Seguimiento de ECL-65: corregir S6845 y S6843 en `DataTable`, y los dos
patrones con backtracking señalados en `driverForm.ts` y `VehiclesPage.tsx`.
No cambia el contrato de la API ni las reglas de licencia o placa.
El cierre requiere el análisis del PR en SonarCloud y revisión independiente.

## Cambios

- Se elimina `tabIndex` de la región estática de la tabla. Cuando existe
  desbordamiento, dos botones nativos permiten desplazarla horizontalmente
  con Tab y Enter/Espacio. `aria-controls` identifica el contenedor desplazado.
  Los botones conservan el foco al alcanzar un extremo. `ResizeObserver`
  actualiza su presencia al cambiar el tamaño de la tabla o del contenedor,
  y se desconecta al desmontar el componente.
- Se elimina `role="cell"` de `td`, conservando su semántica nativa, el
  `caption`, `scope="col"` y los roles de tabla, grupos y filas usados por la
  presentación móvil. No se sustituyen por roles interactivos ni se suprimen
  avisos del analizador.
- El correo del conductor se comprueba mediante longitud, espacios y búsquedas
  de `@` y del punto separador. Se conserva el formato anterior, incluidos sus
  casos poco habituales con puntos consecutivos; no se añade una política
  distinta de correo ni de licencia.
- Los ceros finales de la fracción decimal se recorren una sola vez desde el
  final, conservando los límites de precisión y el texto original del payload.

Cada recorrido de validación es lineal respecto de la longitud de la entrada.
Las búsquedas de separadores y la expresión de espacios no contienen
alternativas con backtracking superlineal. El recorte decimal realiza como
máximo una iteración por carácter de la fracción.

## Validación local del 7 de noviembre de 2026

Entorno: Windows, Node.js 22.20.0 y dependencias de `package-lock.json`.

| Comprobación | Resultado |
|---|---|
| TypeScript | `npm run typecheck` sin errores |
| ESLint | `npm run lint` sin errores |
| Vitest con cobertura | 57 archivos y 863 pruebas aprobadas |
| Cobertura global | Líneas 97,86 %; sentencias 95,73 %; ramas 93,04 %; funciones 95,31 % |
| Cobertura de los archivos modificados | Líneas 100 % en `DataTable.tsx`, `driverForm.ts` y `VehiclesPage.tsx` |
| Producción | `npm run build` completado, incluido el shell offline |
| Chrome automatizado | A 900 y 360 px: 1 tabla, 3 filas, 8 encabezados y 16 celdas en el árbol de accesibilidad de una muestra sintética |
| Teclado automatizado en Chrome | Tab, Enter y Espacio desplazan la tabla; a 360 px no aparecen controles de desplazamiento ni desbordamiento de la página |
| Narrador y teclado manual | Giancarlo informó en la sesión de trabajo: «Tabla anunciada y teclado correcto» en la app local; no se adjunta grabación |
| SonarCloud del PR | Pendiente de comprobar; los resultados locales no acreditan el cierre de los cuatro issues |
| Auditoría independiente y aprobación humana | Pendientes; esta implementación no se autoaprueba |

Las pruebas versionadas cubren correos válidos e inválidos, normalización,
límites de licencia y placa y entradas de 100 000, 200 000 y 400 000 caracteres.
También comprueban una fracción válida con 100 000 ceros finales, sin alterar
el payload; una inválida conserva el formulario y no llama a la API.
Las pruebas de tabla cubren desbordamiento, cambios de tamaño, limpieza del
observador y controles de fila en el recorrido de Tab. jsdom no mide geometría;
sus callbacks se simulan, y la geometría se contrastó en Chrome real.

Una comprobación auxiliar local comparó 55 987 cadenas de hasta seis caracteres
del alfabeto `a`, `@`, `.`, espacio, salto de línea y `ñ` con la expresión
anterior del correo: ninguna diferencia. El código auxiliar y las capturas de
Chrome se mantienen como artefactos temporales locales, no como evidencia
histórica versionada.

Medición auxiliar sobre las funciones reales transpiladas desde TypeScript:
mediana de siete muestras de veinte ejecuciones por tamaño, en milisegundos
por ejecución. Correo adversario: `a@` seguido de puntos y `!`; decimal
inválido: `1.` seguido de ceros y `1`; decimal válido: `1.23` seguido de ceros.

| Caracteres repetidos | Correo rechazado | Decimal inválido | Decimal válido |
|---:|---:|---:|---:|
| 100 000 | 0,909 ms | 0,058 ms | 0,530 ms |
| 200 000 | 2,354 ms | 0,134 ms | 0,876 ms |
| 400 000 | 3,748 ms | 0,225 ms | 1,797 ms |

Son observaciones locales, no umbrales de rendimiento ni mediciones del API.
La complejidad se sustenta también en los recorridos del código; estos tiempos
no sustituyen el análisis estático ni la validación del PR.

## Reproducción de las pruebas versionadas

Desde `frontend/`, con Node y npm compatibles con el README:

```powershell
npm ci
npm run typecheck
npm run lint
npm run test -- src/components/ui/ui.test.tsx src/domain/driverForm.test.ts src/pages/VehiclesPage.test.tsx
npm run test:coverage
npm run build
```

Para repetir la comprobación manual, reconstruir el frontend de Docker y abrir
`http://127.0.0.1:5173/vehiculos` con una cuenta demo autorizada. Activar Narrador
con Win+Ctrl+Enter, comprobar el anuncio de tabla y encabezados y recorrer las
acciones con Tab. Si la tabla desborda, activar sus botones con Enter y Espacio.
En móvil, comprobar las tarjetas y las acciones de cada fila. No publicar
credenciales ni datos personales en capturas.

Las métricas del análisis final se interpretan según el
[glosario del Sprint 4](CONVENCIONES_Y_GLOSARIO_ECL99.md).

[Índice del Sprint 4](README.md)

[Volver al README principal](../../../README.md)
