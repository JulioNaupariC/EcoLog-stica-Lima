# ECL-83 — Aviso y renovación de sesión

Validación local: 07/11/2026. Contrato confirmado por Antony a través de Giancarlo. Revisión de backend: Antony; frontend: José. Auditoría independiente y aprobación del PR pendientes.

## Contrato

Login entrega `expires_at` y `max_expires_at` para todos los roles. `POST /sesion/extender` conserva cookie y token; calcula `min(ahora + SESSION_TTL_MINUTES, creado_en + 12 h)`, con TTL actual de 60 minutos. Devuelve ambos plazos y Set-Cookie con el tiempo restante, HttpOnly, SameSite=Strict y Secure en producción. Login y renovación usan Cache-Control: no-store. Origin, cuando está presente, debe estar permitido por CORS.

Sesiones inexistentes, vencidas o revocadas reciben 401. Una sesión válida cuya expiración ya alcanza el tope recibe 409: «La sesión alcanzó su duración máxima; vuelve a iniciar sesión». Fallos de almacenamiento reciben 503 sin detalles internos. No hay contador ni nueva columna. Renovar no elimina la obligación de cambiar contraseña ni habilita acceso offline en ese estado.

Se bloquea primero usuario y después sesión, como en restablecimiento de contraseña. Actualización y auditoría SESION_EXTENDIDA son atómicas. El detalle contiene solo resultado RENOVACION, sin token ni datos personales; se conservan los identificadores técnicos propios del modelo.

## Interfaz y recuperación

Aviso dos minutos antes del vencimiento, con revisión al volver a la pestaña. El diálogo anuncia el plazo, enfoca «Seguir conectado», contiene el foco y permite Tab, Escape, Enter y Espacio. Escape vuelve al formulario dejando un aviso para reabrirlo. Renovar conserva el formulario montado. Las respuestas tardías tras desmontar se ignoran. Un fallo de red permite reintentar sin ampliar el plazo localmente.

El 409 ofrece «Guardar borrador y volver a entrar». La descarga JSON es explícita y excluye contraseñas, archivos, campos ocultos y campos identificados como secretos. Al vencer, el borrador permanece en memoria de React y solo se ofrece descargar después de autenticar al mismo usuario. No se rellena automáticamente. Recargar o cerrar la pestaña lo pierde; cambiar de cuenta o cerrar sesión explícitamente lo elimina. No se guarda el formulario en localStorage ni sessionStorage. Descargar antes de abandonar la página si se necesita conservarlo.

## Migración

Reserva confirmada: `0015_sesion_extendida`, sobre `0014_resolver_incidencias`. Amplía `ck_auditoria_accion` y el enum. Su downgrade borra exclusivamente eventos SESION_EXTENDIDA antes de restaurar la restricción; implica pérdida de esos registros y requiere una reversión autorizada. Se verificó localmente upgrade → downgrade -1 → upgrade; current y heads coinciden en un único head 0015. No se borraron volúmenes ni datos de negocio.

Reservas comunicadas: 0016 para ST-046 y 0017 para EN-008. Si otra migración entra primero, quien integre después debe revisar el head y conservar la unión de eventos al recrear la restricción.

## Verificación y alcance

- Backend: 1047 pruebas unitarias aprobadas, una omitida; cobertura global 94,55 %. Ruff y formato aprobados.
- Integración: nueve pruebas contra PostgreSQL/PostGIS en una base separada. Login HTTP real, cinco roles, renovación, recorte al límite, 409, 401, cookie, revocación, rollback de auditoría y downgrade/upgrade. Reloj controlado en el servicio; no se alteró el reloj del equipo.
- Frontend: typecheck, lint, suite completa con cobertura y build aprobados. Cobertura de líneas 97,85 %. Se cubren temporizadores, reintento, respuestas tardías, recuperación y cambio de usuario.
- Navegador: [resultado](evidencias/ECL-83/browser-2026-11-07/resultado.json), [escritorio](evidencias/ECL-83/browser-2026-11-07/aviso-escritorio.png), [móvil oscuro](evidencias/ECL-83/browser-2026-11-07/tope-movil-oscuro.png). Componente real con HTTP simulado y sin credenciales.
- Narrador: el usuario declaró «Anuncios, foco y teclado correctos en ambos casos» para renovación y tope en ese banco. [Registro](evidencias/ECL-83/revision-manual.json). Sin grabación ni versión registrada; no equivale a prueba manual de cinco roles contra el backend real.

[WCAG 2.2.1](https://www.w3.org/WAI/WCAG21/Understanding/timing-adjustable.html) pide al menos 20 segundos para actuar y diez extensiones. La prueba de integración realiza doce renovaciones cada 58 minutos hasta el límite absoluto con TTL de 60 minutos. Cambiar el TTL requiere verificar de nuevo esa relación.

La [matriz derivada para ECL-103](<ECL-83 matriz WCAG.csv>) conserva 49 observaciones históricas de ECL-67 y modifica solo 2.2.1. No reevalúa otras vistas ni declara conformidad global del MVP. ECL-103 debe evaluar su alcance final. Las evidencias históricas permanecen intactas.

[← Índice Sprint 4](README.md) · [README principal](../../../README.md)
