import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { createHash } from 'node:crypto'
import { fileURLToPath, pathToFileURL } from 'node:url'

// Run only through verify-route-execution-real.ps1, against its disposable database.
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const requireFrontend = createRequire(resolve(root, 'frontend/package.json'))
const { default: puppeteer } = await import(pathToFileURL(requireFrontend.resolve('puppeteer-core')))
const origin = process.env.ECL120_ORIGIN || 'http://127.0.0.1:5184'
const api = process.env.ECL120_API || 'http://127.0.0.1:8001'
const database = process.env.ECL120_ISOLATED_DATABASE
const password = process.env.ECL120_TEST_PASSWORD
assert(/^ecologistica_ecl120_\d+_demo$/u.test(database || ''), 'Disposable database marker required')
assert.equal(new URL(api).hostname, '127.0.0.1'); assert.equal(new URL(api).port, '8001')
assert.equal(new URL(origin).hostname, '127.0.0.1'); assert(password && password.length >= 12, 'Ephemeral test password required')
const output = resolve(process.env.ECL120_OUTPUT || resolve(root, '.tmp-ecl120-real'))
await mkdir(output, { recursive: true })
const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
const browser = await puppeteer.launch({ headless: true, executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe' })
const checks = []
try {
  const page = await browser.newPage()
  await page.setViewport({ width: 1280, height: 900 })
  page.on('dialog', async dialog => { await dialog.dismiss(); throw new Error('Unexpected native confirmation dialog') })
  await page.goto(origin + '/login')
  await page.waitForSelector('#login-email')
  await page.type('#login-email', 'operador.demo@ecologistica.example')
  await page.type('#login-password', password)
  await page.locator('button[type="submit"]').click()
  await page.waitForFunction(() => document.querySelector('main h1')?.textContent === 'Inicio')
  // Setup uses the existing optimization API; all outcome/closure writes use the UI.
  const setup = await page.evaluate(async ({ api, today }) => {
    const before = await fetch(`${api}/indicadores/sostenibilidad?desde=${today}&hasta=${today}`, { credentials: 'include' })
    const empty = await before.json()
    const request = await fetch(`${api}/optimizaciones`, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ fecha_operacion: today }) })
    const result = await request.json()
    if (request.status !== 201) return { status: request.status }
    const detail = await (await fetch(`${api}/optimizaciones/${result.optimizacion_id}`, { credentials: 'include' })).json()
    return { status: request.status, optimizationId: result.optimizacion_id, route: detail.rutas[0], emptyBefore: empty.con_datos === false, simulated: detail.simulado }
  }, { api, today })
  assert.equal(setup.status, 201, 'Optimization setup failed')
  assert.equal(setup.simulated, false); assert.equal(setup.emptyBefore, true)
  assert(setup.route?.paradas.length > 0)
  await page.locator('a[href="/operacion/rutas"]').click()
  await page.waitForSelector('.route-stop-list')
  await page.locator('button::-p-text(Ocultar mapa)').click()
  const routeId = setup.route.ruta_id
  const stops = setup.route.paradas
  assert.equal(await page.$eval('.route-execution > button', button => button.disabled), true)
  for (let index = 0; index < stops.length; index++) {
    const sequence = index + 1, base = `outcome-${stops[index].parada_id}`
    await page.locator(`button::-p-text(Registrar resultado de parada ${sequence})`).click()
    if (index !== 0) await page.select(`#${base}-state`, 'NO_ATENDIDA')
    else assert.equal(await page.$eval(`#${base}-time`, input => document.activeElement === input), true)
    await page.locator(`button::-p-text(Guardar resultado de parada ${sequence})`).click()
    await page.waitForFunction(sequence => ![...document.querySelectorAll('button')].some(button => button.textContent === `Guardar resultado de parada ${sequence}`), {}, sequence)
    await page.waitForFunction(() => document.activeElement?.getAttribute('role') === 'status')
  }
  checks.push({ name: 'UI registra resultados persistidos', attended: 1, notAttended: stops.length - 1 })
  await page.locator('button::-p-text(Cerrar ruta)').click()
  await page.waitForFunction(() => document.activeElement?.textContent === 'Cancelar cierre')
  await page.keyboard.press('Tab'); await page.keyboard.press('Enter')
  await page.waitForFunction(() => document.querySelector('.route-execution')?.textContent.includes('Ruta cerrada el'))
  assert.equal(await page.$('.stop-outcome-form'), null)
  await page.screenshot({ path: resolve(output, 'ruta-cerrada-real.png'), fullPage: true })
  const persisted = await page.evaluate(async ({ api, id, routeId, today }) => {
    const detail = await (await fetch(`${api}/optimizaciones/${id}`, { credentials: 'include' })).json()
    const route = detail.rutas.find(r => r.ruta_id === routeId)
    const repeat = await fetch(`${api}/rutas/${routeId}/cierre`, { method: 'POST', credentials: 'include' })
    const closure = await repeat.json()
    const response = await fetch(`${api}/indicadores/sostenibilidad?desde=${today}&hasta=${today}`, { credentials: 'include' })
    const body = await response.text(), indicators = JSON.parse(body)
    return { routeState: route.estado, stopStates: route.paradas.map(s => s.estado), repeatedCloseStatus: repeat.status,
      closedAt: closure.cerrada_en, attended: closure.paradas_atendidas, notAttended: closure.paradas_no_atendidas,
      withData: indicators.con_datos, simulated: indicators.simulado, routes: indicators.rutas_cerradas,
      versions: indicators.parametros_versiones, utf8Bytes: new TextEncoder().encode(body).length }
  }, { api, id: setup.optimizationId, routeId, today })
  assert.equal(persisted.routeState, 'CERRADA'); assert.equal(persisted.stopStates.filter(s => s === 'ATENDIDA').length, 1)
  assert.equal(persisted.stopStates.filter(s => s === 'NO_ATENDIDA').length, stops.length - 1)
  assert.equal(persisted.repeatedCloseStatus, 200); assert.equal(persisted.attended, 1); assert.equal(persisted.notAttended, stops.length - 1)
  assert.equal(persisted.withData, true); assert.equal(persisted.simulated, false); assert.equal(persisted.routes, 1)
  assert(persisted.versions.length > 0); assert(persisted.utf8Bytes <= 250000)
  await page.locator('a::-p-text(Ver dashboard de sostenibilidad)').click()
  await page.waitForSelector('.sustainability-page table')
  assert(!await page.$eval('.sustainability-page', element => element.textContent.includes('Datos de prueba')))
  await page.screenshot({ path: resolve(output, 'dashboard-real.png'), fullPage: true })
  checks.push({ name: 'GET confirma cierre, parada real, reintento idempotente y dashboard sin simular', ...persisted })
  const sourceHashes = {}
  for (const file of ['frontend/src/components/RouteExecution.tsx', 'frontend/src/components/StopOutcomeForm.tsx', 'frontend/src/services/routeOutcomes.ts', 'frontend/src/pages/OperationRoutesPage.tsx']) {
    sourceHashes[file] = createHash('sha256').update(await readFile(resolve(root, file))).digest('hex')
  }
  await writeFile(resolve(output, 'results.json'), JSON.stringify({ status: 'passed', date: new Date().toISOString(), browser: await browser.version(),
    source: 'UI real, API FastAPI real, PostgreSQL/PostGIS aislado con seed sintético; no usa la base demo del usuario', sourceHashes, checks }, null, 2) + '\n')
  console.log(JSON.stringify({ status: 'passed', routeClosed: true, dashboardWithData: true, simulated: false, stops: stops.length }))
} finally { await browser.close() }
