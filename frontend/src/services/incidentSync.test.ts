import { IDBFactory } from 'fake-indexeddb'
import { correctRejectedIncident, enqueueIncident, listIncidents, loadIncidentDraft, saveIncidentDraft, updateIncident, removeIncidentDraft } from './incidentStorage'
import { synchronizeIncidents } from './incidentSync'
import { sendIncident } from './incidents'
import { getDriverItinerary, DriverItineraryServiceError } from './driverItinerary'
import { loadItinerary, saveItinerary } from './offlineStorage'
import { enqueueReport, listPendingReports } from './reportQueue'
import { newIncidentDraft } from '../domain/incident'
import type { StoredIncident } from '../domain/incident'

vi.mock('./driverItinerary', async original => ({ ...await original<typeof import('./driverItinerary')>(), getDriverItinerary: vi.fn() }))
const ownerId = '123e4567-e89b-42d3-a456-426614174005'
const otherId = '123e4567-e89b-42d3-a456-426614174006'
const operationId = '123e4567-e89b-42d3-a456-426614174007'
const item = (): StoredIncident => ({ ownerId, createdAt: Date.now(), payload: {
  operation_id: operationId, tipo: 'AVERIA', severidad: 'ALTA',
  ocurrida_en: new Date().toISOString(), latitud: -12, longitud: -77, observacion: '',
} })
const ack = { incidencia_id: otherId, operation_id: operationId, estado: 'PENDIENTE_VALIDACION', registrada_en: new Date().toISOString() }
const sync = (manual = false) => synchronizeIncidents(ownerId, new AbortController().signal, manual)

beforeEach(() => {
  vi.stubGlobal('indexedDB', new IDBFactory())
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(ack), { status: 201 })))
  vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true)
  vi.mocked(getDriverItinerary).mockReset().mockResolvedValue([])
})
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.unstubAllEnvs() })

it('ruta dorada: persiste antes de enviar y acepta 201/200 sin reenviar confirmados', async () => {
  await enqueueIncident(item())
  await sync()
  expect((await listIncidents(ownerId))[0].acknowledgement).toEqual(ack)
  await sync()
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(fetch).toHaveBeenCalledWith('http://localhost:8000/conductor/incidencias', expect.objectContaining({ credentials: 'include',
    headers: { 'Content-Type': 'application/json', 'X-Expected-Owner-ID': ownerId },
  }))
})
it('ruta de borde: offline y respuesta perdida reutilizan exactamente operación y contenido', async () => {
  const report = item()
  await enqueueIncident(report)
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false)
  await sync()
  expect(fetch).not.toHaveBeenCalled()
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true)
  vi.mocked(fetch).mockRejectedValueOnce(new TypeError('respuesta perdida'))
  await sync()
  expect((await listIncidents(ownerId))[0]).toEqual(report)
  vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify(ack), { status: 200 }))
  await Promise.all([sync(), sync()])
  const bodies = vi.mocked(fetch).mock.calls.map(call => call[1]?.body)
  expect(bodies).toEqual([JSON.stringify(report.payload), JSON.stringify(report.payload)])
  expect((await listIncidents(ownerId)).filter(entry => !entry.acknowledgement)).toHaveLength(0)
})
it.each([401, 403, 409, 422])('ruta infeliz: %i conserva contenido y pausa reintentos automáticos', async status => {
  await enqueueIncident(item())
  vi.mocked(fetch).mockResolvedValue(new Response('{}', { status }))
  await sync(); await sync()
  expect(fetch).toHaveBeenCalledTimes(1)
  expect((await listIncidents(ownerId))[0].errorStatus).toBe(status)
  await sync(true)
  expect(fetch).toHaveBeenCalledTimes(status === 401 || status === 409 ? 1 : 2)
})
it('ruta de borde: 5xx y confirmación inválida no retiran el pendiente', async () => {
  await enqueueIncident(item())
  vi.mocked(fetch).mockResolvedValueOnce(new Response('{}', { status: 503 }))
  await sync()
  expect((await listIncidents(ownerId))[0].acknowledgement).toBeUndefined()
  vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({ ...ack, operation_id: otherId }), { status: 201 }))
  await sync()
  expect((await listIncidents(ownerId))[0].acknowledgement).toBeUndefined()
})
it('ruta de borde: cuenta ajena, cambio de cookie y cancelación nunca envían el pendiente', async () => {
  await enqueueIncident(item())
  expect(await listIncidents(otherId)).toEqual([])
  await synchronizeIncidents(otherId, new AbortController().signal)
  expect(fetch).not.toHaveBeenCalled()
  vi.mocked(getDriverItinerary).mockRejectedValueOnce(new DriverItineraryServiceError('sesión cambió', false, 401))
  await sync()
  expect(fetch).not.toHaveBeenCalled()
  const controller = new AbortController(); controller.abort()
  await synchronizeIncidents(ownerId, controller.signal)
  expect(fetch).not.toHaveBeenCalled()
})
it('ruta feliz: borrador por propietario y encolado atómico elimina solo el borrador propio', async () => {
  const draft = { ...newIncidentDraft(), observacion: 'Prueba sintética' }
  await saveIncidentDraft(ownerId, draft)
  await saveIncidentDraft(otherId, draft)
  expect(await loadIncidentDraft(ownerId)).toMatchObject(draft)
  await enqueueIncident(item())
  expect(await loadIncidentDraft(ownerId)).toBeUndefined()
  expect(await loadIncidentDraft(otherId)).toMatchObject(draft)
  await removeIncidentDraft(otherId)
  expect(await loadIncidentDraft(otherId)).toBeUndefined()
  await expect(enqueueIncident(item())).rejects.toThrow()
  await updateIncident({ ...item(), errorStatus: 422 })
  expect((await listIncidents(ownerId))[0].errorStatus).toBe(422)
  await expect(listIncidents('invalid')).rejects.toThrow()
})
it('ruta de borde: base separada conserva itineraries y pendingReports del Sprint 2', async () => {
  await saveItinerary({ ownerId, savedAt: Date.now(), expiresAt: Date.now() + 60_000,
    stops: [{ stopId: otherId, position: 1, status: 'PENDIENTE' }] })
  await enqueueReport({ operationId, ownerId, stopId: otherId, status: 'ENTREGADO', createdAt: Date.now(), attemptCount: 0 })
  await enqueueIncident(item()); await sync()
  expect((await loadItinerary(ownerId))?.stops).toHaveLength(1)
  expect(await listPendingReports(ownerId)).toHaveLength(1)
})
it('ruta infeliz: falla de almacenamiento e identidad se propagan sin confirmar', async () => {
  vi.stubGlobal('indexedDB', { open: () => { throw new Error('bloqueado') } })
  await expect(saveIncidentDraft(ownerId, newIncidentDraft())).rejects.toThrow()
  await expect(enqueueIncident(item())).rejects.toThrow()
})
it('ruta infeliz: corrección de 422 es atómica y conserva operación; conflicto no admite corrección', async () => {
  const report = item()
  await enqueueIncident({ ...report, errorStatus: 422 })
  await saveIncidentDraft(ownerId, { ...newIncidentDraft(), operation_id: operationId })
  await correctRejectedIncident(ownerId, { ...report.payload, observacion: 'Corregida' })
  expect((await listIncidents(ownerId))[0].payload).toEqual({ ...report.payload, observacion: 'Corregida' })
  expect(await loadIncidentDraft(ownerId)).toBeUndefined()
  await updateIncident({ ...report, errorStatus: 409 })
  await expect(correctRejectedIncident(ownerId, report.payload)).rejects.toThrow()
})
it('ruta infeliz: respuestas sin acuse válido se rechazan', async () => {
  for (const body of [null, {}, { ...ack, incidencia_id: 'invalid' }, { ...ack, registrada_en: 'bad' }]) {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify(body), { status: 200 }))
    await expect(sendIncident(item().payload, ownerId)).rejects.toThrow()
  }
})
it('ruta infeliz: no envía sin propietario esperado válido', async () => {
  await expect(sendIncident(item().payload, 'invalid-owner')).rejects.toThrow('Identidad inválida')
  expect(fetch).not.toHaveBeenCalled()
})
it('ruta de borde: Web Locks coordina pestañas y cancelación durante verificación evita POST', async () => {
  await enqueueIncident(item())
  const request = vi.fn((_name: string, _options: unknown, task: () => Promise<void>) => task())
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request } })
  try {
    const controller = new AbortController()
    vi.mocked(getDriverItinerary).mockImplementationOnce(() => { controller.abort(); return Promise.resolve([]) })
    await synchronizeIncidents(ownerId, controller.signal)
    expect(request).toHaveBeenCalledTimes(1)
    expect(fetch).not.toHaveBeenCalled()
  } finally { Object.defineProperty(navigator, 'locks', { configurable: true, value: undefined }) }
})
