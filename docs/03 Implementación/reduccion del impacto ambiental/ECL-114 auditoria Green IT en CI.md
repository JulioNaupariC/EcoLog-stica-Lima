# ECL-114 — Auditoría Green IT con Lighthouse CI

**Alcance:** workflow de auditoría de la página pública `/login`, 1 Story Point
según el [glosario ECL-99](<../Sprint 04/CONVENCIONES_Y_GLOSARIO_ECL99.md>).
Las páginas autenticadas corresponden a las campañas manuales ECL-108 y ECL-115.
Este ticket no realiza el cálculo SWDM v4 ni acredita las ocho optimizaciones
de la rúbrica.

## ANTES y DESPUÉS para el informe 01

ANTES oficial: `e09dcd80e32431018d4020bb02c89ffae7505705`, commit de ECL-108.
En ese commit no existen `.github/workflows/green-audit.yml` ni
`frontend/lighthouserc.json`. El workflow existente, `.github/workflows/ci.yml`,
instala y construye el frontend, pero no ejecuta Lighthouse:

```yaml
- name: Install frontend dependencies
  run: npm ci
# ... lint, typecheck y pruebas existentes ...
- name: Build frontend
  run: npm run build
```

Los fragmentos originales de ese workflow, `frontend/package.json` y
`frontend/src/app/App.passwordReset.test.tsx` se conservaron localmente en
`.tmp-ecl114-before/`, obtenidos con `git show` del commit ANTES. La rama de
implementación parte de `0461107`, después de ECL-98. Para recuperar la fuente
ANTES sin modificar evidencias históricas:

```powershell
git show e09dcd80e32431018d4020bb02c89ffae7505705:.github/workflows/ci.yml
git show e09dcd80e32431018d4020bb02c89ffae7505705:frontend/package.json
```

DESPUÉS: `.github/workflows/green-audit.yml` y `frontend/lighthouserc.json`.
El código de aplicación y los checks existentes se conservan. El nuevo job
ejecuta `npm ci`, `npm run build` y `npx --no-install lhci autorun`. Se instala
`@lhci/cli` **0.15.1** como dependencia de desarrollo exacta y con lockfile;
incluye Lighthouse 12.6.1 y es compatible con Node 22.18.0 del proyecto.
LHCI 0.16.0 exige Node >=22.19.0; no se cambió Node para incorporar la herramienta.

## Comportamiento del workflow

- Eventos `push` y `pull_request`; permisos `contents: read`, sin secretos.
- Acciones checkout 7.0.1, setup-node 7.1.0 y upload-artifact 4.6.2 fijadas por
  SHA de sus tags oficiales. No se modifica la configuración de otros workflows.
- `staticDistDir: ./dist`, fallback SPA para `/login` y preset `desktop`.
  LHCI inicia y detiene su servidor estático; sustituye el puerto del URL local.
- Tres corridas; cada aserción usa la mediana de su métrica. Se incluyen también
  las aserciones aprobadas en `assertion-results.json`.
- El reporte se sube a `temporary-public-storage`. Su enlace aparece en el log
  de LHCI y en el resumen del job, leyendo `.lighthouseci/links.json`.
- Los HTML/JSON de las corridas, las aserciones y los enlaces quedan en el
  artefacto `green-audit-<run_id>-<run_attempt>-<evento>` durante 30 días.
  Se intenta conservarlo incluso si falla el umbral o la subida pública.
- Un umbral fallido o una subida pública fallida produce código distinto de
  cero; no se usa `continue-on-error` ni se ignoran errores.
- El check **Green IT / Lighthouse desktop** queda opcional. Este PR no cambia
  las reglas de protección ni convierte el resultado local en aprobación del
  DESPUÉS. Cualquier futura decisión de hacerlo obligatorio requiere validar
  ECL-115 y las mediciones del runner.

El build usa una URL local de API y demo desactivada. Solo se audita login,
sin iniciar sesión, cookies, cuentas ni datos de negocio. Los reportes públicos
son temporales; descargar el artefacto para conservar la evidencia.

## Umbrales y comprobación local

Los valores locales son una comprobación del workflow sobre un build estático,
no una comparación con las mediciones Vite/Compose de ECL-108 ni la campaña
DESPUÉS de ECL-115. Entorno: Windows, Node 22.18.0, Chrome headless 156 y
Lighthouse 12.6.1. Datos por corrida, hashes SHA-256 y aserciones completas:
[validacion-local.json](evidencias/ECL-114/validacion-local.json).

| Métrica | Umbral del ticket | Mediana local (3 corridas) |
|---|---:|---:|
| Performance | >= 0,90 | 1,00 |
| FCP | <= 1000 ms | 632,449 ms |
| LCP | <= 1400 ms | 672,449 ms |
| TBT | <= 85 ms | 0 ms |
| CLS | <= 0,02 | 0,000005302 |
| Transferencia (`total-byte-weight`) | <= 1 100 000 bytes | 425 312 bytes |

La ejecución local de `lhci autorun` terminó con código 0 y publicó
[este reporte temporal](https://storage.googleapis.com/lighthouse-infrastructure.appspot.com/reports/1794078522397-9875.report.html).
También se probó el camino negativo con una configuración temporal que exigía
FCP <=0 ms: `lhci assert` devolvió **1**, como corresponde. Luego se repitió la
aserción con el archivo definitivo: las seis aserciones pasaron. El YAML se
analizó con `js-yaml` y el script del resumen se ejecutó localmente verificando
que genera el enlace público. La ejecución real del workflow se comprueba en
el PR; un resultado local no predice el rendimiento del runner.

## Corrección separada de ECL-111

`UsersPage` difiere su carga inicial a un efecto y una promesa. El título puede
aparecer antes de que `listUsers` sea llamado. En
`frontend/src/app/App.passwordReset.test.tsx` se cambió:

```ts
// ANTES de la corrección
expect(listUsersMock).toHaveBeenCalledWith(1, 12)
// DESPUÉS
await waitFor(() => expect(listUsersMock).toHaveBeenCalledWith(1, 12))
```

También se espera el campo de la página diferida de cambio voluntario mediante
`findByLabelText`, y las llamadas de carga de incidencias/vehículos en
`App.test.tsx` mediante `waitFor`. Se inspeccionaron los otros `App*.test.tsx`
y las pruebas de páginas: las comprobaciones después de datos recibidos o
de guardados ya completados no se cambiaron. No se añadieron esperas fijas ni
se ampliaron los timeouts.

La corrección se conserva en el commit separado
`5678ff2` — `test(ECL-111): esperar la carga de páginas diferidas`.
`npx vitest run src/app` pasó **tres veces: 64 pruebas en 6 archivos por vez**.
Las ejecuciones de cobertura con paralelismo predeterminado presentaron
timeouts en otras pruebas de navegación; se documenta la comprobación con
dos workers para distinguirla de esas ejecuciones fallidas.
Con `npm run test:coverage -- --maxWorkers=2` pasaron **771 pruebas en 52
archivos**: líneas **97,75 %**, ramas **93,03 %**, funciones **94,96 %** y
sentencias **95,48 %**. Typecheck, lint, build y `npm ci` también pasaron.
La limitación de workers fue solo un argumento local: no se cambiaron
la configuración ni los umbrales de las pruebas o del CI existente.

## Reproducción

Desde `frontend/`, con Node indicado en `.nvmrc` y Chrome instalado:

```powershell
npm.cmd ci
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
npx.cmd --no-install lhci autorun
1..3 | ForEach-Object { npx.cmd --no-install vitest run src/app; if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas' } }
npm.cmd run test:coverage -- --maxWorkers=2
```

Desde la raíz: `python scripts/check_docs.py`. Los archivos locales
`.lighthouseci/` se ignoran en Git; las evidencias anteriores se conservan.
Los contratos de API y las migraciones no cambian, por lo que no aplica
actualizar OpenAPI ni ejecutar pruebas del backend por este incremento.

Fuentes: [configuración oficial de LHCI](https://googlechrome.github.io/lighthouse-ci/docs/configuration.html)
y [CLI 0.15.1](https://github.com/GoogleChrome/lighthouse-ci/blob/v0.15.1/packages/cli/package.json).

[Índice del Sprint 4](<../Sprint 04/README.md>)

[← Volver al README principal](../../../README.md)
