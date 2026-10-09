import assert from 'node:assert/strict'
import { randomInt, randomUUID } from 'node:crypto'
import { readFile, mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const root = resolve(frontend, '..')
const output = resolve(frontend, 'evidencias/ECL-49')
const settings = Object.fromEntries((await readFile(resolve(root, '.env.ecl49-preview'), 'utf8'))
  .split(/\r?\n/u).filter(line => line.includes('=')).map(line => {
    const index = line.indexOf('='); return [line.slice(0, index), line.slice(index + 1)]
  }))
for (const prefix of ['ADMIN', 'OPERATOR', 'DRIVER']) {
  assert(settings['ECL49_' + prefix + '_EMAIL'] && settings['ECL49_' + prefix + '_PASSWORD'], 'Missing private preview credentials')
}
const modulePath = process.env.ECL49_PLAYWRIGHT_MODULE || resolve(frontend, 'node_modules/.ecl49-browser-check/node_modules/playwright/index.mjs')
const { chromium, firefox } = await import(pathToFileURL(modulePath).href)
const origin = 'http://127.0.0.1:5173'
const api = 'http://127.0.0.1:8000'
await mkdir(output, { recursive: true })
const results = []
let phase = 'startup'

async function authenticate(page, prefix) {
  await page.goto(origin + '/login')
  await page.getByLabel('Correo electrónico').fill(settings['ECL49_' + prefix + '_EMAIL'])
  await page.getByLabel('Contraseña', { exact: true }).fill(settings['ECL49_' + prefix + '_PASSWORD'])
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
  await page.getByRole('heading', { name: 'Rutas sostenibles para Lima' }).waitFor()
}
async function fillProfile(page, data) {
  for (const [field, value] of Object.entries(data)) await page.locator('#driver-' + field).fill(value)
}
async function snapshot(page, filename) {
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'Horizontal overflow')
  await page.screenshot({ path: resolve(output, filename), fullPage: true })
}

try {
  for (const [name, launcher, prefix] of [['chrome', chromium, 'ADMIN'], ['firefox', firefox, 'OPERATOR']]) {
    phase = name + ': launch'
    const browser = await launcher.launch(name === 'chrome' ? { channel: 'chrome', headless: true } : { headless: true })
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
    const page = await context.newPage()
    const errors = []
    page.on('pageerror', () => { errors.push('pageerror') })
    try {
      phase = name + ': real login'
      await authenticate(page, prefix)
      const delayed = async route => {
        await new Promise(yes => setTimeout(yes, 800))
        await route.continue()
      }
      await page.route('**/conductores?**', delayed)
      await page.getByRole('link', { name: 'Conductores', exact: true }).click()
      await page.getByText('Cargando conductores…', { exact: true }).waitFor()
      await snapshot(page, name + '-01-carga.png')
      await page.getByRole('button', { name: 'Actualizar listado' }).waitFor()
      await page.waitForFunction(() => !document.querySelector('[aria-busy="true"]'))
      await page.unroute('**/conductores?**', delayed)
      await snapshot(page, name + '-02-listado-inicial.png')
      await page.getByRole('button', { name: 'Nuevo conductor', exact: true }).click()
      await page.getByRole('heading', { name: 'Registrar conductor', exact: true }).waitFor()
      await snapshot(page, name + '-03-registro.png')
      await page.getByRole('button', { name: 'Registrar conductor', exact: true }).click()
      await page.getByRole('alert').waitFor()
      await snapshot(page, name + '-04-validacion.png')

      phase = name + ': real registration'
      const label = 'Conductor Prueba ' + name + ' ECL49 ' + randomInt(1000, 9999)
      const dni = String(randomInt(10000000, 99999999))
      const profile = {
        nombre: label, dni, licencia_numero: 'PRUEBA-49',
        licencia_vigente_hasta: name === 'firefox' ? '2000-01-01' : '2099-12-31',
        experiencia_anios: '4', telefono: '+51987654321', punto_partida: 'Base de prueba ECL49',
        disponible_desde: '2099-10-09T08:15:00.123', disponible_hasta: '2099-10-09T17:15',
        email: 'ecl49-' + randomUUID() + '@example.test', password: randomUUID(),
      }
      await fillProfile(page, profile)
      const post = page.waitForResponse(response => response.url() === api + '/conductores' && response.request().method() === 'POST')
      await page.getByRole('button', { name: 'Registrar conductor', exact: true }).click()
      const createdResponse = await post
      assert.equal(createdResponse.status(), 201)
      const created = await createdResponse.json()
      assert.equal(created.habilitado_asignacion, name === 'chrome')
      await page.getByText('Conductor registrado correctamente.', { exact: true }).waitFor()
      await page.waitForFunction(() => !document.querySelector('[aria-busy="true"]'))
      await snapshot(page, name + '-05-registro-confirmado.png')
      const before = await context.request.get(api + '/conductores/' + created.conductor_id)
      assert.equal(before.status(), 200)
      const original = await before.json()

      phase = name + ': real duplicate conflict'
      await page.getByRole('button', { name: 'Nuevo conductor', exact: true }).click()
      await fillProfile(page, { ...profile, email: 'ecl49-' + randomUUID() + '@example.test' })
      const duplicate = page.waitForResponse(response => response.url() === api + '/conductores' && response.request().method() === 'POST')
      await page.getByRole('button', { name: 'Registrar conductor', exact: true }).click()
      assert.equal((await duplicate).status(), 409)
      await page.getByRole('alert').waitFor()
      assert.equal(await page.locator('#driver-password').inputValue(), '')
      await snapshot(page, name + '-06-duplicado.png')
      await page.getByRole('button', { name: 'Cancelar', exact: true }).click()

      phase = name + ': real profile edit'
      await page.getByRole('button', { name: 'Ver y editar ' + label, exact: true }).click()
      await page.getByRole('heading', { name: 'Perfil de ' + label, exact: true }).waitFor()
      await snapshot(page, name + '-07-perfil.png')
      await page.getByLabel('Teléfono', { exact: true }).fill('+51987654322')
      const patched = page.waitForResponse(response => response.url() === api + '/conductores/' + created.conductor_id && response.request().method() === 'PATCH')
      await page.getByRole('button', { name: 'Guardar cambios', exact: true }).click()
      const patch = await patched
      assert.equal(patch.status(), 200)
      assert.deepEqual(patch.request().postDataJSON(), { telefono: '+51987654322' })
      await page.getByText('Conductor actualizado correctamente.', { exact: true }).waitFor()
      const after = await (await context.request.get(api + '/conductores/' + created.conductor_id)).json()
      assert.equal(after.disponible_desde, original.disponible_desde)
      assert.equal(after.telefono, '+51987654322')
      await page.waitForFunction(() => !document.querySelector('[aria-busy="true"]'))
      await snapshot(page, name + '-08-edicion-confirmada.png')

      phase = name + ': remove availability'
      await page.getByRole('button', { name: 'Ver y editar ' + label, exact: true }).click()
      await page.getByRole('heading', { name: 'Perfil de ' + label, exact: true }).waitFor()
      await page.getByRole('checkbox').check()
      const removed = page.waitForResponse(response => response.url() === api + '/conductores/' + created.conductor_id && response.request().method() === 'PATCH')
      await page.getByRole('button', { name: 'Guardar cambios', exact: true }).click()
      const removedResponse = await removed
      assert.equal(removedResponse.status(), 200)
      assert.deepEqual(removedResponse.request().postDataJSON(), { disponible_desde: null, disponible_hasta: null })
      await page.getByText('Conductor actualizado correctamente.', { exact: true }).waitFor()
      const withdrawn = await removedResponse.json()
      assert.equal(withdrawn.habilitado_asignacion, false)

      phase = name + ': mobile'
      await page.setViewportSize({ width: 360, height: 800 })
      await page.waitForFunction(() => !document.querySelector('[aria-busy="true"]'))
      await snapshot(page, name + '-09-listado-360.png')
      await page.getByRole('button', { name: 'Ver y editar ' + label, exact: true }).click()
      await page.getByRole('heading', { name: 'Perfil de ' + label, exact: true }).waitFor()
      await snapshot(page, name + '-10-perfil-360.png')
      await page.getByRole('button', { name: 'Cancelar', exact: true }).click()

      phase = name + ': controlled list error and retry'
      await page.route('**/conductores?**', route => route.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"Controlled test failure"}' }))
      await page.getByRole('button', { name: 'Actualizar listado', exact: true }).click()
      await page.getByRole('alert').waitFor()
      await snapshot(page, name + '-11-error-360.png')
      await page.unroute('**/conductores?**')
      await page.getByRole('button', { name: 'Reintentar carga', exact: true }).click()
      await page.waitForFunction(() => !document.querySelector('[aria-busy="true"]'))
      await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click()
      await page.getByRole('heading', { name: 'Iniciar sesión', exact: true }).waitFor()

      phase = name + ': conductor access denied'
      await authenticate(page, 'DRIVER')
      assert.equal(await page.getByRole('link', { name: 'Conductores', exact: true }).count(), 0)
      await page.evaluate(() => {
        history.pushState({}, '', '/conductores')
        window.dispatchEvent(new PopStateEvent('popstate'))
      })
      await page.getByRole('heading', { name: 'Acceso denegado', exact: true }).waitFor()
      await snapshot(page, name + '-12-conductor-denegado.png')
      assert.equal((await context.request.get(api + '/conductores')).status(), 403)
      assert.equal(errors.length, 0)
      await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click()
      results.push({ browser: name, version: browser.version(), role: prefix === 'ADMIN' ? 'ADMINISTRADOR' : 'OPERADOR',
        passed: true, realLogin: true, realRegistration: true, duplicateConflict: true, realPatch: true,
        unchangedTimestampPreserved: true, availabilityRemoved: true, mobileWidth: 360, desktopWidth: 1280,
        horizontalOverflow: false, pageErrors: 0, conductorDenied: true,
        controlledFailure: 'GET list 503 simulated for error/retry evidence' })
    } finally {
      await context.close()
      await browser.close()
    }
  }
  await writeFile(resolve(output, 'resultados.json'), JSON.stringify({ checkedAt: new Date().toISOString(),
    syntheticData: true, actualHttpApi: true, browsers: results }, null, 2) + '\n')
  process.stdout.write('Chrome and Firefox driver management flows passed.\n')
} catch {
  process.stderr.write('Driver browser verification failed at phase: ' + phase + '. No credentials printed.\n')
  process.exitCode = 1
}
