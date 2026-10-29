# Reporte de Seguridad OWASP Top 10 (2025)

**Nombre del Proyecto:** EcoLogística Lima

**Herramienta de Escaneo:** SonarQube / SonarCloud

| Metadato | Valor |
|---|---|
| Ticket | [ECL-66 / EN-010 — Evaluar la seguridad según OWASP Top 10 2025](https://continental-team-il84x39k.atlassian.net/browse/ECL-66) |
| Versión del documento | 1.0.0 |
| Responsable | Antony Munive Ríos — @ANTONY-MUNIVE |
| Análisis base | SonarCloud, rama `main`, commit `7fd891a`, 29/10/2026 15:39 (America/Lima) |
| Proyecto SonarCloud | [JulioNaupariC_EcoLog-stica-Lima](https://sonarcloud.io/project/overview?id=JulioNaupariC_EcoLog-stica-Lima) |
| Referencia normativa | [OWASP Top 10:2025](https://owasp.org/Top10/2025/) |

**Alcance.** El análisis cubre el código que se despliega: `backend/app` (FastAPI) y
`frontend/src` (React), según `sonar-project.properties`. SonarCloud aporta los hallazgos
SAST; las dependencias se auditaron con `pip-audit` y `npm audit` (sección 4), y cada
categoría se contrastó contra los controles reales del código. «Limpio» significa sin
hallazgos abiertos y con controles verificados en el código; «Bajo revisión», que no hay
hallazgo de SonarCloud pero falta un control y existe un ticket de seguimiento.

## 1. Matriz de Cumplimiento OWASP Top 10 2025

La plantilla oficial titula «2025» pero lista los nombres de categoría de la edición 2021.
Esta matriz usa la **lista oficial de 2025**; la [sección 3](#3-correspondencia-con-los-nombres-de-la-plantilla-2021)
relaciona cada categoría con el nombre que trae la plantilla.

| Categoría OWASP 2025 | Estado en Proyecto (Limpio / Vulnerable / Bajo Revisión) | Hallazgos de SonarQube |
|---|---|---|
| A01:2025 – Broken Access Control | **Vulnerable → corregido** en [PR #78](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/78) | 1 vulnerabilidad MEDIUM: `pythonsecurity:S8703` SSRF en `backend/app/monitoring/poll.py:17` (ver Vulnerabilidad #1). Controles: RBAC por permiso con `require_permission` (`backend/app/core/rbac.py`), alcance propio del Conductor en itinerario e incidencias, `GET /usuarios` solo para quien tiene `USUARIOS_ACTUALIZAR` (Administrador). |
| A02:2025 – Security Misconfiguration | **Bajo revisión** — [ECL-84](https://continental-team-il84x39k.atlassian.net/browse/ECL-84) | 0 vulnerabilidades. 1 code smell BLOCKER de configuración: `python:S8414` orden de `CORSMiddleware` en `backend/app/main.py:93`, aceptado con justificación (ver Hallazgo #4). Controles: CORS con orígenes exactos y métodos/cabeceras explícitos; cookie de sesión `HttpOnly`, `SameSite=Strict` y `Secure` en producción (`backend/app/api/auth.py`); producción exige URLs `https` (`backend/app/core/config.py`). Falta: cabeceras HTTP de seguridad. |
| A03:2025 – Software Supply Chain Failures | **Vulnerable → corregido** en [PR #77](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/77); acciones del CI **bajo revisión** — [ECL-85](https://continental-team-il84x39k.atlassian.net/browse/ECL-85) | SonarCloud no reporta hallazgos (no es una herramienta SCA). `pip-audit` y `npm audit`: producción limpia; 2 paquetes Python y 7 avisos npm en dependencias de desarrollo (sección 4). Controles: `requirements.lock`, `package-lock.json` e imágenes Docker fijadas por digest `sha256`. Falta: acciones de GitHub por SHA y alertas de Dependabot. |
| A04:2025 – Cryptographic Failures | **Limpio** | 0 hallazgos. Controles: Argon2id (`t=3`, `m=64 MiB`, `p=4`) en `backend/app/core/passwords.py`; token de sesión de 256 bits (`secrets.token_urlsafe(32)`) guardado solo como SHA-256 (`backend/app/core/session_tokens.py`); contraseña temporal de US-013 persistida solo como hash; HTTPS obligatorio en producción. |
| A05:2025 – Injection | **Limpio** | 0 hallazgos. Controles: SQLAlchemy ORM con parámetros enlazados; las únicas sentencias `text()` son literales fijos (`SELECT 1`, versión de PostgreSQL/PostGIS, expresión de índice); validación estricta con Pydantic (`extra="forbid"`); React escapa la salida y no hay `dangerouslySetInnerHTML`, `innerHTML` ni `eval` en `frontend/src`. |
| A06:2025 – Insecure Design | **Bajo revisión** — [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86) | No aplica a SAST. Controles de diseño: BDD por ruta (dorada, feliz, infeliz, de borde) por historia, reglas RN-001 a RN-022, idempotencia por `operation_id`, mínimo privilegio. Falta: modelo de amenazas formal de los flujos críticos. |
| A07:2025 – Authentication Failures | **Limpio** (falso positivo eliminado en [PR #78](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/78)) | 1 vulnerabilidad MEDIUM: `python:S2068` «credencial embebida» en `backend/app/api/dependencies.py:19`, **falso positivo** (ver Vulnerabilidad #2). Controles: bloqueo tras 3 intentos fallidos por 15 min (RN-001), 401 genérico sin enumerar cuentas, sesión de 60 min, contraseña temporal de 24 h y un solo ciclo con cambio obligatorio de mínimo 12 caracteres (US-013, RN-016 a RN-018). |
| A08:2025 – Software or Data Integrity Failures | **Bajo revisión** — [ECL-85](https://continental-team-il84x39k.atlassian.net/browse/ECL-85) | 0 hallazgos. Controles: CI obligatorio con pruebas, CodeQL y Quality Gate de SonarCloud; protección de `main` con aprobación de otra persona; `CODEOWNERS` por carpeta; solo JSON validado, sin deserialización de objetos. Falta: que la protección exija la aprobación de los Code Owners. |
| A09:2025 – Security Logging and Alerting Failures | **Bajo revisión** — [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86) | 0 hallazgos. Controles: auditoría de `LOGIN_EXITOSO`, `LOGIN_FALLIDO`, `CUENTA_BLOQUEADA`, `AUTORIZACION_DENEGADA`, `CONTRASENA_RESTABLECIDA`, `CONTRASENA_CAMBIADA` e `INCIDENCIA_REGISTRADA`, sin contraseñas, hashes ni datos personales (`backend/app/repositories/auditoria.py`); métricas HTTP y 5xx (ECL-60). Falta: alertas ante patrones anómalos. |
| A10:2025 – Mishandling of Exceptional Conditions | **Bajo revisión** — [ECL-84](https://continental-team-il84x39k.atlassian.net/browse/ECL-84) | 0 vulnerabilidades. 1 code smell BLOCKER `python:S3516` en `backend/app/monitoring/poll.py:50`, corregido en [PR #78](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/78) (ver Hallazgo #3). Controles: los 422 no repiten la entrada (`SanitizedRoute`, `hide_input_in_errors` en login y auditoría); errores de almacenamiento convertidos en excepciones saneadas. Falta: `pedidos` y `vehiculos` aún incluyen `input` en sus 422. |

**Resumen:**

- A04 y A05 están limpias.
- A01, A03 y A07 tienen hallazgos corregidos en el sprint (#77 y #78).
- A02, A06, A08, A09 y A10 quedan bajo revisión, cada una con su ticket del Sprint 4. A03 también tiene pendiente la parte del CI (ECL-85).
- No hay vulnerabilidades altas ni críticas abiertas.

## 2. Detalles de Security Hotspots y Vulnerabilidades Críticas

**Security Hotspots:** SonarCloud no tiene hotspots abiertos en `main`
(`security_hotspots = 0`, Security Review Rating **A**). La exportación de la API
está en [sonarcloud-hotspots-main-7fd891a.json](<evidencias/ECL-66/sonarcloud-hotspots-main-7fd891a.json>).
El único hotspot anterior fue reclasificado por SonarCloud como vulnerabilidad
(etiqueta `former-hotspot`) y se detalla como Vulnerabilidad #2.

**Vulnerabilidades:** 2, ambas de severidad **MEDIUM** en seguridad (Security Rating **C**
por esa causa). Ninguna es alta ni crítica. Ambas se corrigen en el
[PR #78](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/78).

- **Vulnerabilidad #1 — SSRF (`pythonsecurity:S8703`, A01:2025).**
  *Descripción:* `check()` abre con `urlopen` una URL derivada del argumento `--url`.
  *Ubicación:* `backend/app/monitoring/poll.py:17`.
  *Análisis:* es una herramienta de línea de comandos del operador (sondeo de disponibilidad,
  ST-034), no un endpoint; ya exigía `http`/`https`, host presente y prohibía credenciales,
  ruta, query y fragmento. Aun así, permitía apuntar a cualquier host interno, por ejemplo
  `169.254.169.254`.
  *Mitigación aplicada:* solo se aceptan `127.0.0.1`, `localhost` y `::1`; cualquier otro
  origen debe declararse explícitamente en `MONITOR_ALLOWED_HOSTS`. Pruebas nuevas:
  host no permitido rechazado sin sondear, loopback aceptado y allowlist explícita.
- **Vulnerabilidad #2 — Credencial embebida (`python:S2068`, A07:2025).**
  *Descripción:* SonarCloud detecta la palabra «password» en una asignación literal.
  *Ubicación:* `backend/app/api/dependencies.py:19`,
  `PASSWORD_CHANGE_REQUIRED = "Cambio de contraseña requerido"`.
  *Análisis:* **falso positivo**: el valor es el mensaje de la respuesta 403 cuando el
  usuario debe cambiar su contraseña temporal; no es una credencial.
  *Mitigación aplicada:* la constante se renombra a `CHANGE_REQUIRED_DETAIL` con un
  comentario que lo justifica. La respuesta de la API no cambia.

Hallazgos de configuración relacionados con seguridad (code smells):

- **Hallazgo #3 — `python:S3516` (BLOCKER, A10).** `backend/app/monitoring/poll.py:50`:
  `main()` devolvía siempre 0, también al interrumpirse. *Corrección:* devuelve 130 ante
  Ctrl+C ([PR #78](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/78)).
- **Hallazgo #4 — `python:S8414` (BLOCKER, A02).** `backend/app/main.py:93`: SonarCloud
  recomienda agregar `CORSMiddleware` al final. *Decisión:* **aceptado con justificación,
  sin cambio de código.** `MetricsMiddleware` va por fuera a propósito para contar también
  las solicitudes preflight CORS (ECL-60, prueba
  `test_cors_preflight_and_unsupported_method_are_counted`); ese middleware nunca genera
  respuestas propias, así que ninguna respuesta pierde las cabeceras CORS. Se marca como
  *Accepted* en SonarCloud con este motivo.

## 3. Correspondencia con los nombres de la plantilla (2021)

| Categoría oficial 2025 | Nombre en la plantilla | Relación |
|---|---|---|
| A01:2025 Broken Access Control | A01 Broken Access Control | Misma categoría; en 2025 absorbe SSRF (antes A10:2021). |
| A02:2025 Security Misconfiguration | A05 Security Misconfiguration | Sube del puesto 5 al 2. |
| A03:2025 Software Supply Chain Failures | A06 Vulnerable and Outdated Components | Ampliada a toda la cadena de suministro (dependencias, CI, imágenes). |
| A04:2025 Cryptographic Failures | A02 Cryptographic Failures | Baja del puesto 2 al 4. |
| A05:2025 Injection | A03 Injection | Baja del puesto 3 al 5. |
| A06:2025 Insecure Design | A04 Insecure Design | Baja del puesto 4 al 6. |
| A07:2025 Authentication Failures | A07 Identification and Authentication Failures | Renombrada. |
| A08:2025 Software or Data Integrity Failures | A08 Software and Data Integrity Failures | Renombrada. |
| A09:2025 Security Logging and Alerting Failures | A09 Security Logging and Monitoring Failures | Énfasis en alertar, no solo registrar. |
| A10:2025 Mishandling of Exceptional Conditions | A10 Server-Side Request Forgery (SSRF) | Categoría nueva; SSRF pasa a A01. |

## 4. Herramientas complementarias

Ejecutadas sobre `main` en el commit `7fd891a`, el 29/10/2026 a las 15:42 (America/Lima).
Los resultados completos están en [evidencias/ECL-66](<evidencias/ECL-66/README.md>).

| Herramienta | Alcance | Resultado | Acción |
|---|---|---|---|
| `pip-audit -r backend/requirements.lock` | Dependencias de producción (imagen Docker) | 29 paquetes, **0 vulnerabilidades** | Ninguna |
| `pip-audit -r backend/requirements-dev.lock` | Herramientas de desarrollo y CI | 3 avisos en 2 paquetes: `certifi 2026.7.22` (PYSEC-2026-4320 / GHSA-6q48-6c7w-9gw2, CA comprometida) y `setuptools 84.0.0` (GHSA-xmj3-9gf7-h52w) | Actualizados a `2026.10.19` y `84.1.0` en [PR #77](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/77); re-auditoría sin vulnerabilidades |
| `npm audit --omit=dev` (frontend) | Dependencias de producción | 8 paquetes, **0 vulnerabilidades** | Ninguna |
| `npm audit` (frontend, todas) | Incluye herramientas de desarrollo | 7 avisos: 4 altos (`vite`, `undici`, `zod`, `source-map-js`) y 3 moderados (`vitest`, `@vitest/mocker`, `@vitest/coverage-v8`) | Actualizados sin versiones mayores en [PR #77](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/77); re-auditoría con 0. Relevante porque la demo local (ECL-68) ejecuta el servidor de desarrollo de Vite |
| CodeQL (GitHub, Python y JavaScript/TypeScript) | Código fuente, en cada PR y en `main` | Jobs en verde; los PR #74 a #76 informan «No new alerts in code changed by this pull request» | Seguimiento continuo en el CI |

## 5. Plan de seguimiento

| Ticket | Categorías | Acción | Fecha objetivo |
|---|---|---|---|
| [PR #77](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/77) | A03 | Dependencias de desarrollo actualizadas | Sprint 3 (en revisión) |
| [PR #78](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/78) | A01, A07, A10 | SSRF, falso positivo y código de salida | Sprint 3 (en revisión) |
| [ECL-84](https://continental-team-il84x39k.atlassian.net/browse/ECL-84) | A02, A10 | Cabeceras HTTP de seguridad; 422 saneados en `pedidos` y `vehiculos` | Sprint 4 |
| [ECL-85](https://continental-team-il84x39k.atlassian.net/browse/ECL-85) | A03, A08 | Acciones del CI por SHA, alertas de Dependabot, revisión obligatoria de Code Owners | Sprint 4 |
| [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86) | A06, A09 | Modelo de amenazas de los flujos críticos y alertas de eventos de seguridad | Sprint 4 |

Tras el merge de #77 y #78, el siguiente análisis de SonarCloud sobre `main` debe mostrar
0 vulnerabilidades; ese resultado se registrará en la revisión del Sprint 4.

[Evidencias ECL-66](<evidencias/ECL-66/README.md>) ·
[Volver al índice del Sprint 3](README.md) ·
[← Volver al README principal](../../../README.md)
