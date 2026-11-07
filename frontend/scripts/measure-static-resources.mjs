// ECL-112 local paired campaign. Public /login only; no credentials, cookies,
// business payloads or HAR are exported. This is not the final ECL-115 campaign.
// From frontend/: install the pinned tools described in the ECL-112 report,
// then node scripts/measure-static-resources.mjs NEW_OUTPUT_DIRECTORY
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { cpus, release, totalmem } from 'node:os'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const root = fileURLToPath(new URL('../', import.meta.url))
const output = process.argv[2]
assert(output, 'Specify a new output directory; existing runs are never overwritten')
await mkdir(dirname(resolve(output)), { recursive: true })
await mkdir(output)
const tools = resolve(root, '.tmp-ecl112/node_modules')
const { default: puppeteer } = await import(pathToFileURL(resolve(tools, 'puppeteer-core/lib/esm/puppeteer/puppeteer-core.js')))
const { default: lighthouse, desktopConfig } = await import(pathToFileURL(resolve(tools, 'lighthouse/core/index.js')))
const origin = 'http://127.0.0.1:5173'
const pause = ms => new Promise(accept => setTimeout(accept, ms))
const save = (name, value) => writeFile(resolve(output, name), JSON.stringify(value, null, 2) + '\n', { flag: 'wx' })
const css = await readFile(resolve(root, 'src/styles/base.css'))
const metadata = {
  ticket: 'ECL-112', scope: 'Local paired measurement of public login; not ECL-115',
  baselineEcl108: 'e09dcd80e32431018d4020bb02c89ffae7505705',
  head: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
  modifiedTrackedFiles: execFileSync('git', ['diff', 'HEAD', '--name-only'], { cwd: root, encoding: 'utf8' }).trim().split(/\r?\n/u).filter(Boolean),
  baseCssSha256: createHash('sha256').update(css).digest('hex'),
  startedAt: new Date().toISOString(), timezone: 'America/Lima',
  node: process.version, cpu: cpus()[0]?.model, ramBytes: totalmem(), windowsRelease: release(),
  lighthouse: '12.8.2', viewport: { width: 1350, height: 940, deviceScaleFactor: 1 },
  configuration: { mode: 'navigation', preset: 'desktop', performanceOnly: true, disableStorageReset: true,
    network: 'DevTools NetworkLog; no throttling; disabled HTTP cache; networkidle0 + 1 second',
    lighthouseThrottling: desktopConfig.settings.throttling, frontend: 'Docker Compose / Vite development',
    warmup: 'One initial public login navigation before the three measured reloads; no API campaign',
    limitations: 'Different PC and Chrome from ECL-108; protected views and final ECL-115 not measured' },
  rounds: [],
}
let browser
try {
  browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: false,
    args: ['--disable-extensions', '--auto-open-devtools-for-tabs', '--window-size=1500,1100'],
  })
  metadata.chrome = await browser.version()
  const context = await browser.createBrowserContext()
  const page = await context.newPage()
  await page.setViewport(metadata.viewport)
  await page.goto(`${origin}/login`, { waitUntil: 'networkidle0' })
  await page.waitForSelector('#login-email')
  await pause(1000)
  const target = browser.targets().filter(item => item.url().startsWith('devtools:')).at(-1)
  assert(target, 'Dedicated DevTools target unavailable')
  const devtools = await target.asPage()
  await devtools.evaluate(async () => {
    const UI = await import('./ui/legacy/legacy.js')
    const Common = await import('./core/common/common.js')
    await UI.InspectorView.InspectorView.instance().showPanel('network')
    Common.Settings.Settings.instance().moduleSetting('cache-disabled').set(true)
    UI.DockController.DockController.instance().setDockSide('undocked')
  })
  for (let round = 1; round <= 3; round += 1) {
    const prefix = `login-${String(round).padStart(2, '0')}`
    const client = await page.createCDPSession()
    await client.send('Network.enable')
    await client.send('Network.clearBrowserCache')
    await client.send('Network.setCacheDisabled', { cacheDisabled: true })
    await devtools.evaluate(async () => {
      const Logs = await import('./models/logs/logs.js')
      Logs.NetworkLog.NetworkLog.instance().reset(true)
    })
    const start = performance.now()
    await page.reload({ waitUntil: 'networkidle0', timeout: 60000 })
    await pause(1000)
    assert.equal(new URL(page.url()).pathname, '/login', 'Unexpected final URL')
    const network = await devtools.evaluate(async () => {
      const Logs = await import('./models/logs/logs.js')
      const Common = await import('./core/common/common.js')
      const requests = Logs.NetworkLog.NetworkLog.instance().requests()
      return { requests: requests.length, transferredBytes: requests.reduce((sum, item) => sum + item.transferSize, 0),
        failures: requests.filter(item => item.failed).length,
        cacheDisabled: Common.Settings.Settings.instance().moduleSetting('cache-disabled').get(),
        resources: requests.map(item => ({ path: new URL(item.url()).pathname, type: item.resourceType().name(),
          transferredBytes: item.transferSize, decodedBytes: item.resourceSize, status: item.statusCode })) }
    })
    network.observedMs = performance.now() - start
    network.finalUrl = page.url()
    await save(`${prefix}.network.json`, network)
    await devtools.screenshot({ path: resolve(output, `${prefix}-network.png`) })
    await page.screenshot({ path: resolve(output, `${prefix}-pagina.png`), fullPage: true })
    const result = await lighthouse(`${origin}/login`, { onlyCategories: ['performance'], disableStorageReset: true, logLevel: 'error' }, desktopConfig, page)
    assert(result && !result.lhr.runtimeError, 'Lighthouse runtime error')
    assert.equal(new URL(result.lhr.finalDisplayedUrl || result.lhr.finalUrl).pathname, '/login')
    await save(`${prefix}.lighthouse.json`, result.lhr)
    const audits = result.lhr.audits
    const values = { round, performance: result.lhr.categories.performance.score * 100,
      fcpMs: audits['first-contentful-paint'].numericValue, lcpMs: audits['largest-contentful-paint'].numericValue,
      tbtMs: audits['total-blocking-time'].numericValue, cls: audits['cumulative-layout-shift'].numericValue,
      transferredBytes: network.transferredBytes, requests: network.requests }
    metadata.rounds.push(values)
    console.log(JSON.stringify(values))
    await client.detach()
  }
  const accessibility = await lighthouse(`${origin}/login`, { onlyCategories: ['accessibility'], disableStorageReset: true, logLevel: 'error' }, desktopConfig, page)
  assert(accessibility && !accessibility.lhr.runtimeError, 'Accessibility audit runtime error')
  await save('login-accessibility.lighthouse.json', accessibility.lhr)
  metadata.accessibility = accessibility.lhr.categories.accessibility.score * 100
  metadata.inlineSvg = await page.evaluate(() => ({ count: document.querySelectorAll('svg').length,
    decorativeHidden: [...document.querySelectorAll('svg')].every(svg => svg.getAttribute('aria-hidden') === 'true'),
    images: document.querySelectorAll('img, picture').length, fontFamily: getComputedStyle(document.body).fontFamily }))
  metadata.medians = Object.fromEntries(Object.keys(metadata.rounds[0]).filter(key => key !== 'round').map(key =>
    [key, metadata.rounds.map(round => round[key]).sort((a, b) => a - b)[1]]))
  console.log(JSON.stringify({ medians: metadata.medians, accessibility: metadata.accessibility, inlineSvg: metadata.inlineSvg }))
} finally {
  metadata.finishedAt = new Date().toISOString()
  await save('resultados.json', metadata)
  await browser?.close()
}
