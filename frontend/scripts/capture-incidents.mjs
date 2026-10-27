// ECL-74: browser evidence with a synthetic local HTTP API (no real credentials).
// Build with VITE_API_BASE_URL=http://127.0.0.1:8000 and serve `npm run preview`.
// Install playwright-core externally; pass CAPTURE_PLAYWRIGHT_MODULE if needed.
import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { createServer } from 'node:http'
import { execFileSync } from 'node:child_process'

const modulePath = process.env.CAPTURE_PLAYWRIGHT_MODULE || 'node_modules/.ecl74-browser/node_modules/playwright-core/index.mjs'
const { chromium, firefox } = await import(pathToFileURL(resolve(modulePath)).href)
const origin = process.env.CAPTURE_ORIGIN || 'http://127.0.0.1:5173'
assert.equal(new URL(origin).hostname, '127.0.0.1')
const output = resolve(process.env.ECL74_OUTPUT || '../docs/03 Implementación/Sprint 03/validaciones/evidencias/ECL-74')
assert.equal(execFileSync('git', ['ls-files', '--', output], { encoding: 'utf8' }).trim(), '',
  'Historical evidence must not be overwritten. Set ECL74_OUTPUT to a new directory.')
await mkdir(output, { recursive: true })
const owner = '123e4567-e89b-42d3-a456-426614174005'
const stop = '123e4567-e89b-42d3-a456-426614174006'
const results = []
let operations = new Map()
let posts = []
const fixtureApi = createServer(async (request, response) => {
  response.setHeader('Access-Control-Allow-Origin', origin)
  response.setHeader('Access-Control-Allow-Credentials', 'true')
  response.setHeader('Access-Control-Allow-Headers', 'Content-Type')
  response.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
  response.setHeader('Content-Type', 'application/json')
  response.setHeader('Cache-Control', 'no-store')
  if (request.method === 'OPTIONS') { response.writeHead(204).end(); return }
  if (request.url === '/conductor/itinerario') {
    response.end(JSON.stringify({ owner_id: owner, stops: [{ stop_id: stop, position: 1,
      status: 'EN_RUTA', delivery: { address: 'Dirección sintética de prueba', reference: null,
        window_start: '2026-10-26T08:00:00-05:00', window_end: '2026-10-26T10:00:00-05:00',
        latitud: -12.0464, longitud: -77.0428 } }] }))
  } else if (request.url === '/conductor/incidencias' && request.method === 'POST') {
    let raw = ''
    for await (const chunk of request) raw += chunk
    const payload = JSON.parse(raw)
    posts.push(payload)
    const existing = operations.get(payload.operation_id)
    const ack = existing || { incidencia_id: crypto.randomUUID(), operation_id: payload.operation_id,
      estado: 'PENDIENTE_VALIDACION', registrada_en: new Date().toISOString() }
    operations.set(payload.operation_id, ack)
    response.writeHead(existing ? 200 : 201).end(JSON.stringify(ack))
  } else response.end('{}')
})
await new Promise((resolve, reject) => { fixtureApi.once('error', reject); fixtureApi.listen(8000, '127.0.0.1', resolve) })

try {
for (const [name, engine, options] of [
  ['chrome', chromium, { executablePath: process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe' }],
  ['firefox', firefox, {}],
]) {
  const browser = await engine.launch({ headless: true, ...options })
  try {
    for (const colorScheme of ['light', 'dark']) {
      const context = await browser.newContext({ viewport: { width: 360, height: 800 }, colorScheme })
      operations = new Map()
      posts = []
      await context.addInitScript(({ owner }) => {
        sessionStorage.setItem('ecologistica-driver-tab', JSON.stringify({ usuario_id: owner,
          rol: 'CONDUCTOR', expires_at: new Date(Date.now() + 3_600_000).toISOString() }))
        Object.defineProperty(navigator, 'geolocation', { value: {
          getCurrentPosition: (_ok, error) => error({ code: 1, message: 'Synthetic denied GPS' }),
        } })
      }, { owner })
      const page = await context.newPage()
      const errors = []
      page.on('pageerror', error => errors.push(error.message))
      const screenshot = async state => {
        await page.evaluate(() => scrollTo(0, 0))
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'No horizontal overflow at 360px')
        await page.screenshot({ path: resolve(output, `${name}-${colorScheme}-360-${state}.png`), fullPage: true })
      }
      await page.goto(`${origin}/conductor/itinerario`)
      await page.getByRole('heading', { name: 'Parada 1', exact: true }).waitFor()
      await page.getByRole('link', { name: 'Reportar incidencia' }).click()
      await page.getByLabel('Tipo', { exact: true }).waitFor()
      await page.getByRole('button', { name: 'Enviar incidencia' }).click()
      await page.getByText('Selecciona el tipo de incidencia.', { exact: true }).waitFor()
      assert.equal(await page.locator('#tipo').evaluate(element => element === document.activeElement), true)
      await screenshot('faltantes')
      await page.getByLabel('Tipo', { exact: true }).selectOption('AVERIA')
      await page.getByRole('radio', { name: /Alta/ }).focus()
      await page.keyboard.press('Space')
      assert.equal(await page.getByRole('radio', { name: /Alta/ }).isChecked(), true)
      await page.getByRole('button', { name: 'Usar mi ubicación' }).click()
      await page.getByText(/Puedes continuar con una parada/).waitFor()
      await page.getByLabel('Parada actual', { exact: true }).selectOption(stop)
      await page.getByLabel('Observación (opcional)', { exact: true }).fill('Avería sintética para validar ECL-74.')
      await page.getByText('Borrador guardado en este dispositivo.', { exact: true }).waitFor()
      await screenshot('formulario')
      // Wait for a production SW to control this route before the real offline reload.
      await page.evaluate(async () => {
        await navigator.serviceWorker.ready
        if (!navigator.serviceWorker.controller) await new Promise(resolve => navigator.serviceWorker.addEventListener('controllerchange', resolve, { once: true }))
      })
      await context.setOffline(true)
      await page.getByRole('button', { name: 'Enviar incidencia' }).click()
      await page.getByRole('heading', { name: 'Mis envíos' }).waitFor()
      await page.reload()
      await page.getByText('Pendiente de envío · se sincronizará al reconectar.', { exact: true }).waitFor()
      await screenshot('offline-recarga')
      assert.equal(posts.length, 0)
      await context.setOffline(false)
      await page.getByText(/Incidencia registrada · pendiente de validación/).waitFor()
      await screenshot('confirmada')
      assert.equal(operations.size, 1)
      assert.equal(new Set(posts.map(body => body.operation_id)).size, 1)
      assert.deepEqual(errors, [])
      results.push({ browser: name, version: browser.version(), colorScheme, width: 360,
        missingFieldFocus: true, keyboardRadio: true, gpsDeniedStopFallback: true,
        offlineReload: true, uniqueOperations: operations.size, posts: posts.length, pageErrors: errors })
      await context.close()
    }
  } finally { await browser.close() }
}
await writeFile(resolve(output, 'browser-results.json'), JSON.stringify({
  executedAt: new Date().toISOString(), mode: 'Synthetic local HTTP API; not Docker/backend E2E', results,
}, null, 2) + '\n')
console.log(JSON.stringify(results, null, 2))
} finally { await new Promise(resolve => fixtureApi.close(resolve)) }
