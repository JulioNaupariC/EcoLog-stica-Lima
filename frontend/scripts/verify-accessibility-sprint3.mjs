import assert from 'node:assert/strict'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { createRequire } from 'node:module'
import { inspectTextSpacing } from './review-text-spacing.mjs'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const deps = resolve(process.env.ECL67_TOOLS || resolve(root, '.tmp-ecl67/node_modules'))
const output = resolve(process.env.EVIDENCE_DIR || resolve(root, '.tmp-ecl67/baseline'))
const axeOnly = process.argv.includes('--axe-only')
const spacingReview = process.argv.includes('--spacing-review')
const { chromium } = await import(pathToFileURL(resolve(deps, 'playwright/index.mjs')))
const requireTool = createRequire(resolve(deps, 'package.json'))
const { default: puppeteer } = await import(pathToFileURL(requireTool.resolve('puppeteer-core')))
const { snapshot, generateReport } = await import(pathToFileURL(resolve(deps, 'lighthouse/core/index.js')))
const origin = 'http://127.0.0.1:5173'
const api = 'http://127.0.0.1:8000'
const settings = Object.fromEntries((await readFile(resolve(root, '.env'), 'utf8')).split(/\r?\n/u)
  .filter(line => /^SEED_DEMO_PASSWORD_[A-Z]+=/u.test(line)).map(line => {
    const position = line.indexOf('=')
    return [line.slice(0, position), line.slice(position + 1)]
  }))

const screens = [
  { id: 'login', role: null, path: '/login', title: 'Iniciar sesión' },
  { id: 'inicio-operador', role: 'OPERADOR', path: '/', title: 'Inicio' },
  { id: 'conductores', role: 'OPERADOR', path: '/conductores', title: 'Conductores' },
  { id: 'pedido', role: 'OPERADOR', path: '/pedidos/nuevo', title: 'Registrar pedido' },
  { id: 'preferencias', role: 'OPERADOR', path: '/clientes/preferencias', title: 'Preferencias de entrega' },
  { id: 'incidencias-operacion', role: 'OPERADOR', path: '/operacion/incidencias', title: 'Incidencias pendientes' },
  { id: 'inicio-conductor', role: 'CONDUCTOR', path: '/', title: 'Inicio' },
  { id: 'itinerario', role: 'CONDUCTOR', path: '/conductor/itinerario', title: 'Mi itinerario' },
  { id: 'incidencias-conductor', role: 'CONDUCTOR', path: '/conductor/incidencias/nueva', title: 'Reportar incidencia' },
  { id: 'usuarios', role: 'ADMINISTRADOR', path: '/usuarios', title: 'Usuarios' },
  { id: 'cambio-contrasena', role: 'ADMINISTRADOR', path: '/cambiar-contrasena', title: 'Cambiar contraseña' },
]
const selectedScreens = process.env.ECL67_SCREENS?.split(',')

const results = []
const supplementary = []
let browser
let phase = 'startup'
let activeRole
let page
let context

async function save(name, value) {
  await writeFile(resolve(output, name), typeof value === 'string' ? value : JSON.stringify(value, null, 2) + '\n', { flag: 'wx' })
}

async function settle() {
  await page.waitForFunction(() => !document.querySelector('[aria-busy="true"], .skeleton'), undefined, { timeout: 15_000 })
  await page.evaluate(async () => { await document.fonts.ready })
}

async function signIn(role) {
  if (activeRole === role) return
  if (activeRole) {
    await page.getByRole('button', { name: /^Cuenta:/u }).click()
    await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click()
    await page.getByRole('heading', { name: 'Iniciar sesión', exact: true }).waitFor()
  }
  await page.goto(origin + '/login')
  if (role) {
    assert(settings[`SEED_DEMO_PASSWORD_${role}`], 'Missing private demo configuration')
    await page.getByLabel('Correo electrónico', { exact: true }).fill(`${role.toLowerCase()}.demo@ecologistica.example`)
    await page.getByLabel('Contraseña', { exact: true }).fill(settings[`SEED_DEMO_PASSWORD_${role}`])
    await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
    await page.getByRole('heading', { name: 'Inicio', exact: true }).waitFor()
  }
  activeRole = role
}

async function navigate(screen) {
  await signIn(screen.role)
  if (new URL(page.url()).pathname !== screen.path) {
    // A document reload would discard the staff identity held in React memory.
    await page.evaluate(path => {
      history.pushState(null, '', path)
      dispatchEvent(new PopStateEvent('popstate'))
    }, screen.path)
  }
  await page.getByRole('heading', { name: screen.title, exact: true }).waitFor()
  await settle()
  if (screen.id === 'preferencias') {
    await page.getByRole('combobox', { name: 'Cliente', exact: true }).fill('Bodega')
    await page.getByRole('option').first().click()
    await page.getByRole('button', { name: 'Consultar preferencias', exact: true }).click()
    await page.getByRole('heading', { name: 'Preferencias del cliente', exact: true }).waitFor()
    await settle()
  }
}

async function appearance(value) {
  await page.evaluate(theme => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('ecologistica-theme', theme)
  }, value)
  await page.evaluate(async () => {
    // Audit the settled theme, not intermediate colors during CSS transitions.
    await Promise.all(document.getAnimations().filter(animation => animation.effect?.getTiming().iterations !== Infinity)
      .map(animation => animation.finished.catch(() => {})))
  })
}

async function inspect(screen, theme, width, capture) {
  await page.setViewportSize({ width, height: 900 })
  await appearance(theme)
  await page.evaluate(() => scrollTo(0, 0))
  assert.equal(await page.locator('input[type="password"]').evaluateAll(inputs => inputs.some(input => input.value !== '')), false,
    'Never capture or audit a password value')
  await page.addScriptTag({ path: resolve(deps, 'axe-core/axe.min.js') })
  const audit = await page.evaluate(async () => {
    const result = await window.axe.run(document, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] },
    })
    return { testEngine: result.testEngine, testEnvironment: result.testEnvironment,
      violations: result.violations, incomplete: result.incomplete, passes: result.passes, inapplicable: result.inapplicable }
  })
  const dimensions = await page.evaluate(() => ({ viewport: innerWidth, scroll: document.documentElement.scrollWidth,
    title: document.title, lang: document.documentElement.lang, heading: document.querySelector('h1')?.textContent }))
  const key = `${screen.id}-${theme}-${width}`
  await save(`axe-${key}.json`, audit)
  if (capture || dimensions.scroll > dimensions.viewport || audit.violations.length > 0) {
    await page.screenshot({ path: resolve(output, `${key}.png`), fullPage: true, animations: 'disabled' })
  }
  const record = { screen: screen.id, route: screen.path, role: screen.role, theme, width, ...dimensions,
    axe: { violations: audit.violations.map(item => ({ id: item.id, impact: item.impact, tags: item.tags,
      targets: item.nodes.map(node => node.target) })), passes: audit.passes.length, incomplete: audit.incomplete.length,
    report: `axe-${key}.json` } }
  results.push(record)
  return record
}

try {
  await mkdir(output, { recursive: true })
  // Exclusive manifest creation prevents accidental replacement of an earlier evidence run.
  await save('run-start.json', { ticket: 'ECL-67', at: new Date().toISOString(), axeOnly, source: 'real API, synthetic local demo' })
  browser = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true })
  const puppeteerPage = (await browser.pages())[0]
  await puppeteerPage.goto(origin + '/login')
  const playwrightBrowser = await chromium.connectOverCDP(browser.wsEndpoint())
  context = playwrightBrowser.contexts()[0]
  page = context.pages().find(tab => tab.url().startsWith(origin))
  assert(page)

  for (const screen of screens.filter(item => !selectedScreens || selectedScreens.includes(item.id))) {
    phase = screen.id
    await page.setViewportSize({ width: 1280, height: 900 })
    await navigate(screen)
    for (const theme of ['light', 'dark']) {
      phase = `${screen.id}/${theme}`
      const desktop = await inspect(screen, theme, 1280, !axeOnly)
      if (!axeOnly) {
        // Snapshot mode evaluates the authenticated SPA without navigating back to login.
        const report = await snapshot(puppeteerPage, { flags: { onlyCategories: ['accessibility'],
          formFactor: 'desktop', screenEmulation: { disabled: true }, logLevel: 'error' } })
        assert.equal(report.lhr.gatherMode, 'snapshot')
        await save(`lighthouse-${screen.id}-${theme}.json`, report.lhr)
        await save(`lighthouse-${screen.id}-${theme}.html`, generateReport(report.lhr, 'html'))
        desktop.lighthouse = { mode: 'snapshot', score: report.lhr.categories.accessibility.score,
          report: `lighthouse-${screen.id}-${theme}.json` }
      }
      await inspect(screen, theme, 360, !axeOnly)
      await inspect(screen, theme, 320, false)
      // An automated text-resize probe, explicitly distinct from the user's real browser zoom test.
      await page.setViewportSize({ width: 1280, height: 900 })
      await page.evaluate(() => { document.documentElement.style.fontSize = '200%' })
      const resized = await page.evaluate(() => ({ viewport: innerWidth, scroll: document.documentElement.scrollWidth,
        overflowing: [...document.querySelectorAll('body *')].filter(element => element.getBoundingClientRect().right > innerWidth + 1)
          .slice(0, 12).map(element => ({ tag: element.tagName, class: String(element.className), right: element.getBoundingClientRect().right })) }))
      supplementary.push({ screen: screen.id, theme, check: '200-percent-root-font-size-not-browser-zoom', ...resized })
      if (resized.scroll > resized.viewport) {
        await page.screenshot({ path: resolve(output, `${screen.id}-${theme}-text-200.png`), fullPage: true, animations: 'disabled' })
      }
      await page.evaluate(() => { document.documentElement.style.fontSize = '' })
      if (spacingReview) {
        const style = await page.addStyleTag({ content: '* { line-height: 1.5 !important; letter-spacing: .12em !important; word-spacing: .16em !important; } p { margin-bottom: 2em !important; }' })
        for (const width of [1280, 360, 320]) {
          await page.setViewportSize({ width, height: 900 })
          await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))
          await appearance(theme)
          await page.evaluate(() => scrollTo(0, 0))
          const review = await page.evaluate(inspectTextSpacing)
          review.controls = await page.locator('main a[href], main button:not([disabled]), main input:not([disabled]), main select, main textarea').evaluateAll(async elements => {
            const controls = []
            for (const element of elements) {
              if (!element.getClientRects().length || element.closest('[hidden], [inert]')) continue
              element.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' })
              const rect = element.getBoundingClientRect()
              const hit = document.elementFromPoint(rect.x + rect.width / 2, rect.y + rect.height / 2)
              controls.push({ tag: element.tagName, id: element.id,
                name: element.getAttribute('aria-label') || element.textContent?.trim().slice(0, 80),
                reachableAtCenter: Boolean(hit && (element === hit || element.contains(hit))) })
            }
            scrollTo(0, 0)
            return controls
          })
          await save(`spacing-${screen.id}-${theme}-${width}.json`, review)
          await page.screenshot({ path: resolve(output, `spacing-${screen.id}-${theme}-${width}.jpg`), fullPage: true, quality: 80, animations: 'disabled' })
        }
        await style.evaluate(element => element.remove())
        await page.setViewportSize({ width: 1280, height: 900 })
      }
      const spacingStyle = await page.addStyleTag({ content: '* { line-height: 1.5 !important; letter-spacing: .12em !important; word-spacing: .16em !important; } p { margin-bottom: 2em !important; }' })
      const spacing = await page.evaluate(() => ({ viewport: innerWidth, scroll: document.documentElement.scrollWidth }))
      supplementary.push({ screen: screen.id, theme, check: 'text-spacing-overflow-probe-not-complete-visual-review', ...spacing })
      await spacingStyle.evaluate(element => element.remove())
      await page.setViewportSize({ width: 900, height: 360 })
      const landscape = await page.evaluate(() => ({ viewport: innerWidth, scroll: document.documentElement.scrollWidth,
        heading: document.querySelector('main h1')?.textContent, orientationLock: screen.orientation?.type }))
      supplementary.push({ screen: screen.id, theme, check: 'landscape-layout-probe', ...landscape })
      console.log(`ECL-67 ${screen.id}/${theme}: axe ${desktop.axe.violations.length}, Lighthouse ${desktop.lighthouse?.score ?? 'not-run'}`)
    }
  }

  phase = 'home index navigation by role'
  const indexes = []
  const headings = { ...Object.fromEntries(screens.map(screen => [screen.path, screen.title])), '/vehiculos': 'Vehículos' }
  for (const role of ['ADMINISTRADOR', 'OPERADOR', 'CONDUCTOR', 'ANALISTA', 'AUDITOR']) {
    await navigate({ role, path: '/', title: 'Inicio' })
    await page.setViewportSize({ width: 1280, height: 900 })
    const paths = await page.locator('main a[href]').evaluateAll(links => [...new Set(links.map(link => link.getAttribute('href')))])
    const visited = []
    for (const path of paths) {
      await page.locator(`main a[href="${path}"]`).first().click()
      await page.waitForURL(url => url.pathname === path)
      await page.getByRole('heading', { name: headings[path], exact: true }).waitFor()
      await settle()
      const heading = await page.locator('main h1').innerText()
      assert.notEqual(heading, 'Acceso denegado')
      visited.push({ path, heading })
      await page.locator('header a.brand').click()
      await page.getByRole('heading', { name: 'Inicio', exact: true }).waitFor()
    }
    indexes.push({ role, visited })
  }
  await save('navigation-home-index.json', indexes)

  phase = 'mobile drawer keyboard'
  await signIn('OPERADOR')
  await page.setViewportSize({ width: 360, height: 900 })
  await page.getByRole('button', { name: 'Abrir menú', exact: true }).click()
  const focus = []
  for (let index = 0; index < 18; index++) {
    focus.push(await page.evaluate(() => ({ tag: document.activeElement.tagName,
      inDrawer: Boolean(document.activeElement.closest('#menu-lateral')),
      name: document.activeElement.getAttribute('aria-label') || document.activeElement.textContent?.trim().slice(0, 80) })))
    await page.keyboard.press('Tab')
  }
  await save('keyboard-mobile-drawer.json', focus)
  await page.keyboard.press('Escape')
  supplementary.push({ check: 'mobile-drawer-escape', focusReturned: await page.getByRole('button', { name: 'Abrir menú', exact: true }).evaluate(button => button === document.activeElement) })
  await context.request.post(api + '/logout')
} catch (error) {
  console.error(`ECL-67: falló «${phase}» (${error.name}); detalles privados omitidos.`)
  process.exitCode = 1
} finally {
  await save('summary.json', { ticket: 'ECL-67', executedAt: new Date().toISOString(), timezone: 'America/Lima',
    browser: browser ? await browser.version() : null, completed: !process.exitCode, phase, axeOnly, results, supplementary,
    manualScreenReader: 'pending user evaluation', realBrowserZoom200: 'pending user evaluation',
    note: 'Automated scores are not a WCAG conformance percentage.' })
  await browser?.close()
}
