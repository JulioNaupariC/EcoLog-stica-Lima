import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { createRequire } from 'node:module'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

// UI/keyboard/accessibility scenarios use intercepted synthetic HTTP; no database writes.
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const requireFrontend = createRequire(resolve(root, 'frontend/package.json'))
const { default: puppeteer } = await import(pathToFileURL(requireFrontend.resolve('puppeteer-core')))
const { snapshot } = await import(pathToFileURL(resolve(root, 'frontend/node_modules/lighthouse/core/index.js')))
const origin = process.env.ECL120_ORIGIN || 'http://127.0.0.1:5184'
const api = process.env.ECL120_API || 'http://127.0.0.1:8001'
const output = resolve(process.env.ECL120_BROWSER_OUTPUT || resolve(root, '.tmp-ecl120-browser'))
const fixtures = resolve(root, 'frontend/src/test/fixtures/rutas')
const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
const raw = JSON.parse((await readFile(resolve(fixtures, 'optimizacion-completada.json'), 'utf8')).replaceAll('2026-11-20', today))
const dashboard = JSON.parse(await readFile(resolve(fixtures, 'sostenibilidad-con-datos.json'), 'utf8'))
const records = []
await mkdir(output, { recursive: true })
const save = (name, value) => writeFile(resolve(output, name), JSON.stringify(value, null, 2) + '\n')
const click = (page, name) => page.locator(`button::-p-text(${name})`).click()
async function login(page, email = 'synthetic@example.test') {
  await page.setViewport({ width: 1280, height: 900 })
  await page.goto(origin + '/login'); await page.waitForSelector('#login-email')
  await page.type('#login-email', email); await page.type('#login-password', 'synthetic-password')
  await page.locator('button[type="submit"]').click()
  await page.waitForFunction(() => document.querySelector('main h1')?.textContent === 'Inicio')
  await page.locator('a[href="/operacion/rutas"]').click(); await page.waitForSelector('.route-stop-list')
  await click(page, 'Ocultar mapa')
}
async function checkBrowser(name, launchOptions) {
  const browser = await puppeteer.launch({ headless: true, ...launchOptions })
  try {
    const page = await browser.newPage(), version = await browser.version()
    await page.setViewport({ width: 1280, height: 900 })
    await page.setRequestInterception(true)
    const plan = structuredClone(raw); plan.simulado = false; plan.rutas = [plan.rutas[0]]
    const route = plan.rutas[0]; route.estado = 'PLANIFICADA'; route.paradas = route.paradas.slice(0, 2).map(s => ({ ...s, estado: 'PENDIENTE' }))
    let role = 'OPERADOR', failNext = '', patchCalls = 0, closeCalls = 0
    page.on('dialog', async dialog => { await dialog.dismiss(); throw new Error('Unexpected window.confirm') })
    page.on('request', async request => {
      const url = new URL(request.url())
      if (url.origin !== api) { void request.continue(); return }
      const headers = { 'Access-Control-Allow-Origin': origin, 'Access-Control-Allow-Credentials': 'true', 'Access-Control-Allow-Headers': 'content-type', 'Access-Control-Allow-Methods': 'GET,POST,PATCH,OPTIONS', 'Cache-Control': 'no-store' }
      if (request.method() === 'OPTIONS') { void request.respond({ status: 204, headers }); return }
      let body, status = 200
      if (url.pathname === '/login') body = { usuario_id: '123e4567-e89b-42d3-a456-426614174000', rol: role }
      else if (url.pathname === '/optimizaciones') body = { items: [plan], page: 1, page_size: 12, total: 1, simulado: false }
      else if (url.pathname === `/optimizaciones/${plan.optimizacion_id}`) body = structuredClone(plan)
      else if (url.pathname.startsWith(`/rutas/${route.ruta_id}/paradas/`)) {
        patchCalls++
        if (failNext === 'time') { status = 422; body = { detail: { campo: 'atendida_en', motivo: 'La hora de atención no puede ser futura' } }; failNext = '' }
        else if (failNext === 'service') { status = 503; body = { detail: 'Servicio no disponible' }; failNext = '' }
        else {
          const stop = route.paradas.find(s => url.pathname.endsWith(s.parada_id)), payload = JSON.parse(await request.fetchPostData())
          assert(stop && role === 'OPERADOR'); stop.estado = payload.estado; route.estado = 'EN_CURSO'
          body = { ruta_id: route.ruta_id, parada_id: stop.parada_id, estado: stop.estado, atendida_en: payload.atendida_en ?? null, ruta_estado: route.estado }
        }
      } else if (url.pathname === `/rutas/${route.ruta_id}/cierre`) {
        closeCalls++
        if (failNext === 'conflict') { status = 409; route.paradas[1].estado = 'PENDIENTE'; body = { detail: 'Faltan 1 paradas por registrar' }; failNext = '' }
        else { route.estado = 'CERRADA'; body = { ruta_id: route.ruta_id, estado: 'CERRADA', cerrada_en: new Date().toISOString(), paradas_atendidas: 1, paradas_no_atendidas: 1 } }
      } else if (url.pathname === '/indicadores/sostenibilidad') body = { ...dashboard, periodo: { desde: url.searchParams.get('desde'), hasta: url.searchParams.get('hasta') } }
      else { status = 503; body = { detail: 'Servicio no incluido en esta prueba' } }
      void request.respond({ status, headers, contentType: 'application/json', body: JSON.stringify(body) })
    })
    await login(page)
    assert.equal(await page.$eval('.route-execution > button', button => button.disabled), true)
    await click(page, 'Registrar resultado de parada 1')
    const timeId = `outcome-${route.paradas[0].parada_id}-time`, state2 = `outcome-${route.paradas[1].parada_id}-state`
    await page.waitForFunction(id => document.activeElement?.id === id, {}, timeId)
    const proposal = await page.$eval(`#${timeId}`, input => input.value)
    for (const theme of ['light', 'dark']) {
      for (const width of [1280, 360]) {
        await page.setViewport({ width, height: 900 })
        await page.evaluate(theme => { document.documentElement.dataset.theme = theme }, theme)
        await page.evaluate(async () => {
          await document.fonts.ready
          await Promise.all(document.getAnimations().filter(animation => animation.effect?.getTiming().iterations !== Infinity).map(animation => animation.finished.catch(() => {})))
        })
        await page.addScriptTag({ path: requireFrontend.resolve('axe-core/axe.min.js') })
        const audit = await page.evaluate(async () => {
          const result = await window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] } })
          return { violations: result.violations, incomplete: result.incomplete.map(x => ({ id: x.id, targets: x.nodes.map(n => n.target) })), passes: result.passes.length }
        })
        const dimensions = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth }))
        const key = `${name}-${theme}-${width}`
        await save(`axe-${key}.json`, audit)
        await page.$eval('.stop-outcome-form', element => element.scrollIntoView({ block: 'center' }))
        await page.screenshot({ path: resolve(output, `${key}.png`) })
        records.push({ browser: name, version, theme, ...dimensions, axeViolations: audit.violations.length, axeIncomplete: audit.incomplete.length })
        assert.equal(audit.violations.length, 0, `${key}: ${audit.violations.map(v => v.id)}`); assert.equal(dimensions.scroll, width, `${key}: overflow`)
      }
      if (name === 'chrome') {
        await page.setViewport({ width: 1280, height: 900 })
        const result = await snapshot(page, { flags: { onlyCategories: ['accessibility'], formFactor: 'desktop', screenEmulation: { disabled: true }, logLevel: 'error' } })
        await save(`lighthouse-${theme}.json`, result.lhr)
        const failed = Object.values(result.lhr.audits).filter(a => a.score === 0 && a.scoreDisplayMode !== 'notApplicable').map(a => a.id)
        records.push({ browser: name, theme, lighthouseMode: result.lhr.gatherMode, accessibility: result.lhr.categories.accessibility.score, failed })
        assert.equal(result.lhr.categories.accessibility.score, 1, failed.join(', '))
      }
    }
    const setTime = value => page.evaluate(({ id, value }) => {
      const input = document.getElementById(id), setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
      setter.call(input, value); input.dispatchEvent(new Event('input', { bubbles: true }))
    }, { id: timeId, value })
    const tomorrow = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(Date.now() + 86400000))
    await setTime(`${tomorrow}T23:59:59`); await click(page, 'Guardar resultado de parada 1')
    await page.waitForSelector('.field-error[role="alert"]'); assert.equal(patchCalls, 0)
    await page.waitForFunction(id => document.activeElement?.id === id, {}, timeId)
    await setTime(proposal); failNext = 'time'; await click(page, 'Guardar resultado de parada 1')
    await page.waitForFunction(() => document.querySelector('.field-error')?.textContent.includes('no puede ser futura'))
    await page.waitForFunction(id => document.activeElement?.id === id, {}, timeId)
    failNext = 'service'; await click(page, 'Guardar resultado de parada 1')
    await page.waitForFunction(() => document.activeElement?.getAttribute('role') === 'alert')
    assert.equal(await page.$eval(`#${timeId}`, input => input.matches(':disabled')), true)
    assert.equal(await page.$eval(`#${timeId}`, input => input.value), proposal)
    await click(page, 'Actualizar estado de la ruta')
    await page.waitForFunction(id => !document.getElementById(id).matches(':disabled'), {}, timeId)
    await click(page, 'Guardar resultado de parada 1')
    await page.waitForFunction(id => !document.getElementById(id), {}, timeId)
    await page.waitForFunction(() => document.activeElement?.getAttribute('role') === 'status')
    async function secondStop() {
      await click(page, 'Registrar resultado de parada 2'); await page.select(`#${state2}`, 'NO_ATENDIDA')
      await click(page, 'Guardar resultado de parada 2'); await page.waitForFunction(id => !document.getElementById(id), {}, state2)
    }
    await secondStop()
    await click(page, 'Cerrar ruta'); await page.waitForFunction(() => document.activeElement?.textContent === 'Cancelar cierre')
    await page.keyboard.press('Enter'); assert.equal(closeCalls, 0)
    await page.waitForFunction(() => document.activeElement?.textContent === 'Cerrar ruta')
    await click(page, 'Cerrar ruta'); failNext = 'conflict'; await click(page, 'Confirmar cierre')
    await page.waitForFunction(() => document.activeElement?.getAttribute('role') === 'alert')
    await click(page, 'Actualizar estado de la ruta'); await page.waitForSelector(`button::-p-text(Registrar resultado de parada 2)`)
    assert.equal(await page.$eval('.route-execution > button', button => button.disabled), true)
    await secondStop(); await click(page, 'Cerrar ruta')
    await page.waitForFunction(() => document.activeElement?.textContent === 'Cancelar cierre')
    await page.keyboard.press('Tab'); await page.keyboard.press(' ')
    await page.waitForFunction(() => document.querySelector('.route-execution')?.textContent.includes('Ruta cerrada el'))
    assert.equal(closeCalls, 2); assert.equal(await page.$('.stop-outcome-form'), null)
    role = 'ADMINISTRADOR'; await login(page)
    assert.equal(await page.$('.stop-outcome-form'), null)
    assert.equal(await page.$('.route-close-confirm'), null)
    assert(!await page.$eval('.route-execution', element => element.textContent.includes('Cerrar ruta')))
    records.push({ browser: name, keyboard: true, timeValidationNoRequest: true, server422Focus: true, service503BlocksUntilRefresh: true,
      conflict409Refresh: true, closedRouteReadOnly: true, administratorReadOnly: true, nativeConfirmationUsed: false })
    console.log(JSON.stringify({ browser: name, version, status: 'passed' }))
  } finally { await browser.close() }
}
try {
  await checkBrowser('chrome', { executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe' })
  await checkBrowser('firefox', { browser: 'firefox', executablePath: 'C:/Program Files/Mozilla Firefox/firefox.exe' })
  const sourceHashes = {}
  for (const file of ['frontend/src/components/RouteExecution.tsx', 'frontend/src/components/StopOutcomeForm.tsx', 'frontend/src/services/routeOutcomes.ts', 'frontend/src/pages/OperationRoutesPage.tsx', 'frontend/src/styles/routeExecution.css']) sourceHashes[file] = createHash('sha256').update(await readFile(resolve(root, file))).digest('hex')
  await save('results.json', { status: 'passed', date: new Date().toISOString(), source: 'SPA real, HTTP sintético interceptado; la prueba real de BD se registra separadamente', sourceHashes, records })
} catch (error) { await save('failure.json', { message: error instanceof Error ? error.message : String(error), records }); throw error }
