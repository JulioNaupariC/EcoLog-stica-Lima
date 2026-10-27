# ECL-67 — Comprobación final de espaciado y navegación

Fecha: 27/10/2026. Código evaluado:
`2e8898b7c1fabac084d027ee2ed4dcc6664c6d2c`,
[PR #71](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/71).
Esta entrega completa las dos verificaciones que la evaluación inicial dejó
pendientes. Los artefactos anteriores permanecen intactos como registro histórico.

## Resultado y método

| Principio | Cumplen / aplicables | Pendientes de comprobación | % en la muestra |
|---|---:|---:|---:|
| Perceptible | 12/12 | 0 | 100 % |
| Operable | 12/13 | 0 | 92,31 % |
| Comprensible | 9/9 | 0 | 100 % |
| Robusto | 2/2 | 0 | 100 % |

La [matriz actualizada](matriz-criterios.csv) conserva el denominador y los motivos
de aplicabilidad del [registro inicial](../matriz-criterios.json). Solo cambian
1.4.12 y 2.4.5, con nueva evidencia. El incumplimiento 2.2.1 permanece registrado
en [ECL-83](https://continental-team-il84x39k.atlassian.net/browse/ECL-83).
No se declara conformidad AA de toda la aplicación ni resolución de ese problema.
La evaluación técnica de la muestra queda preparada para auditoría independiente;
esta revisión del implementador no constituye aprobación del PR.

## 1.4.12 — Espaciado de texto

Se aplicaron simultáneamente interlineado 1.5, espacio entre párrafos 2em,
letras .12em y palabras .16em, sin alterar el código de producción ni los datos.
Once vistas, claro/oscuro y 1280/360/320 CSS px: **66 mediciones** y capturas
adicionales al recorrido axe/Lighthouse.

El análisis de geometría registra candidatos a recorte y solapamiento; también
desplaza cada enlace, botón y campo visible del contenido al centro de la ventana
y comprueba que sea alcanzable. Resultado: sin desbordamiento, recortes
inesperados, superposición de texto en el flujo ni controles inaccesibles en
las 66 combinaciones. Es un complemento a la inspección, no su sustituto.

La inspección visual técnica del implementador, asistida por IA, revisó las once
vistas a 320 px y una muestra de escritorio. Se conservaron como casos
intencionales: marca/cuenta con elipsis y nombre accesible completo, encabezado
semántico de tabla móvil oculto visualmente con etiquetas de tarjeta visibles,
y barras fijas cuya posición aparece una sola vez en una captura larga. Los
campos nativos conservan edición/desplazamiento interno; no se exige que todo
un valor largo aparezca simultáneamente en una línea de 320 px. No se detectó
pérdida de información o funcionalidad por aplicar este espaciado en la muestra.

Esta revisión técnica no se atribuye a Giancarlo como una nueva sesión de
Narrador. Su declaración manual anterior se conserva en
[revision-manual.json](../revision-manual.json).

Capturas inspeccionadas:

- [Login](capturas/spacing-login-dark-320.jpg), [Inicio de Operación](capturas/spacing-inicio-operador-light-320.jpg), [Conductores](capturas/spacing-conductores-dark-320.jpg).
- [Pedido](capturas/spacing-pedido-light-320.jpg), [Preferencias](capturas/spacing-preferencias-dark-320.jpg), [Incidencias de Operación](capturas/spacing-incidencias-operacion-dark-320.jpg).
- [Inicio del conductor](capturas/spacing-inicio-conductor-light-320.jpg), [Itinerario](capturas/spacing-itinerario-dark-320.jpg), [Reportar incidencia](capturas/spacing-incidencias-conductor-light-320.jpg).
- [Usuarios](capturas/spacing-usuarios-light-320.jpg), [Cambiar contraseña](capturas/spacing-cambio-contrasena-dark-320.jpg), [Pedido de escritorio](capturas/spacing-pedido-dark-1280.jpg).

Referencia: [W3C, espaciado de texto](https://www.w3.org/WAI/WCAG21/Understanding/text-spacing.html).

## 2.4.5 — Alternativas para localizar las pantallas

Inicio actúa como índice de destinos permitidos para cada rol. Se completaron
sus accesos a Incidencias, Usuarios y Cambiar contraseña, además de Reportar
incidencia para el conductor. Se conservan el menú principal, el menú de cuenta
y los enlaces contextuales. Cada destino permite volver a Inicio mediante la
marca de la cabecera, sin recargar el documento ni perder la identidad en memoria.

El navegador recorrió realmente los **19 enlaces** y sus retornos:

| Rol | Destinos de Inicio | Mecanismo adicional |
|---|---|---|
| Administrador | Pedido, Preferencias, Vehículos, Conductores, Incidencias, Usuarios, Cambiar contraseña | Menú principal; cuenta para contraseña |
| Operador | Los anteriores salvo Usuarios | Menú principal; cuenta para contraseña |
| Conductor | Itinerario, Reportar incidencia, Cambiar contraseña | Navegación inferior, enlace desde Itinerario y menú de cuenta |
| Analista | Cambiar contraseña | Menú de cuenta |
| Auditor | Vehículos, Cambiar contraseña | Menú principal y cuenta |

Los accesos se filtran por los permisos existentes; no se cambian rutas ni RBAC.
Login y cambio obligatorio de contraseña son pasos del proceso de acceso,
no destinos alternativos que permitan eludirlo. Inicio se alcanza desde la
marca y desde la navegación principal. Se aplica el enfoque de índice de
Inicio para un sitio pequeño descrito por
[W3C, múltiples vías](https://www.w3.org/WAI/WCAG21/Understanding/multiple-ways.html).

## Artefactos y validación

- [comprobaciones.json](comprobaciones.json): 66 mediciones de espaciado, candidatos
  clasificados, controles alcanzables y métricas de validación.
- [navegacion-por-rol.json](navegacion-por-rol.json): rutas y encabezados realmente visitados.
- [resumen-automatico.json](resumen-automatico.json): 66 axe sin violaciones y
  22 Lighthouse 100/100. Estos puntajes no son los porcentajes de cumplimiento.
- [matriz CSV](matriz-criterios.csv) y [JSON](matriz-criterios.json): cálculo por criterio.
- [reportes-y-capturas.zip](reportes-y-capturas.zip): ejecución completa, incluidos
  JSON/HTML de Lighthouse, axe, 66 capturas JPG de espaciado y 44 PNG del recorrido
  normal. Las métricas sin clasificar se conservan dentro del archivo.
- [SHA256SUMS.txt](SHA256SUMS.txt): integridad del contenido publicado en Git;
  los archivos de texto se calculan con los finales de línea del índice Git.

Validación del código: **702 pruebas en 50 archivos**, typecheck, lint y build
correctos. Cobertura: líneas 97,67 %, ramas 92,99 %, sentencias 95,49 % y funciones
94,96 %. Se verificaron los archivos y el ZIP contra los valores privados locales
sin imprimirlos. No se modificaron pedidos, incidencias, usuarios ni contraseñas.

Reproducción: en la rama de código, ejecutar
`node frontend/scripts/verify-accessibility.mjs --sprint3 --spacing-review` con
un `EVIDENCE_DIR` nuevo, siguiendo
[frontend/README.md](../../../../../../frontend/README.md).

[Documento WCAG](<../../../05 WCAG V_1_0_0.md>) ·
[Registro inicial de evidencias](../README.md) ·
[Índice del Sprint 3](../../../README.md) ·
[← Volver al README principal](../../../../../../README.md)
