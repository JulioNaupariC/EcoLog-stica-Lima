# Evidencias visuales — ECL-77 / US-013

Capturas de la aplicación real (backend y frontend de la rama
`feat/ECL-77-restablecer-contrasena`), tomadas el 25/10/2026 con Chrome sin
interfaz en tema claro (`prefers-color-scheme: light`), a 360 px y 1280 px.

**Entorno aislado:** PostgreSQL/PostGIS temporal, cuentas sintéticas
`*.demo@ecologistica.example` con contraseñas aleatorias que nunca se mostraron.
El entorno se eliminó al terminar. No se usó la base de demostración.

**Sin secretos:** la contraseña temporal se reemplaza por `•••• •••• •••• ••••`
en el DOM antes de cada captura. Ninguna imagen contiene una contraseña real.

**Página completa:** son capturas de página completa. Los elementos fijos (el
fondo oscuro de los diálogos y el aviso emergente) se ubican a la altura de la
ventana visible y no cubren el resto de la página. Es un efecto de la captura,
no de la interfaz.

En cada pantalla se comprobó automáticamente que no hay scroll horizontal
(`scrollWidth <= innerWidth`).

| # | Pantalla | 360 px | 1280 px | Qué demuestra |
|---|---|---|---|---|
| 1 | Login con ayuda abierta | [01-login-olvidaste-360.png](<01-login-olvidaste-360.png>) | [01-login-olvidaste-1280.png](<01-login-olvidaste-1280.png>) | «¿Olvidaste tu contraseña?» abre el aviso en línea: pedirla al Administrador; no se envían contraseñas por correo. No hay campo de correo, así que no permite enumerar cuentas. |
| 2 | Lista de usuarios | [02-usuarios-360.png](<02-usuarios-360.png>) | [02-usuarios-1280.png](<02-usuarios-1280.png>) | `/usuarios` del Administrador, con correo, rol y estado. «Restablecer contraseña» está deshabilitado en la propia cuenta. A 360 px la tabla se presenta como tarjetas y los correos largos se ajustan. |
| 3 | Confirmación | [03-confirmar-360.png](<03-confirmar-360.png>) | [03-confirmar-1280.png](<03-confirmar-1280.png>) | El diálogo nombra al usuario y avisa que se cerrarán sus sesiones activas. El foco inicial está en «Cancelar». |
| 4 | Temporal enmascarada | [04-temporal-360.png](<04-temporal-360.png>) | [04-temporal-1280.png](<04-temporal-1280.png>) | La temporal se muestra una sola vez, con «Copiar», la advertencia «No se volverá a mostrar · vence en 24 h» y «Listo». En la captura está enmascarada. |
| 5 | Cambio obligatorio con validación | [07-cambio-validacion-360.png](<07-cambio-validacion-360.png>) | [07-cambio-validacion-1280.png](<07-cambio-validacion-1280.png>) | Tras entrar con la temporal, la app solo permite esta página. Los errores aparecen al salir del campo: «Usa al menos 12 caracteres.» y «Las contraseñas no coinciden.». Hay salida con «Cerrar sesión». |
| 6 | Inicio con «Contraseña actualizada» | [08-inicio-tras-cambio-360.png](<08-inicio-tras-cambio-360.png>) | [08-inicio-tras-cambio-1280.png](<08-inicio-tras-cambio-1280.png>) | Después de guardar, la app vuelve al inicio con acceso normal y el aviso «Contraseña actualizada.». |

Controles del mismo recorrido, todos verdaderos:

- la confirmación nombra al usuario;
- la temporal tiene 16 caracteres;
- al cerrar el diálogo, la temporal ya no está en el DOM;
- aparece la insignia «Debe cambiar contraseña»;
- una ruta bloqueada redirige al cambio;
- aparece el aviso «Contraseña actualizada»;
- ninguna pantalla tiene scroll horizontal.

[↑ Validación US-013](<../../VALIDACION_US013.md>)

[↑ Índice del Sprint 3](<../../../README.md>)

[← Volver al README principal](<../../../../../../README.md>)
