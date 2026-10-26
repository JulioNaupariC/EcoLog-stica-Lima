import { installPasswordChangeGuard } from './passwordChangeGuard'

const REQUIRED = 'Cambio de contraseña requerido'
const fetchMock = vi.fn<typeof fetch>()
function reply(status: number, detail: string) {
  return new Response(JSON.stringify({ detail }), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/v1')
  vi.stubGlobal('fetch', fetchMock)
  fetchMock.mockReset()
})
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); vi.unstubAllGlobals() })

it('avisa solo ante el 403 exacto del API y devuelve la misma respuesta sin leerla', async () => {
  const onRequired = vi.fn()
  const uninstall = installPasswordChangeGuard(onRequired)
  const original = reply(403, REQUIRED)
  fetchMock.mockResolvedValueOnce(original)
  const response = await fetch('https://api.example.test/v1/vehiculos')
  expect(response).toBe(original)
  expect(response.bodyUsed).toBe(false)
  await expect(response.json()).resolves.toEqual({ detail: REQUIRED })
  expect(onRequired).toHaveBeenCalledTimes(1)
  uninstall()
})

it('solo clona respuestas 403 cuyo URL empieza por VITE_API_BASE_URL', async () => {
  const clone = vi.spyOn(Response.prototype, 'clone')
  const onRequired = vi.fn()
  const uninstall = installPasswordChangeGuard(onRequired)
  const cases: [string | URL | Request, Response][] = [
    ['https://api.example.test/v1/vehiculos', reply(200, REQUIRED)],
    ['https://api.example.test/v1/vehiculos', reply(401, REQUIRED)],
    ['https://otro.example.test/v1/x', reply(403, REQUIRED)],
    // Same origin, outside the API base path.
    ['https://api.example.test/otra-app/x', reply(403, REQUIRED)],
    ['https://api.example.test/v10/x', reply(403, REQUIRED)],
  ]
  for (const [input, response] of cases) {
    fetchMock.mockResolvedValueOnce(response)
    expect(await fetch(input)).toBe(response)
  }
  expect(clone).not.toHaveBeenCalled()
  expect(onRequired).not.toHaveBeenCalled()

  fetchMock.mockResolvedValueOnce(reply(403, 'Acceso denegado'))
  await fetch(new URL('https://api.example.test/v1/usuarios'))
  fetchMock.mockResolvedValueOnce(new Response('<html>', { status: 403 }))
  await fetch(new Request('https://api.example.test/v1/pedidos'))
  expect(clone).toHaveBeenCalledTimes(2)
  expect(onRequired).not.toHaveBeenCalled()
  uninstall()
})

it('al retirarse restaura fetch y deja de observar', async () => {
  const onRequired = vi.fn()
  const uninstall = installPasswordChangeGuard(onRequired)
  expect(globalThis.fetch).not.toBe(fetchMock)
  uninstall()
  expect(globalThis.fetch).toBe(fetchMock)
  fetchMock.mockResolvedValueOnce(reply(403, REQUIRED))
  await fetch('https://api.example.test/v1/vehiculos')
  expect(onRequired).not.toHaveBeenCalled()
})

it('no pisa un fetch instalado después de él', () => {
  const uninstall = installPasswordChangeGuard(vi.fn())
  const later = vi.fn<typeof fetch>()
  globalThis.fetch = later
  uninstall()
  expect(globalThis.fetch).toBe(later)
})

it('sin API configurada no clona ni intercepta nada', async () => {
  vi.stubEnv('VITE_API_BASE_URL', '')
  const clone = vi.spyOn(Response.prototype, 'clone')
  const onRequired = vi.fn()
  const uninstall = installPasswordChangeGuard(onRequired)
  fetchMock.mockResolvedValueOnce(reply(403, REQUIRED))
  await fetch('https://api.example.test/v1/vehiculos')
  expect(clone).not.toHaveBeenCalled()
  expect(onRequired).not.toHaveBeenCalled()
  uninstall()
})
