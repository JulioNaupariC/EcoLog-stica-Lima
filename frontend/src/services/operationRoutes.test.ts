import completed from '../test/fixtures/rutas/optimizacion-completada.json'
import { InvalidRouteData } from '../domain/operationRoutes'
import { operationRoutesApi } from './operationRoutes'

const page = { items: [completed], total: 1, page: 1, page_size: 12, simulado: true }
const signal = () => new AbortController().signal
const reply = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status })
beforeEach(() => { vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000'); vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reply(page))) })
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals() })

it('consulta fecha y paginación con cookie, sin caché y con cancelación', async () => {
  const result = await operationRoutesApi.list('2026-11-20', 1, signal())
  expect(result.items[0].optimizacion_id).toBe(completed.optimizacion_id)
  expect(fetch).toHaveBeenCalledWith('http://127.0.0.1:8000/optimizaciones?fecha=2026-11-20&page=1&page_size=12',
    expect.objectContaining({ credentials: 'include', cache: 'no-store' }))
  expect(vi.mocked(fetch).mock.calls[0][1]?.signal).toBeInstanceOf(AbortSignal)
})
it('consulta detalle, preserva simulado y declara SIN_DATOS en ST-045', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(completed))
  const result = await operationRoutesApi.detail(completed.optimizacion_id, signal())
  expect(result.trafico.estado).toBe('SIN_DATOS')
  expect(result.simulado).toBe(true)
})
it.each([[401, 'unauthorized'], [403, 'forbidden'], [404, 'not_found'], [503, 'unavailable'], [422, 'unavailable']])('M04: HTTP %s produce error seguro %s', async (status, kind) => {
  vi.mocked(fetch).mockResolvedValue(reply('PRIVATE', Number(status)))
  await expect(operationRoutesApi.detail(completed.optimizacion_id, signal())).rejects.toMatchObject({ kind })
})
it('rechaza errores de red y JSON sin eco', async () => {
  vi.mocked(fetch).mockRejectedValueOnce(new Error('PRIVATE'))
  await expect(operationRoutesApi.detail(completed.optimizacion_id, signal())).rejects.toMatchObject({ kind: 'unavailable' })
  vi.mocked(fetch).mockResolvedValueOnce(new Response('PRIVATE'))
  await expect(operationRoutesApi.detail(completed.optimizacion_id, signal())).rejects.toBeInstanceOf(InvalidRouteData)
})
it('no envía fechas o IDs inválidos y rechaza respuestas de otro contexto', async () => {
  await expect(operationRoutesApi.list('2026-02-30', 1, signal())).rejects.toBeInstanceOf(InvalidRouteData)
  await expect(operationRoutesApi.list('2026-11-20', 0, signal())).rejects.toBeInstanceOf(InvalidRouteData)
  await expect(operationRoutesApi.detail('private', signal())).rejects.toBeInstanceOf(InvalidRouteData)
  expect(fetch).not.toHaveBeenCalled()
  vi.mocked(fetch).mockResolvedValueOnce(reply({ ...page, page: 2 }))
  await expect(operationRoutesApi.list('2026-11-20', 1, signal())).rejects.toBeInstanceOf(InvalidRouteData)
  vi.mocked(fetch).mockResolvedValueOnce(reply(completed))
  await expect(operationRoutesApi.detail('123e4567-e89b-42d3-a456-426614174000', signal())).rejects.toBeInstanceOf(InvalidRouteData)
})
it('propaga cancelación sin procesarla como caída del servicio', async () => {
  const controller = new AbortController(); controller.abort()
  const failure = new DOMException('Aborted', 'AbortError')
  vi.mocked(fetch).mockRejectedValue(failure)
  await expect(operationRoutesApi.detail(completed.optimizacion_id, controller.signal)).rejects.toBe(failure)
})
