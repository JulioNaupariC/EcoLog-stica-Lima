# Validación ECL-77 / US-013 — Restablecer contraseña de un usuario

## Trazabilidad

- **Historia:** ECL-77 / US-013, épica EP-01, Sprint 3.
- **Rama:** `feat/ECL-77-restablecer-contrasena`; base `main` en `1d7666a`.
- **Detalle técnico:** [backend/README.md — Restablecimiento de contraseña (ECL-77)](<../../../../backend/README.md>).
- **Capturas:** [evidencias/ECL-77](<evidencias/ECL-77/README.md>).

> Como Administrador quiero restablecer la contraseña de un usuario que la olvidó,
> para que recupere el acceso sin que nadie conozca su contraseña definitiva.

No hay servicio de correo (SMTP), así que no existe autoservicio por email. El
flujo tiene tres piezas:

1. El aviso «¿Olvidaste tu contraseña?» en el login.
2. El restablecimiento por el Administrador, con una temporal que se muestra una
   sola vez.
3. El cambio obligatorio al entrar con la temporal.

## Rutas de validación

Pruebas de integración en `backend/tests/integration/test_password_reset.py`.
Corren sobre PostgreSQL/PostGIS con la cadena real: login, cookie opaca, sesión
persistida, RBAC, Argon2id y auditoría. Las unitarias y las de frontend
complementan cada ruta.

### Ruta dorada — el Administrador restablece

| Criterio | Prueba | Resultado |
|---|---|---|
| Recibe la temporal (16 caracteres) con `Cache-Control: no-store` | `test_golden_reset_revokes_sessions_and_audits` | Pasa |
| Se revocan las sesiones activas del usuario (su sesión previa pasa a 401) | ídem | Pasa |
| Se guarda solo el hash Argon2id y queda `debe_cambiar_contrasena=true`, con vencimiento a 24 h | ídem | Pasa |
| Auditoría `CONTRASENA_RESTABLECIDA` (actor = admin, entidad = usuario, detalle `{"sesiones_revocadas": 1}`, sin contraseña) | ídem | Pasa |
| Interfaz: confirmar, ver y copiar, y al cerrar la temporal desaparece y el foco vuelve al botón de origen | `UsersPage.test.tsx` | Pasa |

### Ruta feliz — login con temporal y cambio

| Criterio | Prueba | Resultado |
|---|---|---|
| El login con la temporal informa `debe_cambiar_contrasena=true` | `test_happy_temporary_login_forces_change_then_normal_access` | Pasa |
| `/vehiculos`, `/usuarios` y `/conductores` responden 403 «Cambio de contraseña requerido» | ídem | Pasa |
| `POST /cambiar-contrasena` responde 204; la sesión actual sigue y obtiene acceso normal | ídem | Pasa |
| La temporal ya no sirve; la nueva entra con `debe_cambiar_contrasena=false`; se audita `CONTRASENA_CAMBIADA` | ídem | Pasa |
| El cambio revoca las otras sesiones y conserva la actual | `test_change_revokes_other_sessions_but_keeps_current` | Pasa |
| Interfaz: redirección forzada tras el login y ante cualquier 403; las demás rutas quedan bloqueadas; aviso «Contraseña actualizada.» | `App.passwordReset.test.tsx` | Pasa |

### Ruta infeliz — un rol que no es Administrador

| Criterio | Prueba | Resultado |
|---|---|---|
| Operador y Auditor no pueden restablecer: 403 y `AUTORIZACION_DENEGADA` con actor y entidad | `test_unhappy_non_admin_cannot_reset[OPERADOR, AUDITOR]` | Pasa |
| Operador, Conductor, Analista y Auditor no pueden listar `/usuarios`: 403 y `AUTORIZACION_DENEGADA` (`usuarios.actualizar`) | `test_unhappy_user_list_is_administrator_only[×4]` | Pasa |
| Los cinco roles que no son Administrador, en unitarias del servicio y del API | `test_restablecimiento.py`, `test_usuarios_api.py` | Pasa |
| Interfaz: un rol que no es Administrador no ve «Usuarios» y `/usuarios` muestra «Acceso denegado» | `App.passwordReset.test.tsx` | Pasa |

### Rutas de borde

| Criterio | Prueba | Resultado |
|---|---|---|
| Temporal vencida: 401 «Credenciales inválidas», idéntico a credenciales incorrectas y sin cookie | `test_edge_expired_temporary_is_generic_401` | Pasa |
| Temporal reutilizada después del cambio: 401 | `test_happy_temporary_login_forces_change_then_normal_access` | Pasa |
| Nueva contraseña de menos de 12 caracteres o igual a la actual: 422, sin repetir la entrada | `test_edge_password_policy_self_reset_and_missing_user` | Pasa |
| El Administrador se restablece a sí mismo: 409 | ídem | Pasa |
| Usuario inexistente: 404 «Usuario no encontrado» | ídem | Pasa |
| Usuario `INACTIVO`: 409 | `test_edge_inactive_user_cannot_be_reset` | Pasa |
| Contraseña actual incorrecta: cuenta como en el login (3 intentos, bloqueo de 15 min, `LOGIN_FALLIDO`/`CUENTA_BLOQUEADA`) | `test_wrong_current_password_counts_and_locks_like_login` | Pasa |
| Ninguna respuesta de error, log ni auditoría contiene una contraseña | `test_no_error_response_or_log_contains_a_password` | Pasa |
| Interfaz: validación al salir del campo de 12 caracteres, distinta de la actual y de coincidencia; el error se limpia al corregir | `ChangePasswordPage.test.tsx` | Pasa |
| Interfaz: el login no tiene campo de correo en la ayuda (sin enumeración) | `LoginPage.forgotPassword.test.tsx` | Pasa |

### Migración `0012_password_reset`

| Criterio | Prueba | Resultado |
|---|---|---|
| `upgrade` → `downgrade` a 0011 → `upgrade`, sin deriva de modelos (`command.check`) | `test_0012_upgrade_downgrade_upgrade_and_single_head` | Pasa |
| Una sola cabeza: `0012_password_reset` | ídem | Pasa |
| El downgrade se niega si hay auditorías nuevas y las conserva | `test_0012_downgrade_rejects_and_preserves_password_audit[×2]` | Pasa |

## Comandos y resultados

Ejecutados el 25/10/2026 sobre el último commit de código de la rama, en Windows 11
con Python 3.12.10 y Node 24.13.0.

Backend, desde `backend/`:

```powershell
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m ruff format --check .
.venv/Scripts/python -m pytest tests/unit --cov=app --cov-fail-under=80
.venv/Scripts/python -m pytest tests/integration   # TEST_DATABASE_URL termina en _test
.venv/Scripts/python -m alembic heads
```

| Comprobación | Resultado |
|---|---|
| `ruff check` / `ruff format --check` | Sin errores / 198 archivos con formato |
| Unitarias | 689 pasan; cobertura total 93,30 % |
| Cobertura de los módulos de ECL-77 | `restablecimiento.py`, `contrasenas.py`, `validation.py` y `schemas/usuario.py` al 100 %; `api/usuarios.py` al 98 %; 99 % en conjunto |
| Integración de ECL-77 | 17 pasan |
| Integración completa | 170 pasan y 1 se omite |
| `alembic heads` | `0012_password_reset (head)` |

La base de pruebas fue un contenedor PostGIS temporal en `127.0.0.1:55432`, con la
base `ecologistica_test` y la extensión `postgis`, eliminado al terminar.

**Nota local:** si la base se crea con `POSTGRES_DB`, la imagen PostGIS instala
también `postgis_topology` y `postgis_tiger_geocoder`, y `alembic check` las
detecta como deriva. Hay que crear la base de pruebas solo con `postgis`.

Frontend, desde `frontend/`:

```powershell
npm run typecheck
npm run lint
npm run test
npm run test:coverage
```

| Comprobación | Resultado |
|---|---|
| `typecheck` / `lint` | Sin errores ni advertencias |
| Pruebas | 598 pasan en 44 archivos |
| Cobertura | 95,57 % de sentencias y 97,73 % de líneas. `users.ts`, `passwordForm.ts` y `LoginPage.tsx` al 100 %; `UsersPage.tsx` al 96,82 % de líneas |

## Seguridad (OWASP A07 y A01)

- **Contraseña temporal:** sale de `secrets`, con 16 caracteres sin ambiguos.
  Solo se persiste su hash Argon2id, vence en 24 h y se entrega una única vez con
  `no-store`. En la interfaz se borra del estado al cerrar el diálogo.
- **Revocación de sesiones:** el restablecimiento revoca todas las sesiones del
  usuario, y el cambio revoca las demás.
- **Respuestas que no revelan nada:** una temporal vencida responde el mismo 401
  genérico. El login no pide correo para la ayuda, así que no permite enumerar
  cuentas.
- **Fuerza bruta en el cambio:** tiene el mismo conteo y bloqueo que el login.
- **Mínimo privilegio (A01):** `GET /usuarios` exige `USUARIOS_ACTUALIZAR`. La
  matriz RBAC no cambia; el `USUARIOS_CONSULTAR` del Operador queda para revisión
  del equipo.
- **Sin contraseñas en salidas:** ninguna contraseña aparece en respuestas de
  error, logs, auditoría, capturas ni en este documento.

## Pendiente

- El requisito funcional lo registra el Analista de requisitos en
  `docs/01 Inicio/06. Requisitos funcionales`; este ticket no lo modifica.
- Encadenar la migración de ECL-73 después de `0012_password_reset`.

[↑ Índice del Sprint 3](<../README.md>)

[← Volver al README principal](<../../../../README.md>)
