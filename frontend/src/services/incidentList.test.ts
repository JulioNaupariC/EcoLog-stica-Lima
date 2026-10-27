import { IncidentListError, listPendingIncidents } from './incidentList'
import { pendingIncident as item, pendingIncidentPage as page } from '../test/incidentFixtures'

const fetchMock = vi.fn<typeof fetch>()
function reply(body: unknown = page, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000')
  vi.stubGlobal('fetch', fetchMock)
  fetchMock.mockReset().mockResolvedValue(reply())
})
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals() })

it('I02/I15: solicita la página real de pendientes con cookie, sin caché y con señal', async () => {
  fetchMock.mockResolvedValue(reply({ ...page, page: 2, total: 21 }))
  await expect(listPendingIncidents(2)).resolves.toEqual({ ...page, page: 2, total: 21 })
  const [url, init] = fetchMock.mock.calls[0]
  expect(url).toBe('http://127.0.0.1:8000/incidencias?estado=PENDIENTE_VALIDACION&page=2&page_size=20')
  expect(init).toMatchObject({ credentials: 'include', cache: 'no-store' })
  expect(init?.signal).toBeInstanceOf(AbortSignal)
})

it('ordena por el instante de ocurrencia, con ID ascendente en empate', async () => {
  const newer = { ...item, incidencia_id: '323e4567-e89b-42d3-a456-426614174000', ocurrida_en: '2026-10-26T10:00:00-05:00' }
  const tied = { ...item, incidencia_id: '423e4567-e89b-42d3-a456-426614174000', ocurrida_en: '2026-10-26T15:00:00Z' }
  fetchMock.mockResolvedValue(reply({ ...page, items: [item, tied, newer], total: 3 }))
  const result = await listPendingIncidents()
  expect(result.items.map(incident => incident.incidencia_id)).toEqual([newer.incidencia_id, tied.incidencia_id, item.incidencia_id])
})

it('I02: descarta campos personales extra aunque aparezcan en la respuesta', async () => {
  fetchMock.mockResolvedValue(reply({ ...page, items: [{ ...item,
    conductor: { ...item.conductor, dni: 'SYNTHETIC', telefono: 'SYNTHETIC', licencia: 'SYNTHETIC' },
    usuario_email: 'synthetic@example.test' }] }))
  expect((await listPendingIncidents()).items).toEqual([item])
})

it('acepta páginas vacías, incluidas las posteriores al total', async () => {
  fetchMock.mockResolvedValue(reply({ items: [], page: 3, page_size: 20, total: 2 }))
  await expect(listPendingIncidents(3)).resolves.toEqual({ items: [], page: 3, page_size: 20, total: 2 })
})

it.each([[0, 20], [1.5, 20], [1, 0], [1, 101], [1, 2.5]])('rechaza paginación inválida %s/%s antes de consultar', async (number, size) => {
  await expect(listPendingIncidents(number, size)).rejects.toBeInstanceOf(IncidentListError)
  expect(fetchMock).not.toHaveBeenCalled()
})

it.each([
  [401, 'unauthorized'], [403, 'forbidden'], [422, 'unexpected'], [503, 'unavailable'], [201, 'unexpected'],
])('traduce HTTP %s sin mostrar el cuerpo ni datos enviados', async (status, kind) => {
  fetchMock.mockResolvedValue(reply({ detail: 'PRIVATE_DETAIL_MUST_NOT_APPEAR' }, status))
  const error = await listPendingIncidents().catch((caught: unknown) => caught)
  expect(error).toMatchObject({ kind })
  expect((error as Error).message).not.toContain('PRIVATE_DETAIL')
})

it('informa fallo de red y respeta la cancelación del consumidor', async () => {
  const offline = new TypeError('private network detail')
  fetchMock.mockRejectedValue(offline)
  await expect(listPendingIncidents()).rejects.toMatchObject({ kind: 'network' })
  const controller = new AbortController()
  controller.abort()
  await expect(listPendingIncidents(1, 20, controller.signal)).rejects.toBe(offline)
})

it('rechaza configuración o JSON inválidos', async () => {
  vi.stubEnv('VITE_API_BASE_URL', '')
  await expect(listPendingIncidents()).rejects.toMatchObject({ kind: 'unexpected' })
  expect(fetchMock).not.toHaveBeenCalled()
  vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000')
  fetchMock.mockResolvedValue(new Response('not-json', { status: 200 }))
  await expect(listPendingIncidents()).rejects.toMatchObject({ kind: 'unexpected' })
})

it.each([
  null, [], { ...page, page: 2 }, { ...page, page_size: 100 }, { ...page, total: -1 },
  { ...page, total: 1.5 }, { ...page, items: {} }, { ...page, total: 0 },
  { ...page, items: Array.from({ length: 21 }, () => item), total: 21 },
])('rechaza metadatos de página inconsistentes', async body => {
  fetchMock.mockResolvedValue(reply(body))
  await expect(listPendingIncidents()).rejects.toMatchObject({ kind: 'unexpected' })
})

it.each([
  null, { ...item, incidencia_id: 'invalid' }, { ...item, tipo: 'NEW_TYPE' },
  { ...item, severidad: 'CRITICA' }, { ...item, ocurrida_en: 'not-a-date' },
  { ...item, ocurrida_en: '2026-10-26T09:00:00' }, { ...item, registrada_en: null },
  { ...item, conductor: null }, { ...item, conductor: { conductor_id: 'bad', nombre: 'Ejemplo' } },
  { ...item, conductor: { ...item.conductor, nombre: ' ' } },
  { ...item, latitud: '-12' }, { ...item, latitud: 91 }, { ...item, longitud: 181 },
  { ...item, longitud: null }, { ...item, observacion: null }, { ...item, observacion: 'x'.repeat(501) },
  { ...item, estado: 'VALIDADA' },
])('rechaza incidencias fuera del contrato aprobado antes de renderizarlas', async invalid => {
  fetchMock.mockResolvedValue(reply({ ...page, items: [invalid] }))
  await expect(listPendingIncidents()).rejects.toMatchObject({ kind: 'unexpected' })
})
