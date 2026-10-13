# Evidencia ECL-22 / EN-004 — Rediseño UI/UX (13/10/2026)

Capturas antes/después de las siete pantallas principales a 360, 768 y 1280 px,
en tema claro y oscuro (42 por fase). Las pantallas muestran los datos ficticios
de `backend/scripts/seed_demo.py` sobre una base local `ecologistica_demo`, con la
API FastAPI y la vista previa del frontend en `127.0.0.1`.

- **Antes:** commit `83b28bd` (`main` tras las fases 1 y 2).
- **Después:** rama `feat/ECL-22-rediseno-ui`.
- **Instrumento:** [`scripts/capture-redesign.mjs`](../../scripts/capture-redesign.mjs)
  (Playwright 1.58.2, Chrome 155.0.8059.40, Node 22.18.0). En la fase «después» el
  script falla si alguna pantalla tiene desbordamiento horizontal: no hubo ninguno.

Actualización 13/10/2026: tras la revisión se regeneraron solo `despues/02-inicio-*` (sección «Próximamente» sin nombres de sprint) y `despues/07-itinerario-*` (botones «Marcar como entregado» / «Marcar como no entregado» y paradas de la demo en el mismo día, 09:00–14:00) con `capture-redesign.mjs despues 02-inicio,07-itinerario`.

Notas de lectura:

- La interfaz anterior no tenía modo oscuro: sus capturas «oscuro» se ven igual que
  las claras.
- Son capturas de página completa: los elementos fijos (navegación inferior del
  conductor y barra de acciones del formulario en móvil) aparecen a la altura de la
  primera pantalla, no al pie de la imagen. En uso real quedan pegados al borde
  inferior de la pantalla.

## Guía visual ST-029 (ECL-55)

Se respetaron las decisiones de la guía de Giancarlo, que aún no está en `main`
(`git show origin/docs/ECL-55-diseno-movil-conductor:frontend/diseno/ST-029/guia-visual.md`):
marco de 360 px con márgenes de 16 px; escala de espaciado 8/12/16/24; verde
`#166534` para acciones, verde suave para la siguiente parada, texto `#17251C` /
`#526158`, ámbar `#854D0E`, rojo `#B42318` y foco azul `#1D4ED8` de 3 px; Inter;
botones de 48 px con radio de 12 px; estados con texto explícito (no solo color);
la siguiente parada destacada con título y tarjeta propios; y estado sin
asignación que orienta a consultar al coordinador. La escala tipográfica es la
modular 1.200 pedida (16 → 19,2 → 23,0 px), cercana a la de la guía (16/18/24 px).

## Accesibilidad y contraste

- [`accesibilidad/`](accesibilidad/resultados.json): `verify-accessibility.mjs` en
  Chrome 155.0.8059.40 y Firefox 146.0.1 con axe-core 4.13.0 (WCAG 2.0/2.1 A y AA):
  0 violaciones, recorrido con teclado y foco visible, sin desbordamiento a
  360/768/1280 px y prueba de espaciado de texto.
- [`scripts/check-contrast.mjs`](../../scripts/check-contrast.mjs): 50
  combinaciones de tokens (texto 4,5:1 e interfaz 3:1, temas claro y oscuro) cumplen
  AA. La de menor margen es el borde de los campos sobre superficie oscura (3,98:1).

## Pares antes / después

### Login

| Ancho | Tema | Antes | Después |
|---:|---|---|---|
| 360 px | Claro | [antes](antes/01-login-360-light.png) | [después](despues/01-login-360-light.png) |
| 768 px | Claro | [antes](antes/01-login-768-light.png) | [después](despues/01-login-768-light.png) |
| 1280 px | Claro | [antes](antes/01-login-1280-light.png) | [después](despues/01-login-1280-light.png) |
| 360 px | Oscuro | [antes](antes/01-login-360-dark.png) | [después](despues/01-login-360-dark.png) |
| 768 px | Oscuro | [antes](antes/01-login-768-dark.png) | [después](despues/01-login-768-dark.png) |
| 1280 px | Oscuro | [antes](antes/01-login-1280-dark.png) | [después](despues/01-login-1280-dark.png) |

### Inicio (Administrador)

| Ancho | Tema | Antes | Después |
|---:|---|---|---|
| 360 px | Claro | [antes](antes/02-inicio-360-light.png) | [después](despues/02-inicio-360-light.png) |
| 768 px | Claro | [antes](antes/02-inicio-768-light.png) | [después](despues/02-inicio-768-light.png) |
| 1280 px | Claro | [antes](antes/02-inicio-1280-light.png) | [después](despues/02-inicio-1280-light.png) |
| 360 px | Oscuro | [antes](antes/02-inicio-360-dark.png) | [después](despues/02-inicio-360-dark.png) |
| 768 px | Oscuro | [antes](antes/02-inicio-768-dark.png) | [después](despues/02-inicio-768-dark.png) |
| 1280 px | Oscuro | [antes](antes/02-inicio-1280-dark.png) | [después](despues/02-inicio-1280-dark.png) |

### Vehículos

| Ancho | Tema | Antes | Después |
|---:|---|---|---|
| 360 px | Claro | [antes](antes/03-vehiculos-360-light.png) | [después](despues/03-vehiculos-360-light.png) |
| 768 px | Claro | [antes](antes/03-vehiculos-768-light.png) | [después](despues/03-vehiculos-768-light.png) |
| 1280 px | Claro | [antes](antes/03-vehiculos-1280-light.png) | [después](despues/03-vehiculos-1280-light.png) |
| 360 px | Oscuro | [antes](antes/03-vehiculos-360-dark.png) | [después](despues/03-vehiculos-360-dark.png) |
| 768 px | Oscuro | [antes](antes/03-vehiculos-768-dark.png) | [después](despues/03-vehiculos-768-dark.png) |
| 1280 px | Oscuro | [antes](antes/03-vehiculos-1280-dark.png) | [después](despues/03-vehiculos-1280-dark.png) |

### Conductores

| Ancho | Tema | Antes | Después |
|---:|---|---|---|
| 360 px | Claro | [antes](antes/04-conductores-360-light.png) | [después](despues/04-conductores-360-light.png) |
| 768 px | Claro | [antes](antes/04-conductores-768-light.png) | [después](despues/04-conductores-768-light.png) |
| 1280 px | Claro | [antes](antes/04-conductores-1280-light.png) | [después](despues/04-conductores-1280-light.png) |
| 360 px | Oscuro | [antes](antes/04-conductores-360-dark.png) | [después](despues/04-conductores-360-dark.png) |
| 768 px | Oscuro | [antes](antes/04-conductores-768-dark.png) | [después](despues/04-conductores-768-dark.png) |
| 1280 px | Oscuro | [antes](antes/04-conductores-1280-dark.png) | [después](despues/04-conductores-1280-dark.png) |

### Registrar pedido (con propuesta P8)

| Ancho | Tema | Antes | Después |
|---:|---|---|---|
| 360 px | Claro | [antes](antes/05-pedido-360-light.png) | [después](despues/05-pedido-360-light.png) |
| 768 px | Claro | [antes](antes/05-pedido-768-light.png) | [después](despues/05-pedido-768-light.png) |
| 1280 px | Claro | [antes](antes/05-pedido-1280-light.png) | [después](despues/05-pedido-1280-light.png) |
| 360 px | Oscuro | [antes](antes/05-pedido-360-dark.png) | [después](despues/05-pedido-360-dark.png) |
| 768 px | Oscuro | [antes](antes/05-pedido-768-dark.png) | [después](despues/05-pedido-768-dark.png) |
| 1280 px | Oscuro | [antes](antes/05-pedido-1280-dark.png) | [después](despues/05-pedido-1280-dark.png) |

### Preferencias de entrega

| Ancho | Tema | Antes | Después |
|---:|---|---|---|
| 360 px | Claro | [antes](antes/06-preferencias-360-light.png) | [después](despues/06-preferencias-360-light.png) |
| 768 px | Claro | [antes](antes/06-preferencias-768-light.png) | [después](despues/06-preferencias-768-light.png) |
| 1280 px | Claro | [antes](antes/06-preferencias-1280-light.png) | [después](despues/06-preferencias-1280-light.png) |
| 360 px | Oscuro | [antes](antes/06-preferencias-360-dark.png) | [después](despues/06-preferencias-360-dark.png) |
| 768 px | Oscuro | [antes](antes/06-preferencias-768-dark.png) | [después](despues/06-preferencias-768-dark.png) |
| 1280 px | Oscuro | [antes](antes/06-preferencias-1280-dark.png) | [después](despues/06-preferencias-1280-dark.png) |

### Itinerario real del conductor

| Ancho | Tema | Antes | Después |
|---:|---|---|---|
| 360 px | Claro | [antes](antes/07-itinerario-360-light.png) | [después](despues/07-itinerario-360-light.png) |
| 768 px | Claro | [antes](antes/07-itinerario-768-light.png) | [después](despues/07-itinerario-768-light.png) |
| 1280 px | Claro | [antes](antes/07-itinerario-1280-light.png) | [después](despues/07-itinerario-1280-light.png) |
| 360 px | Oscuro | [antes](antes/07-itinerario-360-dark.png) | [después](despues/07-itinerario-360-dark.png) |
| 768 px | Oscuro | [antes](antes/07-itinerario-768-dark.png) | [después](despues/07-itinerario-768-dark.png) |
| 1280 px | Oscuro | [antes](antes/07-itinerario-1280-dark.png) | [después](despues/07-itinerario-1280-dark.png) |

[← Volver al README principal](../../../README.md)
