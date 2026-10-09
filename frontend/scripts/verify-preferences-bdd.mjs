import assert from 'node:assert/strict'
import { readFile, mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

// Run only against a disposable preview with synthetic accounts and clients.
const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const root = resolve(frontend, '..')
const output = resolve(frontend, 'evidencias/ECL-54')
const settingsPath = process.env.ECL54_PREVIEW_SETTINGS || resolve(root, '.env.ecl54-preview')
const settings = Object.fromEntries((await readFile(settingsPath, 'utf8')).split(/\r?\n/u)
  .filter(line => line.includes('=')).map(line => {
    const index = line.indexOf('=')
    return [line.slice(0, index), line.slice(index + 1)]
  }))
for (const key of ['ORIGIN', 'API', 'ADMIN_EMAIL', 'ADMIN_PASSWORD', 'OPERATOR_EMAIL', 'OPERATOR_PASSWORD', 'DRIVER_EMAIL', 'DRIVER_PASSWORD', 'CLIENT_A', 'CLIENT_B']) {
  assert(settings['ECL54_' + key], 'Missing private preview configuration')
}
assert(settings.DATABASE_URL?.endsWith('/ecologistica_ecl54_preview_test'), 'Dedicated ECL54 synthetic preview required')
const origin = settings.ECL54_ORIGIN
const api = settings.ECL54_API
assert.equal(new URL(origin).hostname, '127.0.0.1')
assert.equal(new URL(api).hostname, '127.0.0.1')
const modulePath = process.env.ECL54_PLAYWRIGHT_MODULE || resolve(frontend, 'node_modules/.st027-browser-check/node_modules/playwright/index.mjs')
const { chromium, firefox } = await import(pathToFileURL(modulePath).href)
await mkdir(output, { recursive: true })
const results = []
let phase = 'startup'

async function authenticate(page, prefix) {
  await page.goto(origin + '/login')
  await page.getByLabel('Correo electrónico').fill(settings['ECL54_' + prefix + '_EMAIL'])
  await page.getByLabel('Contraseña', { exact: true }).fill(settings['ECL54_' + prefix + '_PASSWORD'])
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
  await page.getByRole('heading', { name: 'Rutas sostenibles para Lima' }).waitFor()
}
async function consult(page, id) {
  await page.getByLabel('ID del cliente', { exact: true }).fill(id)
  await page.getByRole('button', { name: 'Consultar preferencias', exact: true }).click()
  await page.getByRole('heading', { name: 'Preferencias del cliente', exact: true }).waitFor()
}
async function snapshot(page, filename) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
  assert.equal(overflow, false, 'Horizontal overflow')
  await page.screenshot({ path: resolve(output, filename), fullPage: true, animations: 'disabled' })
}
async function readPreferences(context, id) {
  const response = await context.request.get(`${api}/clientes/${id}/preferencias`)
  assert.equal(response.status(), 200)
  return response.json()
}
try {
  for (const [name, browserType, options, prefix] of [
    ['chrome', chromium, { channel: 'chrome' }, 'ADMIN'],
    ['firefox', firefox, {}, 'OPERATOR'],
  ]) {
    phase = name + ': launch'
    const browser = await browserType.launch({ headless: true, ...options })
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, timezoneId: 'America/Lima' })
    const errors = []
    const page = await context.newPage()
    page.on('pageerror', error => errors.push(error.name))
    const clientA = settings.ECL54_CLIENT_A
    const clientB = settings.ECL54_CLIENT_B
    try {
      await authenticate(page, prefix)
      // Reset only the two explicitly configured disposable synthetic fixtures.
      for (const id of [clientA, clientB]) {
        const reset = await context.request.patch(`${api}/clientes/${id}/preferencias`, {
          data: { horario_preferido: null, referencia: null, restriccion_acceso: null },
        })
        assert.equal(reset.status(), 200)
      }
      const otherPreferences = {"horario_preferido": "Tarde (preferido)", "referencia": "Recepcion principal", "restriccion_acceso": "Avisar al llegar"}
      assert.equal((await context.request.patch(`${api}/clientes/${clientB}/preferencias`, { data: otherPreferences })).status(), 200)
      await page.getByRole('link', { name: 'Preferencias de entrega', exact: true }).click()
      phase = name + ': empty preferences'
      await consult(page, clientA)
      assert.equal(await page.getByLabel('Sin horario preferido', { exact: true }).isChecked(), true)
      await snapshot(page, name + '-01-sin-preferencias.png')

      phase = name + ': valid save'
      for (const label of ['Sin horario preferido', 'Sin referencia de ubicación', 'Sin restricciones de acceso definidas']) {
        await page.getByLabel(label, { exact: true }).uncheck()
      }
      await page.getByLabel('Horario preferido', { exact: true }).fill('Lunes a viernes, de 09:00 a 12:00')
      await page.getByLabel('Referencia de ubicación', { exact: true }).fill(' Puerta verde frente al parque de prueba ')
      await page.getByLabel('Restricciones de acceso', { exact: true }).fill('Avisar a recepción. Ingreso por puerta lateral.')
      const save = page.waitForResponse(response => response.url() === `${api}/clientes/${clientA}/preferencias` && response.request().method() === 'PATCH')
      await page.getByRole('button', { name: 'Guardar preferencias', exact: true }).click()
      assert.equal((await save).status(), 200)
      await page.getByText('Preferencias guardadas correctamente.', { exact: true }).waitFor()
      const afterSave = await readPreferences(context, clientA)
      assert.equal(afterSave.referencia, ' Puerta verde frente al parque de prueba ')
      await snapshot(page, name + '-02-guardado.png')

      phase = name + ': retrieve saved data'
      await page.getByRole('button', { name: 'Consultar de nuevo u otro cliente', exact: true }).click()
      await consult(page, clientA)
      assert.equal(await page.getByLabel('Referencia de ubicación', { exact: true }).inputValue(), afterSave.referencia)
      await snapshot(page, name + '-03-recuperado.png')

      phase = name + ': local validation'
      await page.getByLabel('Horario preferido', { exact: true }).fill('A'.repeat(121))
      await page.getByRole('button', { name: 'Guardar preferencias', exact: true }).click()
      await page.getByText('Usa como máximo 120 caracteres.', { exact: true }).waitFor()
      assert.deepEqual(await readPreferences(context, clientA), afterSave)
      await snapshot(page, name + '-04-validacion.png')
      await page.getByRole('button', { name: 'Cancelar cambios', exact: true }).click()

      phase = name + ': explicit clear and isolation'
      await page.getByLabel('Sin restricciones de acceso definidas', { exact: true }).check()
      const clear = page.waitForResponse(response => response.url() === `${api}/clientes/${clientA}/preferencias` && response.request().method() === 'PATCH')
      await page.getByRole('button', { name: 'Guardar preferencias', exact: true }).click()
      const clearedResponse = await clear
      assert.equal(clearedResponse.status(), 200)
      assert.deepEqual(clearedResponse.request().postDataJSON(), { restriccion_acceso: null })
      await page.getByText('Preferencias guardadas correctamente.', { exact: true }).waitFor()
      const afterClear = await readPreferences(context, clientA)
      assert.equal(afterClear.restriccion_acceso, null)
      assert.equal(afterClear.horario_preferido, afterSave.horario_preferido)
      assert.deepEqual(await readPreferences(context, clientB), {
        cliente_id: clientB, ...otherPreferences,
      })

      phase = name + ': mobile and keyboard'
      await page.setViewportSize({ width: 360, height: 800 })
      await page.getByLabel('Horario preferido', { exact: true }).focus()
      await page.keyboard.press('Tab')
      assert.equal(await page.getByLabel('Sin horario preferido', { exact: true }).evaluate(element => element === document.activeElement), true)
      await snapshot(page, name + '-05-movil-360.png')

      phase = name + ': controlled server failure'
      const controlledError = route => route.request().method() === 'PATCH'
        ? route.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"Controlled test failure"}' })
        : route.continue()
      await page.route('**/clientes/*/preferencias', controlledError)
      await page.getByLabel('Referencia de ubicación', { exact: true }).fill('Conservar al fallar')
      await page.getByRole('button', { name: 'Guardar preferencias', exact: true }).click()
      await page.getByRole('alert').waitFor()
      assert.equal(await page.getByLabel('Referencia de ubicación', { exact: true }).inputValue(), 'Conservar al fallar')
      assert.deepEqual(await readPreferences(context, clientA), afterClear)
      await snapshot(page, name + '-06-error-503.png')
      await page.unroute('**/clientes/*/preferencias', controlledError)
      await page.getByRole('button', { name: 'Cancelar cambios', exact: true }).click()
      await page.getByRole('button', { name: 'Consultar de nuevo u otro cliente', exact: true }).click()
      await page.getByLabel('ID del cliente', { exact: true }).fill('00000000-0000-4000-8000-000000000053')
      await page.getByRole('button', { name: 'Consultar preferencias', exact: true }).click()
      await page.getByText('No se encontró el cliente. Revisa su identificador.', { exact: true }).waitFor()
      await snapshot(page, name + '-07-cliente-inexistente.png')

      phase = name + ': P8 order proposal gap'
      const preferenceRequests = []
      const monitor = request => {
        if (request.url().includes('/preferencias')) preferenceRequests.push(request.method())
      }
      page.on('request', monitor)
      await page.getByRole('link', { name: 'Registrar pedido', exact: true }).click()
      await page.getByRole('heading', { name: 'Registrar pedido', exact: true }).waitFor()
      await page.getByLabel('ID del cliente (UUID)', { exact: true }).fill(clientA)
      await page.getByLabel('Punto de referencia', { exact: true }).fill('Referencia propia del pedido')
      await page.locator('#ventana_inicio').fill('2026-10-10T09:00')
      await page.locator('#ventana_fin').fill('2026-10-10T11:00')
      await page.waitForLoadState('networkidle')
      assert.equal(await page.getByRole('button', { name: 'Usar como referencia del pedido', exact: true }).count(), 0)
      assert.equal(preferenceRequests.length, 0)
      assert.equal(await page.getByLabel('Punto de referencia', { exact: true }).inputValue(), 'Referencia propia del pedido')
      assert.equal(await page.locator('#ventana_inicio').inputValue(), '2026-10-10T09:00')
      await snapshot(page, name + '-09-P8-propuesta-ausente.png')
      page.off('request', monitor)

      phase = name + ': denied conductor'
      await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click()
      await page.getByRole('heading', { name: 'Iniciar sesión', exact: true }).waitFor()
      await authenticate(page, 'DRIVER')
      assert.equal(await page.getByRole('link', { name: 'Preferencias de entrega', exact: true }).count(), 0)
      await page.evaluate(() => {
        history.pushState({}, '', '/clientes/preferencias')
        window.dispatchEvent(new PopStateEvent('popstate'))
      })
      await page.getByRole('heading', { name: 'Acceso denegado', exact: true }).waitFor()
      assert.equal((await context.request.get(`${api}/clientes/${clientA}/preferencias`)).status(), 403)
      await snapshot(page, name + '-08-acceso-denegado.png')
      assert.equal(errors.length, 0)
      await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click()
      results.push({ browser: name, version: browser.version(), passed: true, role: prefix === 'ADMIN' ? 'ADMINISTRADOR' : 'OPERADOR',
        realLogin: true, realApiGetPatch: true, preferencesRetrieved: true, explicitClear: true, otherClientUnchanged: true, otherClientInitiallyPopulated: true, P8OrderProposalAvailable: false,
        localValidationPreservesData: true, unknownClient404: true, conductorDenied: true, mobileWidth: 360,
        horizontalOverflow: false, keyboardTab: true, pageErrors: 0,
        simulatedCase: 'PATCH 503 intercepted only for error display and preservation of unsaved values' })
    } finally { await context.close(); await browser.close() }
  }
  await writeFile(resolve(output, 'resultados.json'), JSON.stringify({ checkedAt: new Date().toISOString(),
    syntheticData: true, actualHttpApi: true, browsers: results }, null, 2) + '\n')
  process.stdout.write('Chrome and Firefox preferences flows passed.\n')
} catch {
  process.stderr.write('Preferences verification failed at phase: ' + phase + '. No credentials printed.\n')
  process.exitCode = 1
}
