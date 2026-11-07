// ECL-112: compare two real production builds and verify the public offline
// shell. This does not exercise authenticated driver workflows or mock APIs.
// From frontend/: node scripts/verify-static-resources.mjs BEFORE_DIST AFTER_DIST NEW_REPORT.json
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { preview } from 'vite'

const root = fileURLToPath(new URL('../', import.meta.url))
const [before, after, destination] = process.argv.slice(2)
assert(before && after && destination, 'Specify before/after build directories and a new report')
const { default: puppeteer } = await import(pathToFileURL(resolve(root, '.tmp-ecl112/node_modules/puppeteer-core/lib/esm/puppeteer/puppeteer-core.js')))
const browser = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true })
const results = { ticket: 'ECL-112', startedAt: new Date().toISOString(), chrome: await browser.version(),
  scope: 'Production public login, rendered Spanish and offline shell; not authenticated driver E2E', builds: [] }
const screenshots = []
try {
  for (const [label, directory] of [['antes', before], ['despues', after]]) {
    const dist = resolve(directory)
    const manifest = JSON.parse(await readFile(resolve(dist, 'offline-shell.json'), 'utf8'))
    const server = await preview({ root, configFile: false, build: { outDir: dist },
      preview: { host: '127.0.0.1', port: 5174, strictPort: true } })
    const context = await browser.createBrowserContext()
    try {
      const page = await context.newPage()
      await page.setViewport({ width: 1350, height: 940, deviceScaleFactor: 1 })
      await page.goto('http://127.0.0.1:5174/login', { waitUntil: 'networkidle0' })
      await page.waitForSelector('#login-email')
      await page.evaluate(async () => { await document.fonts.ready; await navigator.serviceWorker.ready })
      await page.waitForFunction(() => navigator.serviceWorker.controller !== null)
      const screenshot = Buffer.from(await page.screenshot({ fullPage: true }))
      screenshots.push(screenshot)
      const cache = await page.evaluate(async () => {
        const name = (await caches.keys()).find(key => key.startsWith('ecologistica-shell-'))
        const store = await caches.open(name)
        const entries = await Promise.all((await store.keys()).map(async request => ({
          path: new URL(request.url).pathname, bytes: (await (await store.match(request)).arrayBuffer()).byteLength,
        })))
        return { entries, fontFiles: entries.filter(entry => entry.path.endsWith('.woff2')) }
      })
      assert.equal(cache.fontFiles.length, label === 'antes' ? 2 : 1)
      const client = await page.createCDPSession()
      await client.send('DOM.enable')
      await client.send('CSS.enable')
      await page.evaluate(async () => {
        const span = document.createElement('span')
        span.id = 'ecl112-spanish'
        span.textContent = 'áéíóúÁÉÍÓÚüÜñÑ¿¡'
        span.style.position = 'absolute'
        document.body.append(span)
        span.getBoundingClientRect()
        await document.fonts.load('16px "Inter Variable"', span.textContent)
        await document.fonts.ready
        span.getBoundingClientRect()
      })
      const documentNode = await client.send('DOM.getDocument')
      const { nodeId } = await client.send('DOM.querySelector', { nodeId: documentNode.root.nodeId, selector: '#ecl112-spanish' })
      const spanishFonts = await client.send('CSS.getPlatformFontsForNode', { nodeId })
      assert(spanishFonts.fonts.length > 0 && spanishFonts.fonts.every(font => font.isCustomFont && font.familyName.includes('Inter')), JSON.stringify(spanishFonts))
      await page.evaluate(() => document.getElementById('ecl112-spanish').remove())
      await page.setOfflineMode(true)
      await page.reload({ waitUntil: 'networkidle0' })
      await page.waitForSelector('#login-email')
      await page.evaluate(() => document.fonts.ready)
      const offlineFonts = await page.evaluate(() => document.fonts.check('16px "Inter Variable"', 'áéíóúñü¿¡'))
      assert(offlineFonts, 'Latin font unavailable offline')
      const files = await Promise.all(manifest.files.map(async file => ({ file, bytes: (await readFile(resolve(dist, file))).length })))
      results.builds.push({ label, manifestVersion: manifest.version, precacheFiles: files.length,
        precacheBodyBytes: files.reduce((sum, item) => sum + item.bytes, 0),
        fontFiles: cache.fontFiles, spanishFonts: spanishFonts.fonts, offlineShellLoaded: true,
        screenshotSha256: createHash('sha256').update(screenshot).digest('hex') })
      await client.detach()
    } finally {
      await context.close()
      await new Promise(accept => server.httpServer.close(accept))
    }
  }
  results.publicLoginScreenshotsIdentical = screenshots[0].equals(screenshots[1])
  assert(results.publicLoginScreenshotsIdentical, 'Public login screenshots differ; inspect before accepting')
  results.precacheBytesSaved = results.builds[0].precacheBodyBytes - results.builds[1].precacheBodyBytes
  results.precacheRequestsSaved = results.builds[0].precacheFiles - results.builds[1].precacheFiles
  await mkdir(dirname(resolve(destination)), { recursive: true })
  await writeFile(destination, JSON.stringify(results, null, 2) + '\n', { flag: 'wx' })
  console.log(JSON.stringify(results, null, 2))
} finally {
  await browser.close()
}
