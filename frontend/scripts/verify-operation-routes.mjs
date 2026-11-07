import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { createRequire } from 'node:module'
import { access, mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

// ECL-14: actual SPA + Leaflet, intercepted HTTP contract with ST-045 fixtures.
// This does not claim backend integration, a real optimizer or a live traffic provider.
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const tools = resolve(process.env.ECL14_TOOLS || resolve(root, '.tmp-ecl14-browser/node_modules'))
const output = resolve(process.env.ECL14_OUTPUT || resolve(root, '.tmp-ecl14-browser/results'))
const origin = process.env.ECL14_ORIGIN || 'http://127.0.0.1:5184'
const requireFrontend = createRequire(resolve(root, 'frontend/package.json'))
const { chromium, firefox } = await import(pathToFileURL(resolve(tools, 'playwright/index.mjs')))
const { default: puppeteer } = await import(pathToFileURL(requireFrontend.resolve('puppeteer-core')))
const { snapshot } = await import(pathToFileURL(resolve(root, 'frontend/node_modules/lighthouse/core/index.js')))
const fixtures = resolve(root, 'frontend/src/test/fixtures/rutas')
const load = async name => JSON.parse(await readFile(resolve(fixtures, name), 'utf8'))
const completed = await load('optimizacion-completada.json')
const progress = await load('optimizacion-en-proceso.json')
const failed = await load('optimizacion-fallida.json')
const records = []
let browser
let currentPage
await mkdir(output, { recursive: true })
async function save(name, body) { await writeFile(resolve(output, name), JSON.stringify(body, null, 2) + '\n', { flag: 'wx' }) }
const sourceHashes = {}
for (const path of ['frontend/src/pages/OperationRoutesPage.tsx', 'frontend/src/components/OperationRouteMap.tsx',
  'frontend/src/components/OperationRouteDetail.tsx', 'frontend/src/domain/operationRoutes.ts',
  'frontend/src/services/operationRoutes.ts', 'frontend/package-lock.json', 'frontend/scripts/verify-operation-routes.mjs']) {
  sourceHashes[path] = createHash('sha256').update(await readFile(resolve(root, path))).digest('hex')
}
await save('run-start.json', { ticket: 'ECL-14', at: new Date().toISOString(), origin,
  baseCommit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(), sourceHashes,
  source: 'intercepted ST-045 fixtures; no actual login or backend', traffic: 'SIN_DATOS', liveTiles: 'OpenStreetMap; degradation tested separately' })

async function prepare(context) {
  await context.route('http://127.0.0.1:8000/**', async route => {
    const request = route.request(), url = new URL(request.url())
    if (request.method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Credentials': 'true', 'Access-Control-Allow-Headers': 'content-type', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS' } })
      return
    }
    let body, status = 200
    if (url.pathname === '/login' && request.method() === 'POST') {
      body = { usuario_id: '123e4567-e89b-42d3-a456-426614174000', rol: 'OPERADOR' }
    } else if (url.pathname === '/optimizaciones') {
      const items = [completed, progress, failed].filter(d => d.fecha_operacion === url.searchParams.get('fecha'))
        .map(({ optimizacion_id, estado, fecha_operacion, solicitada_en, resumen }) => ({ optimizacion_id, estado, fecha_operacion, solicitada_en, resumen }))
      body = { items, total: items.length, page: Number(url.searchParams.get('page')), page_size: 12, simulado: true }
    } else if (url.pathname.startsWith('/optimizaciones/')) {
      body = [completed, progress, failed].find(d => url.pathname.endsWith(d.optimizacion_id))
      if (!body) { status = 404; body = { detail: 'Optimización no encontrada' } }
    } else { status = 503; body = { detail: 'Servicio no incluido en esta prueba' } }
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body),
      headers: { 'Access-Control-Allow-Origin': origin, 'Access-Control-Allow-Credentials': 'true', 'Access-Control-Allow-Headers': 'content-type', 'Cache-Control': 'no-store' } })
  })
}
async function openPlan(page) {
  await page.goto(origin + '/login')
  await page.getByLabel('Correo electrónico', { exact: true }).fill('synthetic@example.test')
  await page.getByLabel('Contraseña', { exact: true }).fill('synthetic-password')
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
  await page.getByRole('heading', { name: 'Inicio', exact: true }).waitFor()
  const drawer = page.getByRole('button', { name: 'Abrir menú', exact: true })
  if (await drawer.isVisible()) await drawer.click()
  await page.getByRole('link', { name: 'Rutas y alertas', exact: true }).click()
  await page.getByLabel('Fecha de operación', { exact: true }).fill('2026-11-20')
  await page.getByRole('heading', { name: 'Ruta ECO-101', exact: true }).waitFor()
  await page.locator('.route-stop-pin').first().waitFor()
  assert.equal(await page.locator('.route-stop-pin').count(), completed.rutas[0].paradas.length)
  assert(await page.locator('.leaflet-overlay-pane path').count() > 0, 'Polyline was not rendered')
  assert.equal(await page.locator('.route-stop-pin').first().textContent(), '1')
  await page.getByRole('link', { name: 'OpenStreetMap contributors', exact: true }).waitFor()
}
async function audit(page, engine, theme, width) {
  await page.setViewportSize({ width, height: 900 })
  await page.evaluate(value => { document.documentElement.dataset.theme = value }, theme)
  await page.evaluate(async () => { await document.fonts.ready; await Promise.all(document.getAnimations().filter(a => a.effect?.getTiming().iterations !== Infinity).map(a => a.finished.catch(() => {}))) })
  await page.addScriptTag({ path: requireFrontend.resolve('axe-core/axe.min.js') })
  const axe = await page.evaluate(async () => {
    const r = await window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] } })
    return { violations: r.violations, incomplete: r.incomplete.map(x => ({ id: x.id, targets: x.nodes.map(n => n.target) })), passes: r.passes.length }
  })
  const dimensions = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth }))
  const key = `${engine}-${theme}-${width}`
  await save(`axe-${key}.json`, axe)
  await page.screenshot({ path: resolve(output, `${key}.png`), fullPage: true, animations: 'disabled' })
  records.push({ engine, theme, ...dimensions, axeViolations: axe.violations.length, axeIncomplete: axe.incomplete.length })
  assert.equal(dimensions.scrollWidth, width, `Horizontal overflow: ${key}`)
  assert.equal(axe.violations.length, 0, `Axe violations: ${key}: ${axe.violations.map(v => v.id)}`)
}
try {
  browser = await puppeteer.launch({ executablePath: process.env.ECL14_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true })
  const puppeteerPage = (await browser.pages())[0]
  await puppeteerPage.goto(origin + '/login')
  const connected = await chromium.connectOverCDP(browser.wsEndpoint())
  const context = connected.contexts()[0]
  await prepare(context)
  const page = context.pages().find(p => p.url().startsWith(origin))
  assert(page)
  currentPage = page
  page.on('requestfailed', request => {
    const url = new URL(request.url())
    records.push({ failedRequest: url.origin + url.pathname, reason: request.failure()?.errorText })
  })
  await openPlan(page)
  for (const theme of ['light', 'dark']) {
    await audit(page, 'chrome', theme, 1280)
    const result = await snapshot(puppeteerPage, { flags: { onlyCategories: ['accessibility'], formFactor: 'desktop', screenEmulation: { disabled: true }, logLevel: 'error' } })
    await save(`lighthouse-${theme}.json`, result.lhr)
    const failures = Object.values(result.lhr.audits).filter(a => a.score === 0 && a.scoreDisplayMode !== 'notApplicable')
    records.push({ engine: 'chrome', theme, lighthouseMode: result.lhr.gatherMode, lighthouseAccessibility: result.lhr.categories.accessibility.score, failures: failures.map(a => a.id) })
    assert.equal(result.lhr.categories.accessibility.score, 1, `Lighthouse accessibility: ${failures.map(a => a.id)}`)
    await audit(page, 'chrome', theme, 360)
  }
  await page.getByRole('link', { name: 'Ir a la lista accesible de paradas', exact: true }).focus()
  await page.keyboard.press('Enter')
  assert(await page.getByRole('heading', { name: 'Secuencia de paradas', exact: true }).evaluate(e => e === document.activeElement))
  await page.keyboard.press('Tab')
  assert(await page.getByRole('button', { name: 'Ver parada 1 en mapa', exact: true }).evaluate(e => e === document.activeElement))
  await context.route('https://tile.openstreetmap.org/**', route => route.abort())
  await page.getByRole('button', { name: 'Ocultar mapa', exact: true }).click()
  await page.getByRole('button', { name: 'Mostrar mapa', exact: true }).click()
  await page.getByRole('button', { name: 'Acercar mapa', exact: true }).click()
  await page.getByText('No se pudieron cargar las teselas.', { exact: false }).waitFor()
  assert.equal(await page.locator('.route-stop-list > li').count(), completed.rutas[0].paradas.length)
  await page.getByRole('button', { name: 'Ver parada 1 en mapa', exact: true }).click()
  await page.locator('.leaflet-popup').waitFor()
  assert(await page.getByRole('region', { name: 'Mapa de ruta ECO-101', exact: true }).evaluate(e => e === document.activeElement))
  records.push({ engine: 'chrome', tileFailureRetainsList: true, keyboardList: true })
  for (const [date, text] of [['2026-11-22', 'Sin optimizaciones en esta fecha'], ['2026-11-21', 'La optimización está en proceso.'], ['2026-11-19', 'La optimización falló']]) {
    await page.getByLabel('Fecha de operación', { exact: true }).fill(date)
    await page.getByText(text, { exact: false }).waitFor()
    assert.equal(await page.locator('.operation-route-map').count(), 0)
  }
  records.push({ engine: 'chrome', emptyLoadingFailedDistinct: true })
  const chromeVersion = await browser.version()
  await browser.close(); browser = null
  browser = await firefox.launch({ headless: true })
  const firefoxVersion = browser.version()
  const ffContext = await browser.newContext({ serviceWorkers: 'block' })
  await prepare(ffContext)
  const ffPage = await ffContext.newPage()
  await openPlan(ffPage)
  for (const width of [1280, 360]) await audit(ffPage, 'firefox', 'light', width)
  await save('results.json', { source: 'ST-045 synthetic HTTP responses; not backend or provider integration', chromeVersion, firefoxVersion, records })
  console.log(JSON.stringify({ status: 'passed', chromeVersion, firefoxVersion, records }, null, 2))
} catch (error) {
  if (currentPage && !currentPage.isClosed()) {
    await currentPage.screenshot({ path: resolve(output, 'failure.png'), fullPage: true })
    records.push({ bodyText: await currentPage.locator('body').innerText() })
  }
  await save('failure.json', { message: error instanceof Error ? error.message : 'Verification failed', records })
  throw error
} finally { await browser?.close() }
