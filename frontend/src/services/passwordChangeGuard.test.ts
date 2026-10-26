import { installPasswordChangeGuard } from './passwordChangeGuard'

const fetchMock = vi.fn<typeof fetch>()
function reply(status: number, detail: string) {
  return new Response(JSON.stringify({ detail }), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/v1')
  vi.stubGlobal('fetch', fetchMock)
  fetchMock.mockReset()
})
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals() })

it('avisa solo ante el 403 exacto del API y no altera la respuesta', async () => {
  const onRequired = vi.fn()
  const uninstall = installPasswordChangeGuard(onRequired)
  fetchMock.mockResolvedValueOnce(reply(403, 'Cambio de contraseña requerido'))
  const response = await fetch('https://api.example.test/v1/vehiculos')
  expect(onRequired).toHaveBeenCalledTimes(1)
  await expect(response.json()).resolves.toEqual({ detail: 'Cambio de contraseña requerido' })

  fetchMock.mockResolvedValueOnce(reply(403, 'Acceso denegado'))
  await fetch(new URL('https://api.example.test/v1/usuarios'))
  fetchMock.mockResolvedValueOnce(reply(403, 'Cambio de contraseña requerido'))
  await fetch('https://otro.example.test/x')
  fetchMock.mockResolvedValueOnce(new Response('<html>', { status: 403 }))
  await fetch(new Request('https://api.example.test/v1/pedidos'))
  expect(onRequired).toHaveBeenCalledTimes(1)

  uninstall()
  expect(globalThis.fetch).toBe(fetchMock)
})

it('sin API configurada no intercepta nada', async () => {
  vi.stubEnv('VITE_API_BASE_URL', '')
  const onRequired = vi.fn()
  const uninstall = installPasswordChangeGuard(onRequired)
  fetchMock.mockResolvedValueOnce(reply(403, 'Cambio de contraseña requerido'))
  await fetch('https://api.example.test/v1/vehiculos')
  expect(onRequired).not.toHaveBeenCalled()
  uninstall()
})
