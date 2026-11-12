# Reporte de Seguridad OWASP Top 10 (2025)

**Nombre del Proyecto:** EcoLogística Lima

**Herramienta de Escaneo:** SonarQube / SonarCloud, con CodeQL, `pip-audit` y `npm audit`

| Metadato | Valor |
|---|---|
| Ticket | [ECL-102 — Evaluación final de calidad y seguridad del MVP](https://continental-team-il84x39k.atlassian.net/browse/ECL-102) |
| Versión del documento | 1.0.0 |
| Redacción | Antony Munive Rios (@ANTONY-MUNIVE), con apoyo de IA (Claude) |
| Análisis base | `main` en `8cf6258`, 12/11/2026 (America/Lima). Quality Gate de SonarCloud **Passed** en ese commit. |
| Proyecto SonarCloud | [JulioNaupariC_EcoLog-stica-Lima](https://sonarcloud.io/project/overview?id=JulioNaupariC_EcoLog-stica-Lima) |
| Referencia normativa | [OWASP Top 10:2025](https://owasp.org/Top10/2025/) |
| Antecedente | [Reporte OWASP del Sprint 3](<../Sprint 03/04 OWASP V_1_0_0.md>), con la correspondencia de nombres 2021 → 2025 en su sección 3 |

**Alcance.**
- Se analiza el código que se despliega: `backend/app` y `frontend/src`.
- Incluye lo que agregó el Sprint 4:
  - Optimización y rutas.
  - Cierre de rutas e indicadores.
  - Parámetros versionados.
  - Renovación de sesión.
  - Validación de incidencias.
- Cada categoría se contrastó con los controles del código y con los tickets
  de seguimiento del Sprint 3.

Estados:
- **Limpio:** sin hallazgos abiertos y con controles verificados.
- **Bajo revisión:** sin hallazgo abierto, pero con un control pendiente y su ticket.

## 1. Matriz de Cumplimiento OWASP Top 10 2025

| Categoría OWASP 2025 | Estado en Proyecto (Limpio / Vulnerable / Bajo Revisión) | Hallazgos de SonarQube |
|---|---|---|
| A01:2025 – Broken Access Control | **Limpio.** La SSRF `S8703` del Sprint 3 se cerró en [ECL-84](https://continental-team-il84x39k.atlassian.net/browse/ECL-84) ([#87](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/87)). | 0 issues de seguridad. Controles: todos los endpoints nuevos usan `require_permission`: `OPTIMIZACIONES_EJECUTAR`/`CONSULTAR`, `RUTAS_CONSULTAR`, `INDICADORES_CONSULTAR` y `PARAMETROS_CONSULTAR`/`CREAR`. La incidencia con parada exige que la parada sea de la jornada del conductor; si no, responde 403 ([ECL-82](https://continental-team-il84x39k.atlassian.net/browse/ECL-82)). El Auditor ve conductores anonimizados ([ECL-80](https://continental-team-il84x39k.atlassian.net/browse/ECL-80)). |
| A02:2025 – Security Misconfiguration | **Limpio.** Cerrado en [ECL-84](https://continental-team-il84x39k.atlassian.net/browse/ECL-84). | 0 issues de seguridad. Controles: middleware de cabeceras para toda respuesta: `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, CSP `default-src 'none'`, COOP, CORP y `Permissions-Policy`; HSTS solo en producción. CORS con lista de orígenes. `S8414` (orden de CORS) sigue aceptado con justificación desde el Sprint 3. |
| A03:2025 – Software Supply Chain Failures | **Bajo revisión**, 1 excepción aceptada en ejecución. Controles de [ECL-85](<ECL-85 cadena de suministro.md>) integrados. | 0 issues de seguridad. Fuera de SonarCloud (sección 4): `protobuf` con PYSEC-2026-1805 (DoS, sin parche compatible con `ortools`), aceptado y documentado. 26 avisos en dependencias de desarrollo (los altos, de `@lhci/cli`), que no se despliegan; PR de Dependabot #140 y #141 pendientes de revisión. |
| A04:2025 – Cryptographic Failures | **Limpio** | 0 issues de seguridad. Sin cambios: Argon2id, token de sesión de 256 bits guardado como SHA-256 y cookie `HttpOnly`, `SameSite=Strict` y `Secure` en producción. La renovación de sesión no vuelve a escribir el token (sin `Set-Cookie`). |
| A05:2025 – Injection | **Limpio** | 0 issues de seguridad. ORM con parámetros enlazados; la única consulta `text()` es `SELECT 1` del sondeo. Las entradas nuevas (fecha de operación, resultado de parada, periodo del dashboard y parámetros) se validan con Pydantic. El mapa muestra texto escapado por React. |
| A06:2025 – Insecure Design | **Limpio**, con riesgos residuales trazados. Cerrado en [ECL-86](<ECL-86 modelo de amenazas.md>). | No aplica a SAST. STRIDE de login, restablecimiento, cola offline y optimización. Límite de 150 pedidos por fecha (422 si hay más). Los resultados de parada no pueden ser futuros ni anteriores al día de la ruta, y no se sobrescriben (409). |
| A07:2025 – Authentication Failures | **Limpio.** WCAG 2.2.1 resuelto sin debilitar la sesión ([ECL-83](<ECL-83 aviso de sesion.md>)). | 0 issues de seguridad. Renovación con tope absoluto de 12 h; 401 para sesiones vencidas o revocadas; 409 al alcanzar el tope; bloqueo usuario → sesión; auditoría `SESION_EXTENDIDA` sin token. Bloqueo de cuenta tras 3 intentos. |
| A08:2025 – Software or Data Integrity Failures | **Limpio.** Cerrado en [ECL-85](<ECL-85 cadena de suministro.md>) y [ECL-88](https://continental-team-il84x39k.atlassian.net/browse/ECL-88). | 0 issues de seguridad. 21 `uses:` fijados por SHA. `main` exige revisión de Code Owners, rama al día y checks; las aprobaciones antiguas se descartan. Los parámetros versionados no se editan ni se borran, y cada optimización guarda su instantánea. |
| A09:2025 – Security Logging and Alerting Failures | **Bajo revisión** — [ECL-122](https://continental-team-il84x39k.atlassian.net/browse/ECL-122) | 0 issues de seguridad. Auditoría de login, bloqueo, restablecimiento, renovación y validación de incidencias. Contador `ecolog_http_5xx_total` por ruta. Falta desplegar la regla y el canal de alerta (ECL-122, backlog). |
| A10:2025 – Mishandling of Exceptional Conditions | **Limpio.** Cerrado en [ECL-84](https://continental-team-il84x39k.atlassian.net/browse/ECL-84). | 0 issues de seguridad. Los 422 de `/pedidos` y `/vehiculos` no repiten la entrada. Los fallos de almacenamiento de la sesión responden 503 sin detalles. Si el motor no encuentra solución o falla, la corrida queda `FALLIDA` y responde 503 con un motivo seguro, sin trazas. La validación de incidencias responde 503 sin detalles internos si falla el almacenamiento. |

**Resumen:**
- 8 de 10 categorías limpias.
- A03 queda **bajo revisión** por una excepción aceptada en una dependencia de
  ejecución sin parche compatible, y por las dependencias de desarrollo de
  Lighthouse CI.
- A09 queda **bajo revisión** porque la alerta no está desplegada (ECL-122).
- Todos los tickets de seguimiento del Sprint 3 (ECL-84, 85 y 86) están
  integrados.
- SonarCloud en `main`: **0 issues de seguridad**, calificación de seguridad **A** (era C en el Sprint 3), 0 security hotspots y Security Review **A** ([overview](<evidencias/ECL-102/sonarcloud-overview-main.png>)).

## 2. Detalles de Security Hotspots y Vulnerabilidades Críticas

**Security Hotspots:**
- **0 por revisar** en `main`; «100 % Security hotspots reviewed».
- Security Review Rating **A**
  ([captura](<evidencias/ECL-102/sonarcloud-security-hotspots-main.png>)).
- SonarQube Cloud avisa que el concepto de hotspot está deprecado: esos
  hallazgos ahora aparecen como issues de seguridad, que también suman 0.

**Vulnerabilidades:**
- **0 issues de seguridad** en todo el código.
- 2 issues de seguridad cerrados en los últimos 30 días (gráfico «Security
  issues closed»), con un tiempo medio de corrección de 7,8 días.
- No hay vulnerabilidades altas ni críticas.
- El único issue abierto del proyecto es de fiabilidad, no de seguridad
  (`vrptw.py`, ver [03 Calidad](<03 Calidad de código V_1_0_0.md>)).

**Informe «Security Reports → OWASP Top 10» de SonarCloud:** no se usa.
- SonarQube Cloud lo marca como deprecado (aparece como «Security r…
  Deprecated» en Measures).
- La matriz de la sección 1 se construyó como en el Sprint 3: hallazgos de
  SonarCloud, más las herramientas de dependencias, más los controles
  verificados en el código.

- **Vulnerabilidad #1 del Sprint 3 — SSRF (`pythonsecurity:S8703`, A01).** Cerrada.
  - *Ubicación:* `backend/app/monitoring/poll.py`.
  - *Mitigación:* `safe_origin()` rearma el origen con un esquema de una lista
    cerrada, el host tomado de la allowlist y el puerto como entero. `urlopen` ya
    no recibe el texto de `--url`. Rechaza credenciales, ruta, query, fragmento y
    puertos inválidos.
  - *Evidencia:* [#87](https://github.com/JulioNaupariC/EcoLog-stica-Lima/pull/87)
    y la calificación de seguridad A con 0 issues de seguridad en el
    [overview](<evidencias/ECL-102/sonarcloud-overview-main.png>).
- **Hallazgo de dependencias — `protobuf` 6.31.1, PYSEC-2026-1805 /
  CVE-2026-0994 (A03).**
  - *Descripción:* denegación de servicio por recursión en
    `json_format.ParseDict()` con mensajes `Any` anidados.
  - *Análisis:* `protobuf` llega como dependencia de `ortools`, que exige
    `< 6.32`. La aplicación no llama a `ParseDict` con datos externos.
  - *Mitigación:* excepción explícita (`--ignore-vuln PYSEC-2026-1805`) en la
    auditoría bloqueante del CI, documentada en
    [ECL-85](<ECL-85 cadena de suministro.md>). Se revisa cuando `ortools`
    admita una versión corregida.
- **Hallazgo de dependencias de desarrollo — cadena de `@lhci/cli` 0.15.1 (A03).**
  - *Descripción:* avisos altos en `basic-ftp`, `extract-zip` y otros paquetes
    transitivos.
  - *Análisis:* solo se usa en el workflow de Lighthouse CI; no está en el
    build ni en la imagen.
  - *Mitigación:* la auditoría de desarrollo solo informa y no bloquea. Los PR
    de seguridad de Dependabot #140 y #141 actualizan `@lhci/cli` y se revisan
    después de la evaluación.

## 3. Herramientas complementarias

| Herramienta | Alcance | Resultado | Acción |
|---|---|---|---|
| `pip-audit` 2.10.1 sobre `requirements.lock` (job «Supply chain / Dependency audit») | Dependencias de ejecución | 1 aviso (`protobuf`, excepción aceptada); bloqueante para cualquier otro | Revisar cuando `ortools` lo permita |
| `npm audit --omit=dev --audit-level=high` | Dependencias de producción del frontend | **0 vulnerabilidades**; bloqueante | Ninguna |
| `pip-audit` y `npm audit` de desarrollo | Herramientas de desarrollo y CI | 26 avisos en npm (13 altos, 11 moderados, 2 bajos, ninguno crítico); los altos vienen de `@lhci/cli` y `minimatch` (por `eslint`). Solo informan | PR #140 y #141 |
| CodeQL (Python y JavaScript/TypeScript) | Código fuente, en cada PR y en `main` | Jobs en verde en `8cf6258` | Seguimiento continuo |
| Dependabot | Alertas de seguridad activas; actualizaciones de versión pausadas hasta el 20/11 | [Captura de alertas](<evidencias/ECL-85/ECL-85-dependabot-alertas.png>) | Reactivar el 20/11 con el procedimiento de `.lock` (A19) |

## 4. Plan de seguimiento

| Ticket | Categorías | Acción | Estado |
|---|---|---|---|
| [ECL-84](https://continental-team-il84x39k.atlassian.net/browse/ECL-84) | A01, A02, A10 | Cierre de `S8703`, cabeceras de seguridad y 422 saneados | Integrado (#87) |
| [ECL-85](https://continental-team-il84x39k.atlassian.net/browse/ECL-85) | A03, A08 | Actions por SHA, auditoría bloqueante y Dependabot | Integrado (#126, #138) |
| [ECL-86](https://continental-team-il84x39k.atlassian.net/browse/ECL-86) | A06, A09 | Modelo de amenazas STRIDE y alerta propuesta | Integrado (#120) |
| [ECL-122](https://continental-team-il84x39k.atlassian.net/browse/ECL-122) | A09 | Alerta 5xx desplegable (credencial de `/metrics`, Prometheus y Alertmanager) | Backlog |
| PR #140 y #141 | A03 | Actualizar `@lhci/cli` (dependencia de desarrollo) | Pendiente de revisión |
| Excepción `protobuf` | A03 | Retirar `--ignore-vuln` cuando `ortools` admita `protobuf` ≥ 6.32 | Revisión mensual |

[Volver al índice del Sprint 4](README.md) ·
[← Volver al README principal](../../../README.md)
