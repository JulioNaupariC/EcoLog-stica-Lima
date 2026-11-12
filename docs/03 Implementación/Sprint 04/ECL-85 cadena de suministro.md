# ECL-85 — Cadena de suministro: Actions por SHA, Dependabot y auditoría de dependencias

| Metadato | Valor |
|---|---|
| Ticket | [ECL-85](https://continental-team-il84x39k.atlassian.net/browse/ECL-85), seguimiento de ECL-66 |
| OWASP | A03:2025 Software Supply Chain Failures; A08:2025 Software or Data Integrity Failures |
| Autor | Antony Munive Rios (@ANTONY-MUNIVE). ECL-85 se le reasignó el 11/11/2026; tuvo apoyo de IA (Claude) |
| Revisión | Dueños de `.github/`: José Delgadillo o Julio Naupari. Dueño de `docs/`: Frank o Giancarlo |
| Fecha | 11/11/2026, America/Lima |

## 1. Acciones fijadas por SHA (ruta dorada)

Cada `uses:` de `.github/workflows/*.yml` apunta al **SHA completo del commit**
y lleva la versión exacta en un comentario. Una etiqueta como `v7` es mutable:
si alguien la mueve, el CI ejecutaría otro código sin que cambie nuestro
repositorio. Con el SHA, un cambio de la acción exige un PR visible.

El SHA de cada fila es el commit al que apuntaba la etiqueta mayor que el
repositorio ya usaba el 11/11/2026, obtenido con
`git ls-remote --tags https://github.com/<acción>`. La versión del comentario es
la etiqueta exacta que comparte ese commit, de modo que el código que corre el CI
no cambia.

| Acción | Antes | SHA fijado | Versión |
|---|---|---|---|
| `actions/checkout` | `@v7` (7 usos) | `3d3c42e5aac5ba805825da76410c181273ba90b1` | v7.0.1 |
| `actions/setup-python` | `@v7` (3) | `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` | v7.1.0 |
| `actions/setup-node` | `@v7` (1) | `949feb2413d6458794dcd2491c4babbbce0c15c1` | v7.1.0 |
| `actions/upload-artifact` | `@v4` (3) | `ea165f8d65b6e75b540449e92b4886f43607fa02` | v4.6.2 |
| `actions/download-artifact` | `@v4` (2) | `d3f86a106a0bac45b974a628896c90dbdf5c8093` | v4.3.0 |
| `github/codeql-action/init` y `/analyze` | `@v4` (4) | `33d7b85da1a04171e211befe2c739303b9a4c066` | v4.39.3 |
| `SonarSource/sonarqube-scan-action` | `@v8` (1) | `e805d875275f728fac1885b413934be6d7c63f65` | v8.4.1 |

Los tres usos que ya estaban fijados (`checkout`, `setup-node` y `upload-artifact`
en `green-audit.yml`) coinciden con los SHA de la tabla. Comprobación:

```bash
grep -rhn "uses:" .github/workflows/ | grep -v "@[0-9a-f]\{40\} # v"   # sin salida
```

## 2. Actualizaciones y alertas (ruta feliz)

- **`.github/dependabot.yml`** propone cada lunes, hora de Lima, actualizaciones
  de `github-actions` (raíz), `pip` (`/backend`) y `npm` (`/frontend`), con un
  máximo de 3 PR abiertos por ecosistema. Cada propuesta es un PR normal: pasa CI,
  CODEOWNERS y las reglas A10 y A12, y nada se mergea solo.
- **Nuevo job `Supply chain / Dependency audit`** en `ci.yml`, en cada push y PR:
  - **Bloqueante:** `pip-audit` 2.10.1 sobre `backend/requirements.lock` y
    `npm audit --omit=dev --audit-level=high` sobre `frontend/package-lock.json`.
    Ambos son lo que se instala en ejecución.
  - **Informativo** (`continue-on-error`): los mismos análisis sobre las
    dependencias de desarrollo, para que el hallazgo quede a la vista en el log.
- **Alertas de Dependabot:** se activan en *Settings → Code security* del
  repositorio, cosa que exige permiso de administrador. Ver la sección 4.

## 3. Resultado de la auditoría del 11/11/2026 (ruta infeliz)

| Alcance | Resultado | Decisión |
|---|---|---|
| `requirements.lock` (ejecución) | 1 aviso: `protobuf` 6.31.1, PYSEC-2026-1805 / CVE-2026-0994 / GHSA-7gcm-g887-7qv7. Es una denegación de servicio por recursión en `json_format.ParseDict()` con mensajes `Any` anidados. Corregido en 5.29.6 y 6.33.5 | **Riesgo aceptado y documentado.** `ortools` 9.14.6206 exige `protobuf<6.32,>=6.31.1`, por lo que 6.33.5 no se puede instalar sin cambiar de motor de optimización. La API no llama a `ParseDict` ni recibe JSON de protobuf de usuarios (`grep -rn "ParseDict\|json_format" backend/app` sin resultados). Se ignora solo ese identificador, con este motivo en el workflow; cualquier otro aviso bloquea |
| `requirements-dev.lock` | El mismo aviso de `protobuf` | Igual |
| `package-lock.json` (producción) | 0 vulnerabilidades | — |
| `package-lock.json` (desarrollo) | 26 avisos: 13 altos, 11 moderados y 2 bajos, ninguno crítico. Los altos vienen de `@lhci/cli` 0.15.1 (Lighthouse CI de ECL-114): `basic-ftp`, `extract-zip` y otros en su cadena; `minimatch` también llega por `eslint` | No se distribuyen en el build ni se ejecutan con datos de usuarios: solo corren en CI y en el equipo del desarrollador. `npm audit fix --force` exige cambios incompatibles en la herramienta de medición en plena semana de inspección; se dejan como seguimiento en ECL-102 (evaluación final OWASP) |

## 4. Pendiente de un administrador del repositorio

El autor tiene permiso de escritura, no de administración: la API de protección
de rama y la de alertas responden `403`. Quedan para **Julio** (dueño del
repositorio):

1. *Settings → Code security*: activar **Dependabot alerts** y **Dependabot
   security updates**, y adjuntar una captura en ECL-85.
2. *Settings → Branches → main*: dejar la captura de **Require review from
   Code Owners**. La exigencia se trabajó en ECL-88; esta es la ruta de borde de
   ECL-85.

Sin esos dos pasos, el código de este PR funciona igual: el job audita en cada
ejecución y `dependabot.yml` queda listo para cuando se activen las alertas.

## 5. Verificación local

- YAML de los tres workflows y de `dependabot.yml` cargado con `yaml.safe_load`.
- `pip-audit -r backend/requirements.lock --no-deps --disable-pip --ignore-vuln PYSEC-2026-1805`:
  «No known vulnerabilities found, 2 ignored» (código 0).
- `npm audit --omit=dev --audit-level=high`: código 0.

[Índice del Sprint 4](README.md) · [← Volver al README principal](../../../README.md)
