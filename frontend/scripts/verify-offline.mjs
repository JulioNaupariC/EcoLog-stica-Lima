import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

// Only disposable synthetic accounts. API responses are real; one ACK is dropped.
const { chromium, firefox } = await import(pathToFileURL(resolve(process.env.PLAYWRIGHT_MODULE)))
const api = process.env.OFFLINE_API_URL
const base = process.env.OFFLINE_PREVIEW_URL
const output = resolve('evidencias/ECL-58')
await mkdir(output, { recursive: true })
const results = []
for (const [name, engine, options] of [['chrome', chromium, { channel: 'chrome' }], ['firefox', firefox, {}]]) {
  const browser = await engine.launch({ headless: true, ...options })
  try {
    const context = await browser.newContext({ viewport: { width: 360, height: 800 } })
    const page = await context.newPage()
    await page.goto(`${base}/login`)
    await page.getByLabel('Correo electrónico').fill(`st032-${name}@example.test`)
    await page.getByLabel('Contraseña').fill(process.env.OFFLINE_TEST_PASSWORD)
    await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
    await page.getByRole('link', { name: 'Mi itinerario' }).click()
    await page.getByRole('heading', { name: 'Parada 1', exact: true }).waitFor()
    await page.evaluate(async () => {
      await navigator.serviceWorker.ready
      if (!navigator.serviceWorker.controller) await new Promise(resolve => navigator.serviceWorker.addEventListener('controllerchange', resolve, { once: true }))
    })
    const cases = []
    for (let n = 1; n <= 10; n++) {
      const card = () => page.locator('.driver-panel').filter({ has: page.getByRole('heading', { name: `Parada ${n}`, exact: true }) })
      await context.setOffline(true)
      await card().getByRole('button', { name: 'Registrar entrega pendiente' }).click()
      await card().getByText('Reportes pendientes: 1', { exact: true }).waitFor()
      if (n === 1) await page.screenshot({ path: resolve(output, `${name}-01-pendiente-offline.png`), fullPage: true })
      await page.reload()
      await card().getByText('Reportes pendientes: 1', { exact: true }).waitFor()
      assert.equal(await card().getByText(/Av. Sintetica/u).count(), 1)
      const pending = await page.evaluate(async () => {
        const db = await new Promise((resolve, reject) => { const r = indexedDB.open('ecologistica-offline-v1', 2); r.onsuccess = () => resolve(r.result); r.onerror = reject })
        try { return await new Promise((resolve, reject) => { const r = db.transaction('pendingReports').objectStore('pendingReports').getAll(); r.onsuccess = () => resolve(r.result); r.onerror = reject }) }
        finally { db.close() }
      })
      assert.equal(pending.length, 1)
      let lostAck = false, calls = 0
      const intercept = async route => {
        calls++
        if (n === 1 && !lostAck) {
          const response = await route.fetch()
          assert.equal(response.status(), 200)
          lostAck = true
          await route.abort('connectionreset')
        } else await route.continue()
      }
      await page.route(`${api}/conductor/reportes`, intercept)
      if (n === 2) {
        const down = route => route.abort('connectionrefused')
        await page.route(`${api}/conductor/itinerario`, down)
        await context.setOffline(false)
        await page.getByText('Sincronización pendiente. Se reintentará cuando el servicio esté disponible.', { exact: true }).waitFor()
        assert.equal(await card().getByText('Reportes pendientes: 1', { exact: true }).count(), 1)
        await page.screenshot({ path: resolve(output, `${name}-03-api-no-disponible.png`), fullPage: true })
        await page.unroute(`${api}/conductor/itinerario`, down)
        // No new online event: backoff must recover automatically.
      } else await context.setOffline(false)
      await card().getByText('Reportes pendientes: 0', { exact: true }).waitFor({ timeout: 20_000 })
      await card().getByText('Entregado', { exact: true }).waitFor()
      assert(await card().getByRole('button', { name: 'Registrar entrega pendiente' }).isDisabled())
      const replay = await page.evaluate(async ({ api, report }) => {
        const response = await fetch(`${api}/conductor/reportes`, {
          method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ operation_id: report.operationId, stop_id: report.stopId, status: report.status }),
        })
        return { status: response.status, body: await response.json() }
      }, { api, report: pending[0] })
      assert.equal(replay.status, 200)
      assert.equal(replay.body.operation_id, pending[0].operationId)
      await page.unroute(`${api}/conductor/reportes`, intercept)
      cases.push({ round: n, operationId: pending[0].operationId, stopId: pending[0].stopId, offlineReload: 'passed', automaticSync: 'passed', lostAck, sendCalls: calls, replay: replay.status })
      if (n === 1) await page.screenshot({ path: resolve(output, `${name}-02-confirmado-reconexion.png`), fullPage: true })
    }
    const cachedUrls = await page.evaluate(async () => {
      const result = []
      for (const name of await caches.keys()) for (const request of await (await caches.open(name)).keys()) result.push(request.url)
      return result
    })
    assert(cachedUrls.every(url => !url.startsWith(api)))
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), 360)
    // Same-browser logout clears local identity; the other account has no cached route.
    await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click()
    await page.getByRole('heading', { name: 'Iniciar sesión', exact: true }).waitFor()
    assert.equal(await page.evaluate(() => sessionStorage.getItem('ecologistica-driver-tab')), null)
    await page.getByLabel('Correo electrónico').fill('st032-other@example.test')
    await page.getByLabel('Contraseña').fill(process.env.OFFLINE_TEST_PASSWORD)
    await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
    await page.getByRole('link', { name: 'Mi itinerario' }).click()
    await page.getByRole('heading', { name: 'Aún no tienes un itinerario asignado', exact: true }).waitFor()
    assert.equal(await page.getByText(/Av. Sintetica/u).count(), 0)
    await page.screenshot({ path: resolve(output, `${name}-04-otra-cuenta.png`), fullPage: true })
    results.push({ browser: name, version: browser.version(), api: 'real FastAPI', database: 'real PostgreSQL/PostGIS', cases, shellCache: cachedUrls, logoutIsolation: 'passed', viewport: 360 })
    await context.close()
  } finally { await browser.close() }
}
await writeFile(resolve(output, 'resultados.json'), JSON.stringify(results, null, 2) + '\n')
console.log('ST032: 10 offline/reload/reconnection rounds per browser passed against real API.')
