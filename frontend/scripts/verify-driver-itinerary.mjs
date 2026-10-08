// Verificación local de ECL-56. Dependencia temporal: ver VALIDACION_ST030.md.
import assert from 'node:assert/strict'
import { readFile, mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const { chromium, firefox } = await import('../node_modules/.ecl56-browser-check/node_modules/playwright/index.mjs')
const privateFile = await readFile(new URL('../../.env.st030', import.meta.url), 'utf8')
const settings = Object.fromEntries(privateFile.split(/\r?\n/).filter((line) => line.includes('=')).map((line) => {
  const index = line.indexOf('=')
  return [line.slice(0, index), line.slice(index + 1)]
}))
assert(settings.ST030_DRIVER_EMAIL && settings.ST030_DRIVER_PASSWORD, 'Falta la cuenta privada local de conductor.')
const output = fileURLToPath(new URL('../evidencias/ECL-56/', import.meta.url))
await mkdir(output, { recursive: true })
const results = []

for (const [name, launcher, options] of [
  ['chrome', chromium, { channel: 'chrome' }],
  ['firefox', firefox, {}],
]) {
  let phase = 'iniciar navegador'
  const browser = await launcher.launch({ headless: true, ...options })
  const context = await browser.newContext({ viewport: { width: 360, height: 800 } })
  const page = await context.newPage()
  const pageErrors = []
  page.on('pageerror', () => pageErrors.push('Error de ejecución en página'))
  const screenshot = async (suffix) => page.screenshot({ path: output + '/' + name + '-' + suffix + '.png', fullPage: true })
  const checkWidth = async () => {
    const size = await page.evaluate(() => ({ viewport: window.innerWidth, content: document.documentElement.scrollWidth }))
    assert(size.content <= size.viewport, 'Desbordamiento horizontal')
  }
  try {
    phase = 'acceso anónimo'
    await page.goto('http://127.0.0.1:5173/conductor/itinerario')
    await page.getByRole('heading', { name: 'Iniciar sesión', exact: true }).waitFor()
    await screenshot('06-sin-sesion-360')
    phase = 'login real de conductor'
    await page.getByLabel('Correo electrónico').fill(settings.ST030_DRIVER_EMAIL)
    await page.getByLabel('Contraseña').fill(settings.ST030_DRIVER_PASSWORD)
    await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
    await page.getByRole('link', { name: 'Mi itinerario', exact: true }).click()
    await page.getByRole('heading', { name: 'Siguiente parada', exact: true }).waitFor()
    await page.getByText('Av. Abancay: +15 min previstos.', { exact: true }).waitFor()
    await checkWidth()
    await screenshot('01-itinerario-360')
    phase = 'detalle y regreso con teclado'
    await page.getByRole('button', { name: 'Ver detalle de parada', exact: true }).focus()
    await page.keyboard.press('Enter')
    await page.getByRole('heading', { name: 'Detalle de parada', exact: true }).waitFor()
    await page.getByText('DEMO-102', { exact: true }).waitFor()
    await checkWidth()
    await screenshot('02-detalle-360')
    await page.keyboard.press('Tab')
    assert(await page.getByRole('button', { name: 'Volver al itinerario' }).evaluate((element) => element === document.activeElement))
    await page.keyboard.press('Space')
    await page.getByRole('heading', { name: 'Mi itinerario', exact: true }).waitFor()
    phase = 'filtros y siguiente parada independiente'
    for (const state of ['PENDIENTE', 'EN_RUTA', 'ENTREGADO', 'DEMORADO']) {
      await page.getByLabel('Filtrar por estado').selectOption(state)
      assert.equal(await page.getByRole('button', { name: /^Ver parada/ }).count(), 1)
      assert((await page.getByRole('region', { name: 'Siguiente parada' }).textContent()).includes('Mercado Central'))
    }
    await checkWidth()
    await screenshot('03-filtro-360')
    phase = 'sin asignación y regreso'
    await page.getByRole('button', { name: 'Ver ejemplo sin asignación' }).click()
    await page.getByRole('heading', { name: 'Aún no tienes un itinerario' }).waitFor()
    await checkWidth()
    await screenshot('04-sin-asignacion-360')
    await page.getByRole('button', { name: 'Cargar ejemplo de itinerario' }).click()
    assert.equal(await page.getByRole('button', { name: /^Ver parada/ }).count(), 4)
    phase = 'escritorio'
    await page.setViewportSize({ width: 1280, height: 900 })
    await checkWidth()
    await screenshot('05-escritorio')
    phase = 'logout real'
    const logout = await context.request.post('http://127.0.0.1:8000/logout')
    assert.equal(logout.status(), 204)
    phase = 'rol no autorizado (login simulado)'
    await page.setViewportSize({ width: 360, height: 800 })
    await page.goto('http://127.0.0.1:5173/login')
    await page.route('http://127.0.0.1:8000/login', (route) => route.fulfill({
      status: 200, contentType: 'application/json',
      headers: { 'Access-Control-Allow-Origin': 'http://127.0.0.1:5173', 'Access-Control-Allow-Credentials': 'true' },
      body: JSON.stringify({ usuario_id: '123e4567-e89b-12d3-a456-426614174000', rol: 'AUDITOR' }),
    }))
    await page.getByLabel('Correo electrónico').fill('auditor@example.test')
    await page.getByLabel('Contraseña').fill('valor-ficticio-de-prueba')
    await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
    await page.getByRole('heading', { name: 'Rutas sostenibles para Lima' }).waitFor()
    assert.equal(await page.getByRole('link', { name: 'Mi itinerario' }).count(), 0)
    // Simula navegación SPA directa conservando la identidad en memoria.
    await page.evaluate(() => { history.pushState({}, '', '/conductor/itinerario'); window.dispatchEvent(new PopStateEvent('popstate')) })
    await page.getByRole('heading', { name: 'Acceso denegado', exact: true }).waitFor()
    await screenshot('07-auditor-denegado-360')
    assert.equal(pageErrors.length, 0)
    results.push({ browser: name, version: browser.version(), mobileWidth: 360, desktopWidth: 1280, result: 'passed', driverLogin: 'real', auditorLogin: 'simulated', horizontalOverflow: false })
    console.log(name + ' ' + browser.version() + ': flujo y capturas correctos')
  } catch {
    console.error(name + ': fallo en ' + phase + '. No se imprimen credenciales ni cookies.')
    process.exitCode = 1
  } finally {
    await context.close()
    await browser.close()
  }
}
await writeFile(output + '/resultados.json', JSON.stringify(results, null, 2) + '\n')
