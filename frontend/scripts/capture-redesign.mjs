// Capturas antes/después de ECL-22 (rediseño UI) con los datos de seed_demo.py.
// Uso: node scripts/capture-redesign.mjs <antes|despues> [pantallas,separadas,por,comas]
// Ej.: node scripts/capture-redesign.mjs despues 02-inicio,07-itinerario (solo esas pantallas)
// Requiere API y vista previa locales sobre una base *_demo sembrada, Playwright
// (CAPTURE_PLAYWRIGHT_MODULE) y CAPTURE_PASSWORDS: archivo privado con
// SEED_DEMO_PASSWORD_ADMINISTRADOR y SEED_DEMO_PASSWORD_CONDUCTOR. No imprime credenciales.
import assert from 'node:assert/strict'
import { mkdir, readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const phase = process.argv[2]
assert(phase === 'antes' || phase === 'despues', 'Indica antes o despues')
const only = process.argv[3] ? new Set(process.argv[3].split(',')) : null
const origin = process.env.CAPTURE_ORIGIN || 'http://127.0.0.1:5173'
assert.equal(new URL(origin).hostname, '127.0.0.1')
const secrets = Object.fromEntries((await readFile(process.env.CAPTURE_PASSWORDS, 'utf8')).split(/\r?\n/u)
  .filter(line => line.includes('=')).map(line => [line.slice(0, line.indexOf('=')), line.slice(line.indexOf('=') + 1)]))
const { chromium } = await import(pathToFileURL(process.env.CAPTURE_PLAYWRIGHT_MODULE).href)
const output = resolve('evidencias/ECL-22-rediseno', phase)
await mkdir(output, { recursive: true })

const WIDTHS = [360, 768, 1280]
const SCHEMES = ['light', 'dark']
const ADMIN = { email: 'administrador.demo@ecologistica.example', password: secrets.SEED_DEMO_PASSWORD_ADMINISTRADOR }
const DRIVER = { email: 'conductor.demo@ecologistica.example', password: secrets.SEED_DEMO_PASSWORD_CONDUCTOR }

async function go(page, path) {
  // In-app navigation keeps the in-memory session (a reload would drop it).
  await page.evaluate(target => {
    history.pushState({}, '', target)
    window.dispatchEvent(new PopStateEvent('popstate'))
  }, path)
}
async function login(page, account) {
  await page.goto(origin + '/login')
  await page.getByLabel('Correo electrónico').fill(account.email)
  await page.getByLabel('Contraseña', { exact: true }).fill(account.password)
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
  await page.waitForURL(origin + '/')
  await page.waitForLoadState('networkidle')
}
async function pickClient(page) {
  await page.getByRole('combobox', { name: 'Cliente', exact: true }).fill('Bodega')
  await page.locator('[role="listbox"] [role="option"]').first().click()
}
async function shot(page, name, width, scheme) {
  if (only && !only.has(name)) return null
  await page.waitForLoadState('networkidle')
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
  if (phase === 'despues') assert.equal(overflow, false, `Desbordamiento horizontal en ${name} ${width}`)
  await page.screenshot({ path: resolve(output, `${name}-${width}-${scheme}.png`), fullPage: true, animations: 'disabled' })
  return { name, width, scheme, overflow }
}

const results = []
const browser = await chromium.launch({ headless: true, channel: 'chrome' })
try {
  for (const scheme of SCHEMES) {
    for (const width of WIDTHS) {
      const viewport = { width, height: width === 360 ? 780 : 900 }
      const admin = await browser.newContext({ viewport, colorScheme: scheme, timezoneId: 'America/Lima', locale: 'es-PE' })
      const page = await admin.newPage()
      await page.goto(origin + '/login')
      await page.getByRole('heading', { name: 'Iniciar sesión' }).waitFor()
      results.push(await shot(page, '01-login', width, scheme))
      await login(page, ADMIN)
      results.push(await shot(page, '02-inicio', width, scheme))
      await go(page, '/vehiculos')
      await page.getByText('DEMO-001', { exact: true }).first().waitFor()
      results.push(await shot(page, '03-vehiculos', width, scheme))
      await go(page, '/conductores')
      await page.getByText('Conductora Demo Uno', { exact: true }).first().waitFor()
      results.push(await shot(page, '04-conductores', width, scheme))
      await go(page, '/pedidos/nuevo')
      await pickClient(page)
      await page.getByText('Puerta junto al parque', { exact: true }).first().waitFor()
      results.push(await shot(page, '05-pedido', width, scheme))
      await go(page, '/clientes/preferencias')
      await pickClient(page)
      await page.getByRole('button', { name: 'Consultar preferencias', exact: true }).click()
      await page.getByRole('heading', { name: 'Preferencias del cliente', exact: true }).waitFor()
      results.push(await shot(page, '06-preferencias', width, scheme))
      await admin.close()

      const driver = await browser.newContext({ viewport, colorScheme: scheme, timezoneId: 'America/Lima', locale: 'es-PE' })
      const driverPage = await driver.newPage()
      await login(driverPage, DRIVER)
      await go(driverPage, '/conductor/itinerario')
      await driverPage.getByText('Pedido demo 01', { exact: true }).first().waitFor()
      results.push(await shot(driverPage, '07-itinerario', width, scheme))
      await driver.close()
    }
  }
} finally { await browser.close() }
const taken = results.filter(Boolean)
process.stdout.write(`${taken.length} capturas en ${output}\n`)
process.stdout.write(`Con desbordamiento horizontal: ${taken.filter(item => item.overflow).map(item => `${item.name}-${item.width}-${item.scheme}`).join(', ') || 'ninguna'}\n`)
