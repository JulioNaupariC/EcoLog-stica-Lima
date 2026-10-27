import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

// ECL-76: real local API and database. No synthetic API or injected session.
// Use the production build/preview: the Compose Vite dev server has no offline shell.
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const api = process.env.OFFLINE_API_URL || 'http://127.0.0.1:8000'
const base = process.env.OFFLINE_PREVIEW_URL || 'http://127.0.0.1:5173'
for (const url of [api, base]) assert.equal(new URL(url).hostname, '127.0.0.1', 'Local demo only')
const stamp = new Date().toISOString().replaceAll(/[:.]/gu, '-')
const output = resolve(process.env.ECL76_OUTPUT || resolve(root,
  `docs/03 Implementación/Sprint 03/validaciones/evidencias/ECL-76/run-${stamp}`))
// mkdir without recursive also rejects a previously used evidence directory.
await mkdir(dirname(output), { recursive: true })
await mkdir(output)
const results = { ticket: 'ECL-76', executedAt: new Date().toISOString(), timezone: 'America/Lima',
  commit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
  workingTreeDirty: execFileSync('git', ['status', '--porcelain'], { cwd: root, encoding: 'utf8' }).trim().length > 0,
  api, base, mode: 'Real local API / PostgreSQL; only first response loss is injected', browsers: [] }
let phase = 'configuration'
let browser

async function signIn(page, role) {
  await page.goto(`${base}/login`)
  await page.getByLabel('Correo electrónico', { exact: true }).fill(`${role.toLowerCase()}.demo@ecologistica.example`)
  await page.getByLabel('Contraseña', { exact: true }).fill(process.env[`SEED_DEMO_PASSWORD_${role}`])
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
  await page.getByRole('heading', { name: 'Inicio', exact: true }).waitFor()
}

async function entries(page) {
  return page.evaluate(async () => {
    const db = await new Promise((resolve, reject) => {
      const request = indexedDB.open('ecologistica-incidents-v1', 1)
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(new Error('Cannot read outbox'))
    })
    try {
      return await new Promise((resolve, reject) => {
        const request = db.transaction('incidents').objectStore('incidents').getAll()
        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(new Error('Cannot read outbox'))
      })
    } finally { db.close() }
  })
}

async function assertUnique(operator, report) {
  // GET deliberately excludes operation_id. Correlate its ACK ID AND a unique
  // synthetic observation associated with that operation, across ALL pages.
  const matches = []
  for (let page = 1; ; page++) {
    const response = await operator.request.get(`${api}/incidencias?estado=PENDIENTE_VALIDACION&page=${page}&page_size=100`)
    assert.equal(response.status(), 200)
    const body = await response.json()
    matches.push(...body.items.filter(item => item.observacion === report.payload.observacion))
    if (page * body.page_size >= body.total) break
    assert(page < 1000, 'Unexpectedly large demo; use an isolated local dataset')
  }
  assert.equal(matches.length, 1, 'Exactly one persisted incidence for the operation marker')
  assert.equal(matches[0].incidencia_id, report.acknowledgement.incidencia_id)
  assert.equal(matches[0].estado, 'PENDIENTE_VALIDACION')
}

try {
  // Node loads dotenv without printing private values; existing env takes priority.
  try { process.loadEnvFile(resolve(root, '.env')) } catch (error) { if (error.code !== 'ENOENT') throw error }
  for (const role of ['CONDUCTOR', 'OPERADOR']) assert(process.env[`SEED_DEMO_PASSWORD_${role}`], `Missing demo password setting for ${role}`)
  const modulePath = process.env.PLAYWRIGHT_MODULE || resolve(root, '.tmp-ecl76/node_modules/playwright/index.mjs')
  const { chromium, firefox } = await import(pathToFileURL(resolve(modulePath)).href)
  for (const [name, engine, options] of [
    ['chrome', chromium, { channel: 'chrome' }], ['firefox', firefox, {}],
  ]) {
    phase = `${name}: launch`
    browser = await engine.launch({ headless: true, ...options })
    const record = { browser: name, engine: name === 'chrome' ? 'chromium' : 'firefox', version: browser.version(), rounds: [] }
    results.browsers.push(record)
    const driver = await browser.newContext({ viewport: { width: 360, height: 800 }, locale: 'es-PE', timezoneId: 'America/Lima' })
    const operator = await browser.newContext()
    try {
      const page = await driver.newPage()
      page.setDefaultTimeout(30_000)
      phase = `${name}: real demo login`
      await signIn(page, 'CONDUCTOR')
      await signIn(await operator.newPage(), 'OPERADOR')
      await page.goto(`${base}/conductor/itinerario`)
      await page.getByRole('heading', { name: 'Parada 1', exact: true }).waitFor()
      await page.evaluate(async () => {
        await Promise.race([
          (async () => {
            await navigator.serviceWorker.ready
            if (!navigator.serviceWorker.controller) await new Promise(resolve => navigator.serviceWorker.addEventListener('controllerchange', resolve, { once: true }))
          })(),
          new Promise((_, reject) => setTimeout(() => reject(new Error('Production service worker required')), 15_000)),
        ])
      })
      await page.getByRole('link', { name: 'Reportar incidencia', exact: true }).click()
      const stop = await page.getByLabel('Parada actual', { exact: true }).locator('option:not([value=""]):not([disabled])').first().getAttribute('value')
      assert(stop, 'Seed a driver itinerary with coordinates')

      async function submit(marker) {
        await page.getByLabel('Tipo', { exact: true }).selectOption('AVERIA')
        await page.getByRole('radio', { name: /Alta/u }).check()
        await page.getByLabel('Parada actual', { exact: true }).selectOption(stop)
        await page.getByLabel('Observación (opcional)', { exact: true }).fill(marker)
        await page.getByRole('button', { name: 'Enviar incidencia', exact: true }).click()
        await page.getByRole('heading', { name: 'Mis envíos', exact: true }).waitFor()
        await page.waitForFunction(async marker => {
          const db = await new Promise((resolve, reject) => {
            const request = indexedDB.open('ecologistica-incidents-v1', 1)
            request.onsuccess = () => resolve(request.result); request.onerror = reject
          })
          try {
            const all = await new Promise((resolve, reject) => {
              const request = db.transaction('incidents').objectStore('incidents').getAll()
              request.onsuccess = () => resolve(request.result); request.onerror = reject
            })
            return all.some(item => item.payload.observacion === marker)
          } finally { db.close() }
        }, marker)
        return (await entries(page)).find(item => item.payload.observacion === marker)
      }

      async function confirmed(operationId) {
        await page.waitForFunction(async operationId => {
          const db = await new Promise((resolve, reject) => {
            const request = indexedDB.open('ecologistica-incidents-v1', 1)
            request.onsuccess = () => resolve(request.result); request.onerror = reject
          })
          try {
            const all = await new Promise((resolve, reject) => {
              const request = db.transaction('incidents').objectStore('incidents').getAll()
              request.onsuccess = () => resolve(request.result); request.onerror = reject
            })
            return all.some(item => item.payload.operation_id === operationId && item.acknowledgement)
          } finally { db.close() }
        }, operationId)
        const report = (await entries(page)).find(item => item.payload.operation_id === operationId)
        assert.equal(report.acknowledgement.operation_id, operationId)
        await page.getByText(`ID: ${report.acknowledgement.incidencia_id}`, { exact: false }).waitFor()
        return report
      }

      phase = `${name}: ruta dorada online`
      const online = await submit(`ECL-76 online ${name} ${crypto.randomUUID()}`)
      await assertUnique(operator, await confirmed(online.payload.operation_id))
      record.online = { passed: true, operationId: online.payload.operation_id }

      for (let round = 1; round <= 10; round++) {
        phase = `${name}: I12/I13 ruta de borde ${round}/10`
        await driver.setOffline(true)
        const pending = await submit(`ECL-76 I12 ${name} ${round} ${crypto.randomUUID()}`)
        assert.equal(pending.acknowledgement, undefined)
        // The original immutable observation maps 1:1 to this operation.
        await page.reload()
        await page.getByText('Pendiente de envío · se sincronizará al reconectar.', { exact: true }).waitFor()
        const restored = (await entries(page)).find(item => item.payload.operation_id === pending.payload.operation_id)
        assert.deepEqual(restored, pending, 'Reload preserves owner, operation and content')
        await page.getByRole('link', { name: 'Volver al itinerario', exact: true }).click()
        await page.getByRole('heading', { name: 'Parada 1', exact: true }).waitFor()
        await page.getByRole('link', { name: 'Reportar incidencia', exact: true }).click()
        if (round === 1) await page.screenshot({ path: resolve(output, `${name}-offline.png`), fullPage: true })
        let lostAck = false
        const statuses = []
        const intercept = async route => {
          const response = await route.fetch()
          statuses.push(response.status())
          if (round === 1 && !lostAck) {
            assert.equal(response.status(), 201)
            lostAck = true
            await route.abort('connectionreset')
          } else await route.fulfill({ response })
        }
        await page.route(`${api}/conductor/incidencias`, intercept)
        await driver.setOffline(false)
        const report = await confirmed(pending.payload.operation_id)
        assert.deepEqual(report.payload, pending.payload)
        assert.equal(report.ownerId, pending.ownerId)
        assert.equal(report.acknowledgement.estado, 'PENDIENTE_VALIDACION')
        if (round === 1) assert.deepEqual(statuses, [201, 200], 'Lost ACK retries same operation')
        else assert.deepEqual(statuses, [201])
        const replay = await driver.request.post(`${api}/conductor/incidencias`, {
          data: pending.payload, headers: { 'X-Expected-Owner-ID': pending.ownerId },
        })
        assert.equal(replay.status(), 200)
        assert.deepEqual(await replay.json(), report.acknowledgement)
        await assertUnique(operator, report)
        await page.unroute(`${api}/conductor/incidencias`, intercept)
        record.rounds.push({ round, scenario: 'I12/I13 ruta de borde', passed: true,
          operationId: pending.payload.operation_id, incidenceId: report.acknowledgement.incidencia_id,
          offlineReload: true, itineraryPreserved: true, lostAck, statuses, replay: 200, persistedMatches: 1 })
        if (round === 1) await page.screenshot({ path: resolve(output, `${name}-reconnected.png`), fullPage: true })
      }
      record.passed = record.rounds.length === 10
    } finally {
      // End only the sessions created by this verification; retain synthetic evidence rows.
      await Promise.allSettled([driver.request.post(`${api}/logout`), operator.request.post(`${api}/logout`)])
      await driver.close(); await operator.close(); await browser.close(); browser = undefined
    }
  }
  results.passed = results.browsers.length === 2 && results.browsers.every(item => item.passed)
  console.log('ECL-76: Chrome y Firefox, 10/10 rondas por navegador; API real, replay y unicidad verificados.')
} catch (error) {
  results.passed = false
  // Playwright diagnostics may echo fill() values. Never serialize error.message/stack.
  results.failure = { phase, errorType: error.name }
  console.error(`ECL-76: bloqueado o fallido en «${phase}» (${error.name}); revisar entorno sin publicar credenciales.`)
  process.exitCode = 1
} finally {
  await browser?.close()
  await writeFile(resolve(output, 'results.json'), JSON.stringify(results, null, 2) + '\n', { flag: 'wx' })
}
