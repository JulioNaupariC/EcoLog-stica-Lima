import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

// Browser dependencies are isolated from the application's package.json.
const { chromium, firefox } = await import(pathToFileURL(resolve(process.env.PLAYWRIGHT_MODULE)))
const axePath = resolve(process.env.AXE_SCRIPT)
const base = process.env.PREVIEW_URL || 'http://127.0.0.1:5178'
const output = resolve(process.env.EVIDENCE_DIR || 'evidencias/ECL-57')
await mkdir(output, { recursive: true })
const results = []
for (const [name, engine, options] of [['chrome', chromium, { channel: 'chrome' }], ['firefox', firefox, {}]]) {
  const browser = await engine.launch({ headless: true, ...options })
  try {
    const context = await browser.newContext({ viewport: { width: 360, height: 800 } })
    const page = await context.newPage()
    const checks = []
    await context.route('**/review-api/**', route => {
      const path = new URL(route.request().url()).pathname
      const body = path.endsWith('/login')
        ? { usuario_id: '123e4567-e89b-42d3-a456-426614174005', rol: 'CONDUCTOR' }
        : { owner_id: '123e4567-e89b-42d3-a456-426614174005', stops: [1, 2].map(position => ({ stop_id: `223e4567-e89b-42d3-a456-42661417400${position}`, position, status: 'PENDIENTE' })) }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
    })
    async function inspect(label) {
      await page.addScriptTag({ path: axePath })
      const audit = await page.evaluate(async () => {
        const result = await window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] } })
        return { violations: result.violations, incomplete: result.incomplete.map(item => ({ id: item.id, targets: item.nodes.map(node => node.target) })), passes: result.passes.length }
      })
      const dimensions = await page.evaluate(() => ({ viewport: innerWidth, scroll: document.documentElement.scrollWidth }))
      assert.equal(dimensions.scroll, dimensions.viewport, `${name}/${label}: horizontal overflow`)
      assert.equal(audit.violations.length, 0, JSON.stringify(audit.violations))
      await page.screenshot({ path: resolve(output, `${name}-${label}.png`), fullPage: true })
      checks.push({ label, dimensions, ...audit })
    }
    await page.goto(`${base}/login`)
    await page.keyboard.press('Tab')
    assert.equal(await page.locator(':focus').textContent(), 'Saltar al contenido principal')
    await page.keyboard.press('Enter')
    assert.equal(await page.locator(':focus').getAttribute('id'), 'contenido-principal')
    await inspect('01-login-360')
    await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
    await inspect('02-validacion-360')
    await page.getByLabel('Correo electrónico').fill('synthetic@example.test')
    await page.getByLabel('Contraseña').fill('synthetic-test-password')
    await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
    await page.getByRole('link', { name: 'Mi itinerario' }).click()
    await page.getByText('Reportes pendientes: 0', { exact: true }).first().waitFor()
    await inspect('03-itinerario-360')
    const keyboard = []
    await page.getByRole('link', { name: 'EcoLogística Lima', exact: true }).focus()
    const controls = await page.locator('a,button:not([disabled]),select,input').count()
    for (let i = 0; i < controls + 2; i++) {
      await page.keyboard.press('Tab')
      keyboard.push(await page.evaluate(() => {
        const e = document.activeElement, s = getComputedStyle(e)
        return { tag: e.tagName, text: e.textContent, focusVisible: e.matches(':focus-visible'), outlineColor: s.outlineColor, outlineStyle: s.outlineStyle, outlineWidth: s.outlineWidth }
      }))
    }
    assert(keyboard.some(e => e.text === 'Sincronizar pendientes' && e.focusVisible))
    assert(keyboard.some(e => e.text === 'Mi itinerario' && e.outlineColor === 'rgb(29, 78, 216)'))
    await page.getByRole('link', { name: 'Mi itinerario' }).focus()
    await page.screenshot({ path: resolve(output, `${name}-04-foco-360.png`), fullPage: true })
    for (const width of [768, 1280]) {
      await page.setViewportSize({ width, height: 900 })
      await inspect(`05-itinerario-${width}`)
    }
    await page.setViewportSize({ width: 360, height: 800 })
    await page.addStyleTag({ content: '* {line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important} p{margin-bottom:2em!important}' })
    await inspect('06-espaciado-360')
    results.push({ browser: name, version: browser.version(), api: 'simulated; only UI accessibility evaluated', checks, keyboard, skipLink: 'passed', focusContrastWhite: 6.701618401398375 })
    await context.close()
  } finally { await browser.close() }
}
await writeFile(resolve(output, 'resultados.json'), JSON.stringify(results, null, 2) + '\n')
console.log('Chrome and Firefox: responsive, keyboard, focus and axe checks passed.')
