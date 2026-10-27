# ECL-67 — Evidencias de accesibilidad

Evaluación del 27/10/2026, Giancarlo Soto. Documento:
[05 WCAG V_1_0_0](<../../05 WCAG V_1_0_0.md>).
Código evaluado: [PR #71](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/71),
commit `5d0ca4d7e831c937ec3e573810bb92f54568bce8`, sobre main `13414dd`.
La rama documental nace de main: los arreglos de UI se revisan en el PR de código.

## Alcance y herramientas efectivamente utilizadas

API real de Docker local y datos de demostración ficticios. Once vistas:
login; inicio de Operación; conductores; registrar pedido; preferencias con
cliente consultado; incidencias de Operación; inicio del conductor; itinerario;
reportar incidencia; usuarios; cambiar contraseña. Roles: Operador, Conductor
y Administrador. Se midió cada vista en claro y oscuro a 1280, 360 y 320 CSS px.

- Chrome automático 156.0.8078.48, Node 22.20.0.
- axe-core 4.14.0, Lighthouse 13.5.0, Playwright 1.64.1 y Puppeteer-core 25.16.0.
- La revisión humana fue declarada por Giancarlo con **Chrome y Narrador**;
  no informó versiones. No se usó NVDA ni la extensión axe DevTools.

Lighthouse se ejecutó en modo **snapshot** sobre la pantalla autenticada.
Una recarga del documento pierde la identidad de Operación guardada en memoria;
medir cada URL con navegación completa podría medir el login en vez de la vista.
Se guardan título, ruta, rol y modo de captura para comprobar la identidad de
cada medición. También se generaron reportes del login mediante `npx lighthouse`
en modo navegación. Ese helper quedó abierto y se detuvo tras producir los
archivos: no se afirma un código de salida satisfactorio de la CLI.

## Archivos y lectura de resultados

| Archivo o carpeta | Contenido |
|---|---|
| [resumen-automatico.json](resumen-automatico.json) | Las 66 mediciones, rutas, títulos, dimensiones, resultado axe y referencia a Lighthouse; sondeos adicionales. |
| [reportes-axe-lighthouse.zip](reportes-axe-lighthouse.zip) | Reportes completos: 66 axe JSON, 22 Lighthouse JSON y 22 HTML; manifiesto de inicio, resumen, teclado y reportes CLI del login. Descomprimir para abrir los HTML o consultar los JSON. |
| [indice-pantallas.csv](indice-pantallas.csv) | Índice de pantalla/tema/ancho y nombre de reporte dentro del ZIP. |
| [capturas](capturas/) | 44 capturas de página completa: cada vista/tema a 1280 y 360 px. A 320 se guardan dimensiones, sin captura al no haber fallos. |
| [teclado-menu-movil.json](teclado-menu-movil.json) | Dieciocho pasos Tab reales del navegador; foco dentro del menú y retorno con Escape en el resumen. |
| [contraste-tokens.json](contraste-tokens.json) | 58 combinaciones revisadas, todas correctas. No es una auditoría completa de contraste de toda la aplicación. |
| [revision-manual.json](revision-manual.json) | Declaración real de Giancarlo, alcance, resultados y límites de lo comunicado. |
| [matriz-criterios.csv](matriz-criterios.csv) y [JSON](matriz-criterios.json) | Cincuenta filas trazables; aplicabilidad, estado, evidencia y cálculo por principio. |
| [antes](antes/) | Muestra de la línea base: nombres, foco, ancho 320 y fuente 200 %; además Lighthouse del itinerario antes de corregir el h2. |
| [procedencia.json](procedencia.json) | Versiones, commits, métricas locales y límites de la evidencia. |
| [SHA256SUMS.txt](SHA256SUMS.txt) | Integridad del contenido publicado en Git; los archivos de texto se calculan con los finales de línea del índice Git. |

Ejemplos visuales: [incidencias de Operación oscuro, 360](capturas/incidencias-operacion-dark-360.png),
[pedido claro, 360](capturas/pedido-light-360.png),
[itinerario claro, 1280](capturas/itinerario-light-1280.png) y
[login oscuro, 360](capturas/login-dark-360.png).
Las barras fijas de acción/navegación se capturan una vez en la posición del
viewport dentro de la imagen larga; una captura completa no demuestra por sí
sola el comportamiento al desplazarse.

Resultado final: 0 violaciones en 66 ejecuciones de axe, Lighthouse 100/100
en los 22 snapshots y sin desbordamiento horizontal en los anchos medidos.
El sondeo de tamaño de fuente al 200 % es distinto del zoom real de Chrome,
que fue confirmado por el usuario. El sondeo de espaciado y el de disposición
horizontal tampoco certifican por sí solos un criterio completo.

axe conserva doce mediciones `incomplete` de contraste, en textos del layout
de escritorio con fondo heredado de un gradiente. El gradiente de layout.css
distribuye bandas sólidas para sidebar, borde y fondo; los textos de la página
están sobre `--color-bg`, con pares de tokens comprobados y revisión manual de
temas declarada correcta. No se borraron esos avisos de los reportes.
El aviso sobre `aria-label` en `time` del informe anterior desaparece con el
texto accesible de la versión final.

La medición anterior incluyó un color intermedio durante una transición de tema;
no se documenta como un defecto estable de la paleta. El ejecutor final espera
el fin de las animaciones antes de medir. La evidencia histórica de ECL-57,
ECL-74 y ECL-75 no se modificó.

## Método y límites del porcentaje

Se usa una matriz independiente de criterios **A y AA**, porque un objetivo AA
incluye ambos niveles, para las vistas y estados observados.

`porcentaje confirmado = criterios con estado cumple / criterios aplicables × 100`

- `no_aplica`: excluido, con justificación por contenido/función ausente.
- `cumple`: evidencia automática, inspección de fuente/pruebas y/o declaración
  manual indicada en la fila. Conclusión limitada a la muestra, no certificación.
- `no_cumple`: incluido en el denominador; no suma al numerador.
- `pendiente`: también incluido en el denominador; no se supone aprobado.

| Principio | Cumplen | Aplicables | No cumplen | Pendientes | % confirmado |
|---|---:|---:|---:|---:|---:|
| Perceptible | 11 | 12 | 0 | 1 | 91,67 % |
| Operable | 11 | 13 | 1 | 1 | 84,62 % |
| Comprensible | 9 | 9 | 0 | 0 | 100 % |
| Robusto | 2 | 2 | 0 | 0 | 100 % |

Los pendientes son 1.4.12 (inspección visual completa con espaciado personalizado)
y 2.4.5 (segundo mecanismo para localizar cada ruta o excepción de proceso).
El registro de estos límites forma parte de la evaluación; no se presenta
ECL-67 como cerrado ni la aplicación como conforme AA.
El incumplimiento 2.2.1 está registrado en
[ECL-83](https://continental-team-il84x39k.atlassian.net/browse/ECL-83):
sesión de 60 minutos sin aviso/extensión, verificado en configuración y código.
No se esperó una hora ni se modificó la duración de sesión durante la prueba.

El catálogo conserva 4.1.1 como fila de trazabilidad, excluida del denominador
por la errata de WCAG 2.1 incorporada en 2025. No se evaluaron criterios
adicionales de 2.2 ni se extrapola a estados no recorridos, otros lectores,
otros navegadores o datos distintos de la demo.

Referencias: [WCAG 2.1](https://www.w3.org/TR/WCAG21/),
[evaluación con herramientas y revisión humana](https://www.w3.org/WAI/test-evaluate/tools/selecting/),
[reflujo a 320 CSS px](https://www.w3.org/WAI/WCAG21/Understanding/reflow.html) y
[tiempo ajustable](https://www.w3.org/WAI/WCAG21/Understanding/timing-adjustable.html).

## Revisión manual registrada y guía para repetirla

Giancarlo respondió que lector, teclado, claro/oscuro, zoom 200 % y 360 px
funcionaron correctamente; después confirmó **Chrome y Narrador en todas las
pantallas**, incluidas las dos de Administrador. No comunicó problemas. Es
testimonio del evaluador, sin transcripción, captura o grabación aportada;
no se atribuyen frases concretas al lector. El campo `pending user evaluation`
del resumen automático solo indica que el ejecutor no realiza pruebas humanas;
el registro humano separado contiene la confirmación posterior.

Para repetir el recorrido:

1. Abrir `http://127.0.0.1:5173` en Chrome. Activar/desactivar Narrador con
   **Windows + Ctrl + Enter**. Mantener las contraseñas en privado y sin capturas.
2. Sin ratón, recorrer con Tab/Shift+Tab y activar con Enter/Espacio. Comprobar
   foco visible, orden, enlace para saltar al contenido, menú y retorno con Esc.
3. En login, probar campos vacíos; luego iniciar sesión como Operador. Recorrer
   Inicio, Conductores, Pedido, Preferencias e Incidencias pendientes. En Cliente,
   escribir Bodega y seleccionar con flechas/Enter. No registrar pedidos nuevos
   solo para probar accesibilidad.
4. Como Conductor, revisar Inicio, Itinerario y Reportar incidencia. Como
   Administrador, revisar Usuarios y Cambiar contraseña; abrir la confirmación
   de restablecimiento y **cancelar**, sin generar una contraseña temporal.
5. Escuchar nombres, roles, estados, instrucciones y errores al enviar formularios
   vacíos. Revisar que los avisos se entiendan sin depender del color.
6. Repetir claro/oscuro, zoom real de Chrome al 200 % y ancho 360 CSS px en
   herramientas de desarrollo. Comprobar lectura y acciones al desplazarse.
7. Registrar pantalla, acción, foco/aviso observado, navegador/lector y versión.
   No completar resultados de memoria ni copiar frases que no se escucharon.

Para completar 1.4.12 se debe ampliar además el interlineado a 1.5, separación
de párrafos a 2em, letras a .12em y palabras a .16em, inspeccionando recortes,
superposición y disponibilidad de controles. Para 2.4.5, registrar los mecanismos
de localización por ruta y justificar cualquier excepción de proceso. Estas
dos comprobaciones no se atribuyen a la declaración general recibida.

## Reproducción automática y validación local

En la rama del [PR #71](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/71),
seguir [frontend/README.md](../../../../../frontend/README.md), sección ECL-67.
El script lee únicamente las contraseñas demo necesarias de `.env`, comprueba
que los campos de contraseña estén vacíos y exige una carpeta nueva por ejecución.
No se publica `.env` ni los valores privados. El ZIP y los archivos sueltos
se revisaron contra los valores privados locales antes de preparar el commit.

Validación local del código evaluado: typecheck y lint correctos; build y precaché
offline correctos; **697 pruebas, 50 archivos**. Cobertura de líneas **97,67 %**,
ramas **92,87 %**, sentencias **95,49 %** y funciones **94,96 %**.
La rama documental ejecuta `python scripts/check_docs.py` después de añadir sus
archivos al índice de Git, porque el comprobador usa los archivos rastreados.
Los resultados de CI deben consultarse en cada PR; no se confunden con estos
resultados locales. Antes de Ready se requiere la auditoría independiente prevista
en la [política de PR](<../../../../04 Contribución/01. Politica de pull requests V_1_0_0.md>).

[Volver al documento WCAG](<../../05 WCAG V_1_0_0.md>) ·
[Volver al índice del Sprint 3](../../README.md) ·
[← Volver al README principal](../../../../../README.md)
