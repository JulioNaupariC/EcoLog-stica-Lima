import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { createRequire } from 'node:module'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

// Full SPA with intercepted synthetic HTTP; never authenticates a real account.
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const requireFrontend = createRequire(resolve(root, 'frontend/package.json'))
const { default: puppeteer } = await import(pathToFileURL(requireFrontend.resolve('puppeteer-core')))
const { snapshot } = await import(pathToFileURL(resolve(root, 'frontend/node_modules/lighthouse/core/index.js')))
const origin = process.env.ECL15_ORIGIN || 'http://127.0.0.1:5184'
const output = resolve(process.env.ECL15_OUTPUT || resolve(root, '.tmp-ecl15-browser'))
const fixtures = resolve(root, 'frontend/src/test/fixtures/rutas')
const full = JSON.parse(await readFile(resolve(fixtures, 'sostenibilidad-con-datos.json'), 'utf8'))
const empty = JSON.parse(await readFile(resolve(fixtures, 'sostenibilidad-sin-datos.json'), 'utf8'))
await mkdir(output, { recursive: true })
const records = []
const save = (file, data) => writeFile(resolve(output, file), JSON.stringify(data, null, 2) + '\n')
const sourceHashes = {}
for (const file of ['frontend/src/pages/SustainabilityPage.tsx', 'frontend/src/domain/sustainability.ts', 'frontend/src/services/sustainability.ts', 'frontend/src/styles/sustainability.css']) {
  sourceHashes[file] = createHash('sha256').update(await readFile(resolve(root, file))).digest('hex')
}

async function checkBrowser(name, options) {
  const browser = await puppeteer.launch({ headless: true, ...options })
  const version = await browser.version()
  try {
    const page = await browser.newPage()
    await page.setViewport({ width: 1280, height: 900 })
    await page.setRequestInterception(true)
    let mode = 'data', calls = 0
    const sizes = []
    page.on('request', request => {
      const url = new URL(request.url())
      if (url.origin !== 'http://127.0.0.1:8000') { void request.continue(); return }
      const headers = { 'Access-Control-Allow-Origin': origin, 'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Headers': 'content-type', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS', 'Cache-Control': 'no-store' }
      if (request.method() === 'OPTIONS') { void request.respond({ status: 204, headers }); return }
      let body, status = 200
      if (url.pathname === '/login') body = { usuario_id: '123e4567-e89b-42d3-a456-426614174000', rol: 'OPERADOR' }
      else if (url.pathname === '/indicadores/sostenibilidad') {
        calls++
        body = { ...(mode === 'empty' ? empty : full), periodo: { desde: url.searchParams.get('desde'), hasta: url.searchParams.get('hasta') } }
        if (mode === 'error') { status = 503; body = { detail: 'UNTRUSTED_DETAIL' } }
        sizes.push(Buffer.byteLength(JSON.stringify(body), 'utf8'))
      } else { status = 503; body = { detail: 'Servicio no incluido en esta prueba' } }
      void request.respond({ status, headers, contentType: 'application/json', body: JSON.stringify(body) })
    })
    await page.goto(origin + '/login')
    await page.waitForSelector('#login-email')
    await page.type('#login-email', 'synthetic@example.test')
    await page.type('#login-password', 'synthetic-password')
    await page.locator('button[type="submit"]').click()
    await page.waitForFunction(() => document.querySelector('main h1')?.textContent === 'Inicio')
    await page.locator('a[href="/indicadores/sostenibilidad"]').click()
    await page.waitForSelector('.sustainability-page table')
    for (const theme of ['light', 'dark']) {
      for (const width of [1280, 360]) {
        await page.setViewport({ width, height: 900 })
        await page.evaluate(theme => { document.documentElement.dataset.theme = theme }, theme)
        await page.evaluate(async () => { await document.fonts.ready })
        await page.addScriptTag({ path: requireFrontend.resolve('axe-core/axe.min.js') })
        const axe = await page.evaluate(async () => {
          const result = await window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] } })
          return { violations: result.violations, incomplete: result.incomplete.map(x => ({ id: x.id, targets: x.nodes.map(n => n.target) })), passes: result.passes.length }
        })
        const dimensions = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth }))
        const key = `${name}-${theme}-${width}`
        await save(`axe-${key}.json`, axe)
        await page.screenshot({ path: resolve(output, `${key}.png`), fullPage: true })
        records.push({ browser: name, version, theme, ...dimensions, axeViolations: axe.violations.length })
        assert.equal(axe.violations.length, 0, `${key}: ${axe.violations.map(x => x.id)}`)
        assert.equal(dimensions.scrollWidth, width, `${key}: horizontal overflow`)
      }
    }
    if (name === 'chrome') {
      await page.setViewport({ width: 1280, height: 900 })
      const result = await snapshot(page, { flags: { onlyCategories: ['accessibility'], formFactor: 'desktop', screenEmulation: { disabled: true }, logLevel: 'error' } })
      await save('lighthouse-accessibility.json', result.lhr)
      const failures = Object.values(result.lhr.audits).filter(a => a.score === 0 && a.scoreDisplayMode !== 'notApplicable').map(a => a.id)
      records.push({ browser: name, lighthouseMode: result.lhr.gatherMode, accessibility: result.lhr.categories.accessibility.score, failures })
      assert.equal(result.lhr.categories.accessibility.score, 1, failures.join(', '))
    }
    // Invalid range must focus the first field, announce the error and avoid HTTP.
    const changeDates = (desde, hasta) => page.evaluate(({ desde, hasta }) => {
      const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
      for (const [id, value] of [['sustainability-from', desde], ['sustainability-to', hasta]]) {
        const input = document.getElementById(id); set.call(input, value); input.dispatchEvent(new Event('input', { bubbles: true }))
      }
    }, { desde, hasta })
    const before = calls
    await changeDates('2026-11-21', '2026-11-20')
    await page.focus('.sustainability-filters button'); await page.keyboard.press('Enter')
    await page.waitForSelector('#sustainability-validation')
    assert.equal(calls, before)
    assert.equal(await page.evaluate(() => document.activeElement.id), 'sustainability-from')
    mode = 'empty'
    await changeDates('2025-01-01', '2025-01-31')
    await page.focus('.sustainability-filters button'); await page.keyboard.press('Enter')
    await page.waitForFunction(() => document.querySelector('main')?.textContent.includes('Sin datos para este periodo'))
    assert.equal(await page.$('main table'), null)
    mode = 'error'
    await page.focus('.sustainability-filters button'); await page.keyboard.press('Enter')
    await page.waitForFunction(() => document.querySelector('[role="alert"]')?.textContent.includes('No se pudo consultar el periodo'))
    assert(!await page.evaluate(() => document.querySelector('main').textContent.includes('UNTRUSTED_DETAIL')))
    assert.equal(await page.$('main table'), null)
    records.push({ browser: name, keyboardSubmit: true, invalidPeriodNoRequest: true, invalidPeriodFocus: true,
      emptyAndErrorDistinct: true, syntheticAggregateMaxBytes: Math.max(...sizes) })
    assert(Math.max(...sizes) <= 250000)
    console.log(JSON.stringify({ browser: name, version, status: 'passed' }))
  } finally { await browser.close() }
}
try {
  await checkBrowser('chrome', { executablePath: process.env.ECL15_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe' })
  await checkBrowser('firefox', { browser: 'firefox', executablePath: process.env.ECL15_FIREFOX || 'C:/Program Files/Mozilla Firefox/firefox.exe' })
  await save('results.json', { status: 'passed', date: new Date().toISOString(), origin, source: 'SPA real; login y GET interceptados con fixtures sintéticos ST-045, sin credenciales ni backend real', sourceHashes, records })
} catch (error) {
  await save('failure.json', { message: error instanceof Error ? error.message : String(error), records })
  throw error
}
