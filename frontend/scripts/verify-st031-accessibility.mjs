// Verificación reproducible de ECL-57 / ST-031. Requiere Vite en 127.0.0.1:5173.
import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const { chromium, firefox } = await import('../node_modules/.ecl57-browser-check/node_modules/playwright/index.mjs')
const output = fileURLToPath(new URL('../evidencias/ECL-57/', import.meta.url))
await mkdir(output, { recursive: true })

const results = []
const testUserId = '123e4567-e89b-42d3-a456-426614174000'

function luminance([red, green, blue]) {
  const channels = [red, green, blue].map((value) => {
    const channel = value / 255
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
}

function rgb(value) {
  const match = value.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)
  assert(match, `Color CSS no reconocido: ${value}`)
  return [Number(match[1]), Number(match[2]), Number(match[3])]
}

function contrast(foreground, background) {
  const light = Math.max(luminance(rgb(foreground)), luminance(rgb(background)))
  const dark = Math.min(luminance(rgb(foreground)), luminance(rgb(background)))
  return (light + 0.05) / (dark + 0.05)
}

for (const [browserName, launcher, options] of [
  ['chrome', chromium, { channel: 'chrome' }],
  ['firefox', firefox, {}],
]) {
  const browser = await launcher.launch({ headless: true, ...options })
  const context = await browser.newContext({ viewport: { width: 360, height: 800 } })
  const page = await context.newPage()
  const pageErrors = []
  page.on('pageerror', (error) => pageErrors.push(error.message))

  try {
    await page.route('http://127.0.0.1:8000/login', (route) => route.fulfill({
      status: 200,
      contentType: 'application/json',
      headers: {
        'Access-Control-Allow-Origin': 'http://127.0.0.1:5173',
        'Access-Control-Allow-Credentials': 'true',
      },
      body: JSON.stringify({ usuario_id: testUserId, rol: 'CONDUCTOR' }),
    }))
    await page.goto('http://127.0.0.1:5173/login')
    await page.getByLabel('Correo electrónico').fill('conductor@example.test')
    await page.getByLabel('Contraseña').fill('credencial-ficticia-de-prueba')
    await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
    await page.getByRole('link', { name: 'Mi itinerario', exact: true }).click()
    await page.getByRole('heading', { name: 'Mi itinerario', exact: true }).waitFor()

    const widthChecks = []
    for (const viewport of [320, 360, 768, 1280]) {
      await page.setViewportSize({ width: viewport, height: 900 })
      const sizes = await page.evaluate(() => ({
        viewport: document.documentElement.clientWidth,
        content: document.documentElement.scrollWidth,
      }))
      assert(sizes.content <= sizes.viewport, `Desbordamiento horizontal a ${viewport}px`)
      widthChecks.push({ width: viewport, horizontalOverflow: false })
    }

    await page.setViewportSize({ width: 360, height: 800 })
    await page.evaluate(() => {
      history.pushState({}, '', '/')
      window.dispatchEvent(new PopStateEvent('popstate'))
    })
    await page.getByRole('heading', { name: 'Rutas sostenibles para Lima' }).waitFor()
    await page.keyboard.press('Tab')
    const skipLink = page.getByRole('link', { name: 'Saltar al contenido principal' })
    await skipLink.waitFor()
    assert(await skipLink.evaluate((element) => element === document.activeElement), 'El enlace de salto no recibe el primer foco')
    const skipStyle = await skipLink.evaluate((element) => {
      const style = getComputedStyle(element)
      return { outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth }
    })
    assert.notEqual(skipStyle.outlineStyle, 'none', 'El enlace de salto no muestra foco visible')

    await page.getByRole('link', { name: 'Mi itinerario', exact: true }).click()
    const controls = page.locator('button, select, a[href], input')
    const unnamedControls = await controls.evaluateAll((elements) => elements.filter((element) => {
      const name = element.getAttribute('aria-label') ?? element.textContent ?? ''
      if (element instanceof HTMLInputElement) {
        return !document.querySelector(`label[for="${element.id}"]`) && !element.getAttribute('aria-label')
      }
      if (element instanceof HTMLSelectElement) {
        return !document.querySelector(`label[for="${element.id}"]`) && !element.getAttribute('aria-label')
      }
      return name.trim().length === 0
    }).length)
    assert.equal(unnamedControls, 0, 'Existen controles sin nombre accesible')

    const contrastTargets = [
      ['.driver-route-label', 'ruta'],
      ['.driver-demo-warning', 'aviso'],
      ['.driver-alert', 'alerta'],
      ['.driver-primary', 'botón principal'],
    ]
    const contrastChecks = []
    for (const [selector, label] of contrastTargets) {
      const colors = await page.locator(selector).first().evaluate((element) => {
        const style = getComputedStyle(element)
        let background = style.backgroundColor
        let ancestor = element.parentElement
        while ((background === 'rgba(0, 0, 0, 0)' || background === 'transparent') && ancestor) {
          background = getComputedStyle(ancestor).backgroundColor
          ancestor = ancestor.parentElement
        }
        return { foreground: style.color, background }
      })
      const ratio = contrast(colors.foreground, colors.background)
      assert(ratio >= 4.5, `Contraste insuficiente en ${label}: ${ratio.toFixed(2)}:1`)
      contrastChecks.push({ label, ratio: Number(ratio.toFixed(2)), required: 4.5 })
    }

    const itineraryButton = page.getByRole('button', { name: 'Ver detalle de parada' })
    await page.keyboard.press('Tab')
    assert(await itineraryButton.evaluate((element) => element === document.activeElement), 'El botón no recibe foco mediante Tab')
    const focusStyle = await itineraryButton.evaluate((element) => {
      const style = getComputedStyle(element)
      return { outlineStyle: style.outlineStyle, outlineWidth: Number.parseFloat(style.outlineWidth) }
    })
    assert.notEqual(focusStyle.outlineStyle, 'none', 'El botón no muestra foco visible')
    assert(focusStyle.outlineWidth >= 3, 'El indicador de foco es menor de 3px')

    await page.screenshot({ path: `${output}/${browserName}-itinerario-360.png`, fullPage: true })
    assert.equal(pageErrors.length, 0, 'Se detectaron errores de ejecución en la página')
    results.push({
      browser: browserName,
      version: browser.version(),
      result: 'passed',
      authentication: 'simulated-conductor-response',
      widthChecks,
      unnamedControls,
      skipLink: 'passed',
      focusVisible: 'passed',
      contrastChecks,
    })
    console.log(`${browserName} ${browser.version()}: ST-031 aprobado`)
  } finally {
    await context.close()
    await browser.close()
  }
}

await writeFile(`${output}/resultados.json`, `${JSON.stringify(results, null, 2)}\n`)
