import assert from 'node:assert/strict'
import { access, mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

// ECL-75: read-only browser checks against the local demo. Never log credentials.
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const output = resolve(process.env.ECL75_OUTPUT || resolve(root,
  'docs/03 Implementación/Sprint 03/validaciones/evidencias/ECL-75'))
const modulePath = process.env.ECL75_PLAYWRIGHT_MODULE || resolve(root, '.tmp-ecl75/node_modules/playwright/index.mjs')
const axePath = process.env.ECL75_AXE_PATH || resolve(root, '.tmp-ecl75/node_modules/axe-core/axe.min.js')
const origin = 'http://127.0.0.1:5173'
const api = 'http://127.0.0.1:8000'
const settings = Object.fromEntries((await readFile(resolve(root, '.env'), 'utf8')).split(/\r?\n/u)
  .filter(line => /^SEED_DEMO_PASSWORD_[A-Z]+=/u.test(line)).map(line => {
    const separator = line.indexOf('=')
    return [line.slice(0, separator), line.slice(separator + 1)]
  }))
const { chromium } = await import(pathToFileURL(modulePath).href)
const checks = []
let phase = 'startup'
let browser

async function signIn(page, role) {
  assert(settings[`SEED_DEMO_PASSWORD_${role}`], 'Missing private demo setting')
  await page.goto(origin + '/login')
  await page.getByLabel('Correo electrónico', { exact: true }).fill(`${role.toLowerCase()}.demo@ecologistica.example`)
  await page.getByLabel('Contraseña', { exact: true }).fill(settings[`SEED_DEMO_PASSWORD_${role}`])
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
  await page.getByRole('heading', { name: 'Inicio', exact: true }).waitFor()
}

async function openIncidents(page) {
  const drawer = page.getByRole('button', { name: 'Abrir menú', exact: true })
  if (await drawer.isVisible()) await drawer.click()
  await page.getByRole('link', { name: 'Incidencias pendientes', exact: true }).click()
  await page.getByRole('table').waitFor()
}

async function theme(page, value) {
  await page.getByRole('button', { name: /^Cuenta:/u }).click()
  await page.getByRole('radio', { name: value === 'dark' ? 'Oscuro' : 'Claro', exact: true }).check()
  await page.keyboard.press('Escape')
  assert.equal(await page.locator('html').getAttribute('data-theme'), value)
}

async function snapshot(page, filename, source) {
  const dimensions = await page.evaluate(() => ({ viewport: innerWidth, scroll: document.documentElement.scrollWidth }))
  assert.equal(dimensions.scroll, dimensions.viewport, 'Page must reflow without horizontal scrolling')
  // Existing tracked evidence is immutable: fail instead of replacing an earlier run.
  const target = resolve(output, filename)
  let exists = false
  try { await access(target); exists = true } catch { /* A new capture is expected. */ }
  assert.equal(exists, false, 'Use a fresh ECL75_OUTPUT directory for another run')
  // Keep the sticky top bar at the top even after focusing a control far down the page.
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: target, fullPage: true, animations: 'disabled' })
  checks.push({ capture: filename, source, ...dimensions })
}

try {
  await mkdir(output, { recursive: true })
  browser = await chromium.launch({ channel: 'chrome', headless: true })
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: 'es-PE', timezoneId: 'America/Lima' })
  const page = await context.newPage()
  let pageErrors = 0
  page.on('pageerror', () => { pageErrors++ })
  phase = 'operator real API'
  await signIn(page, 'OPERADOR')
  await openIncidents(page)
  const response = await context.request.get(api + '/incidencias?estado=PENDIENTE_VALIDACION&page=1&page_size=20')
  assert.equal(response.status(), 200)
  const real = await response.json()
  assert(real.items.length > 0, 'Seed the local demo before running this check')
  assert.equal(await page.getByRole('row').count(), real.items.length + 1)
  for (let index = 1; index < real.items.length; index++) {
    assert(Date.parse(real.items[index - 1].ocurrida_en) >= Date.parse(real.items[index].ocurrida_en))
  }
  checks.push({ check: 'real-api-list', status: response.status(), visible: real.items.length, total: real.total })

  for (const width of [360, 1280]) {
    await page.setViewportSize({ width, height: 900 })
    for (const appearance of ['light', 'dark']) {
      phase = `${width} ${appearance}`
      await theme(page, appearance)
      await page.evaluate(() => window.scrollTo(0, 0))
      await snapshot(page, `chrome-${width}-${appearance}.png`, 'real API, local demo')
      await page.addScriptTag({ path: axePath })
      const audit = await page.evaluate(async () => {
        const result = await window.axe.run(document.querySelector('.incidents-page'), {
          runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] },
        })
        return { violations: result.violations.map(item => ({ id: item.id, impact: item.impact,
          targets: item.nodes.map(node => node.target) })), passes: result.passes.length }
      })
      checks.push({ check: 'automated-accessibility-page-only', width, appearance, ...audit })
      assert.equal(audit.violations.length, 0, 'Review page accessibility findings')
    }
  }

  phase = 'keyboard refresh and map link'
  await page.getByRole('button', { name: 'Actualizar listado', exact: true }).focus()
  await page.keyboard.press('Enter')
  await page.getByRole('table').waitFor()
  // Disabled buttons re-enable when the response arrives; tab into the table and its first map link.
  await page.getByRole('button', { name: 'Actualizar listado', exact: true }).focus()
  await page.keyboard.press('Tab')
  assert.equal(await page.locator(':focus').getAttribute('role'), 'region')
  await page.keyboard.press('Tab')
  const focusedMap = page.locator(':focus')
  assert.equal(await focusedMap.getAttribute('target'), '_blank')
  assert.equal(await focusedMap.getAttribute('rel'), 'noopener noreferrer')
  checks.push({ check: 'keyboard-refresh-table-map', passed: true })

  // These states are simulated at the browser boundary, never persisted to the demo database.
  let mode = 'empty'
  const example = real.items[0]
  await page.route('**/incidencias?**', async route => {
    if (mode === 'error' || mode === 'forbidden') {
      return route.fulfill({ status: mode === 'error' ? 503 : 403, contentType: 'application/json', body: '{}' })
    }
    if (mode === 'slow') await new Promise(done => setTimeout(done, 1600))
    let body = { items: [], page: 1, page_size: 20, total: 0 }
    if (mode === 'list' || mode === 'slow') body = real
    if (mode === 'long') body = { items: [{ ...example, observacion: 'Observación ficticia. ' + 'X'.repeat(350) }], page: 1, page_size: 20, total: 1 }
    if (mode === 'pagination') {
      const number = Number(new URL(route.request().url()).searchParams.get('page'))
      const all = Array.from({ length: 21 }, (_, index) => ({ ...example,
        incidencia_id: `00000000-0000-4000-8000-${String(index).padStart(12, '0')}` }))
      body = { items: all.slice((number - 1) * 20, number * 20), page: number, page_size: 20, total: 21 }
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })

  phase = 'simulated empty'
  await theme(page, 'light')
  await page.getByRole('button', { name: 'Actualizar listado', exact: true }).click()
  await page.getByRole('heading', { name: 'No hay incidencias pendientes de validación', exact: true }).waitFor()
  await snapshot(page, 'chrome-empty-1280.png', 'simulated GET response')

  phase = 'simulated error and retry'
  mode = 'error'
  await page.getByRole('button', { name: 'Actualizar listado', exact: true }).click()
  await page.getByRole('alert').waitFor()
  await snapshot(page, 'chrome-error-1280.png', 'simulated HTTP 503')
  mode = 'list'
  await page.getByRole('button', { name: 'Reintentar', exact: true }).click()
  await page.getByRole('table').waitFor()
  checks.push({ check: 'error-retry', passed: true, source: 'simulated GET responses' })

  phase = 'simulated forbidden'
  mode = 'forbidden'
  await page.getByRole('button', { name: 'Actualizar listado', exact: true }).click()
  await page.getByRole('alert').waitFor()
  assert((await page.getByRole('alert').innerText()).includes('Solo Administrador y Operador'))
  await snapshot(page, 'chrome-forbidden-1280.png', 'simulated HTTP 403')

  phase = 'simulated slow loading'
  mode = 'slow'
  await page.getByRole('button', { name: 'Reintentar', exact: true }).click()
  await page.locator('.incident-loading .skeleton').waitFor()
  await snapshot(page, 'chrome-loading-1280.png', 'simulated delayed GET response')
  await page.getByRole('table').waitFor()

  phase = 'simulated pagination'
  mode = 'pagination'
  await page.getByRole('button', { name: 'Actualizar listado', exact: true }).click()
  await page.getByText('Página 1 de 2', { exact: true }).waitFor()
  await page.getByRole('button', { name: 'Siguiente', exact: true }).focus()
  await page.keyboard.press('Enter')
  await page.getByText('Página 2 de 2', { exact: true }).waitFor()
  assert.equal(await page.getByRole('row').count(), 2)
  await page.getByRole('button', { name: 'Anterior', exact: true }).click()
  await page.getByText('Página 1 de 2', { exact: true }).waitFor()
  checks.push({ check: 'pagination-next-keyboard-previous', passed: true, source: '21 simulated incidents' })

  phase = 'long observation by keyboard at 360px'
  mode = 'long'
  await page.setViewportSize({ width: 360, height: 900 })
  await page.getByRole('button', { name: 'Actualizar listado', exact: true }).click()
  const summary = page.locator('.incident-observation summary')
  await summary.waitFor()
  await summary.focus()
  await page.keyboard.press('Enter')
  assert.equal(await page.locator('.incident-observation details').getAttribute('open'), '')
  await snapshot(page, 'chrome-observation-keyboard-360.png', 'simulated long observation, keyboard focus')
  assert.equal(pageErrors, 0)
  await context.request.post(api + '/logout')
  await context.close()

  for (const role of ['ADMINISTRADOR', 'ANALISTA', 'AUDITOR', 'CONDUCTOR']) {
    phase = `real role ${role}`
    const roleContext = await browser.newContext({ viewport: { width: 1280, height: 900 } })
    try {
      const rolePage = await roleContext.newPage()
      await signIn(rolePage, role)
      const permitted = role === 'ADMINISTRADOR'
      assert.equal(await rolePage.getByRole('link', { name: 'Incidencias pendientes', exact: true }).count(), permitted ? 1 : 0)
      const realResponse = await roleContext.request.get(api + '/incidencias?estado=PENDIENTE_VALIDACION&page=1&page_size=20')
      assert.equal(realResponse.status(), permitted ? 200 : 403)
      if (permitted) await openIncidents(rolePage)
      else {
        await rolePage.evaluate(() => {
          history.pushState(null, '', '/operacion/incidencias')
          dispatchEvent(new PopStateEvent('popstate'))
        })
        await rolePage.getByRole('heading', { name: 'Acceso denegado', exact: true }).waitFor()
      }
      checks.push({ check: 'real-role-access', role, status: realResponse.status(), menuAndRoute: 'passed' })
      await roleContext.request.post(api + '/logout')
    } finally { await roleContext.close() }
  }

  await writeFile(resolve(output, 'results.json'), JSON.stringify({
    ticket: 'ECL-75', executedAt: new Date().toISOString(), timezone: 'America/Lima',
    browser: await browser.version(), automatedAccessibilityScope: 'ECL-75 page only; not a full WCAG audit', checks,
  }, null, 2) + '\n', { flag: 'wx' })
  console.log(`ECL-75: ${checks.length} comprobaciones registradas; capturas guardadas sin credenciales.`)
} catch (error) {
  // Playwright diagnostics can include a fill() value. Keep failures free of private values.
  console.error(`ECL-75: falló la fase «${phase}» (${error.name}); detalles privados omitidos.`)
  await writeFile(resolve(root, '.tmp-ecl75/browser-failure.json'), JSON.stringify({ phase, checks }, null, 2) + '\n')
  process.exitCode = 1
} finally { await browser?.close() }
