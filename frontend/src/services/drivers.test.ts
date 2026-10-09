import { createDriver, DriverServiceError, getDriver, listDrivers, updateDriver } from './drivers'
import type { DriverCreate, DriverDetail } from './drivers'

const id = '123e4567-e89b-12d3-a456-426614174000'
const payload: DriverCreate = { nombre: 'Prueba', dni: '01234567', licencia_numero: 'LIC-01',
  licencia_vigente_hasta: '2099-12-31', experiencia_anios: 3, telefono: '+51987654321',
  punto_partida: 'Base', disponible_desde: '2099-10-09T13:00:00Z', disponible_hasta: '2099-10-09T22:00:00Z',
  email: 'prueba@example.test', password: 'synthetic-password' }
const row: DriverDetail = { ...payload, conductor_id: id, usuario_id: id, estado: 'ACTIVO', habilitado_asignacion: true }
const page = { items: [row], page: 1, page_size: 10, total: 1 }
function respond(body: unknown, status = 200) {
  const mock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify(body), { status })))
  vi.stubGlobal('fetch', mock)
  return mock
}
beforeEach(() => { vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/v1') })
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs() })

it('lista con paginación y cookie, descarta datos personales extra', async () => {
  const fetch = respond(page)
  const result = await listDrivers()
  expect(result.total).toBe(1)
  expect(result.items[0]).not.toHaveProperty('dni')
  expect(result.items[0]).not.toHaveProperty('password')
  expect(fetch).toHaveBeenCalledWith('https://api.example.test/v1/conductores?page=1&page_size=10', { method: 'GET', credentials: 'include' })
})
it('alta envía únicamente el contrato, sin propietario, rol ni hash', async () => {
  const fetch = respond(row, 201)
  const result = await createDriver({ ...payload, password_hash: 'never-send', rol: 'ADMINISTRADOR' } as DriverCreate)
  expect(result).not.toHaveProperty('dni')
  expect(result).not.toHaveProperty('password')
  const options = fetch.mock.calls[0][1] as RequestInit
  expect(JSON.parse(options.body as string)).toEqual(payload)
  expect(options.credentials).toBe('include')
})
it('consulta y PATCH conservan perfiles y null para retirar disponibilidad', async () => {
  const fetch = respond(row)
  expect(await getDriver(id)).toMatchObject({ dni: '01234567' })
  await updateDriver(id, { disponible_desde: null, disponible_hasta: null, email: 'never-send' } as Partial<DriverCreate>)
  expect(fetch.mock.calls[1][0]).toBe('https://api.example.test/v1/conductores/' + id)
  expect(JSON.parse((fetch.mock.calls[1][1] as RequestInit).body as string)).toEqual({ disponible_desde: null, disponible_hasta: null })
})

it.each([[401, 'unauthorized'], [403, 'forbidden'], [404, 'not_found'], [409, 'conflict'],
  [422, 'validation'], [500, 'unavailable'], [503, 'unavailable'], [400, 'unexpected']] as const)('traduce HTTP %s sin mostrar texto del servidor', async (status, kind) => {
  respond({ detail: 'private SQL and password' }, status)
  await expect(listDrivers()).rejects.toMatchObject({ kind })
  try { await listDrivers() } catch (error) {
    expect((error as Error).message).not.toContain('private')
  }
})
it('mapea sólo campos conocidos de 422, ignorando texto y ubicaciones ajenas', async () => {
  respond({ detail: [
    { loc: ['body', 'dni'], msg: 'private' }, { loc: ['body', 'dni'] },
    { loc: ['body', 'password'] }, { loc: ['query', 'page'] },
    { loc: ['body', 'password_hash'] }, { msg: 'malformed' }, null,
  ] }, 422)
  await expect(createDriver(payload)).rejects.toMatchObject({ fields: ['dni', 'password'] })
})
it.each([
  {}, { ...page, page: 2 }, { ...page, page_size: 20 }, { ...page, total: -1 }, { ...page, total: 1.5 },
  { ...page, items: null }, { ...page, items: Array.from({ length: 11 }, () => row) },
  { ...page, items: [{ ...row, conductor_id: 'invalid' }] },
  { ...page, items: [{ ...row, disponible_desde: 'no-zone' }] },
  { ...page, items: [{ ...row, habilitado_asignacion: 'true' }] },
  { ...page, items: [{ ...row, estado: 'UNKNOWN' }] },
])('rechaza listado malformado', async body => {
  respond(body)
  await expect(listDrivers()).rejects.toBeInstanceOf(DriverServiceError)
})
it.each([{ ...row, dni: 123 }, { ...row, usuario_id: 'invalid' },
  { ...row, experiencia_anios: 1.5 }, { ...row, licencia_vigente_hasta: 'bad' }])('rechaza detalle malformado', async body => {
  respond(body)
  await expect(getDriver(id)).rejects.toMatchObject({ kind: 'unexpected' })
})
it('rechaza IDs y páginas inválidos antes de fetch', async () => {
  const fetch = respond(page)
  await expect(getDriver('../login')).rejects.toMatchObject({ kind: 'unexpected' })
  await expect(listDrivers(0)).rejects.toMatchObject({ kind: 'unexpected' })
  expect(fetch).not.toHaveBeenCalled()
})
it('controla red, JSON incorrecto, status inesperado y configuración inválida', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('private')))
  await expect(listDrivers()).rejects.toMatchObject({ kind: 'network' })
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('not JSON', { status: 503 })))
  await expect(listDrivers()).rejects.toMatchObject({ kind: 'unavailable' })
  respond(row, 200)
  await expect(createDriver(payload)).rejects.toMatchObject({ kind: 'unexpected' })
  vi.stubEnv('VITE_API_BASE_URL', '')
  await expect(listDrivers()).rejects.toMatchObject({ kind: 'unexpected' })
})
