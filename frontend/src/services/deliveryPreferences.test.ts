import { getDeliveryPreferences, PreferencesServiceError, updateDeliveryPreferences } from './deliveryPreferences'
import type { PreferencesPatch } from './deliveryPreferences'

const id = '123e4567-e89b-12d3-a456-426614174000'
const saved = { cliente_id: id, horario_preferido: ' Mañana ', referencia: 'Puerta norte', restriccion_acceso: null }
function respond(body: unknown, status = 200) {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status }))
  vi.stubGlobal('fetch', fetch)
  return fetch
}
beforeEach(() => { vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/v1') })
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs() })

it('consulta con cookie y sin cache; preserva texto y descarta campos ajenos', async () => {
  const fetch = respond({ ...saved, telefono: 'private', nombre: 'private' })
  expect(await getDeliveryPreferences(id)).toEqual(saved)
  expect(fetch).toHaveBeenCalledWith(`https://api.example.test/v1/clientes/${id}/preferencias`, {
    method: 'GET', credentials: 'include', cache: 'no-store',
  })
})
it('envía solo cambios admitidos y null explícito', async () => {
  const fetch = respond(saved)
  await updateDeliveryPreferences(id, { referencia: null, nombre: 'ignored', horario_preferido: undefined } as PreferencesPatch)
  const options = fetch.mock.calls[0][1] as RequestInit
  expect(options.method).toBe('PATCH')
  expect(options.headers).toEqual({ 'Content-Type': 'application/json' })
  expect(JSON.parse(options.body as string)).toEqual({ referencia: null })
})
it('acepta UUID con capitalización distinta y preferencias sin definir', async () => {
  respond({ ...saved, horario_preferido: null, referencia: null })
  expect(await getDeliveryPreferences(id.toUpperCase())).toMatchObject({ horario_preferido: null, referencia: null })
})
it.each([[401, 'unauthorized'], [403, 'forbidden'], [404, 'not_found'], [422, 'validation'],
  [500, 'unavailable'], [503, 'unavailable'], [409, 'unexpected']] as const)('traduce %s con mensaje seguro', async (status, kind) => {
  respond({ detail: 'private SQL and credentials' }, status)
  await expect(getDeliveryPreferences(id)).rejects.toMatchObject({ kind })
  try { await getDeliveryPreferences(id) } catch (error) { expect((error as Error).message).not.toContain('private') }
})
it('mapea campos 422 conocidos sin confiar en mensajes o rutas del servidor', async () => {
  respond({ detail: [{ loc: ['body', 'referencia'], msg: 'private' }, { loc: ['body', 'referencia'] },
    { loc: ['body', 'horario_preferido'] }, { loc: ['query', 'referencia'] },
    { loc: ['body', 'nombre'] }, { loc: 'invalid' }, null] }, 422)
  await expect(updateDeliveryPreferences(id, { referencia: 'A' })).rejects.toMatchObject({ fields: ['referencia', 'horario_preferido'] })
})
it.each([null, [], {}, { ...saved, cliente_id: '223e4567-e89b-12d3-a456-426614174000' },
  { ...saved, cliente_id: 1 }, { ...saved, referencia: 1 }, { ...saved, horario_preferido: undefined },
  { ...saved, restriccion_acceso: {} }])('rechaza una respuesta malformada o de otro cliente', async body => {
  respond(body)
  await expect(getDeliveryPreferences(id)).rejects.toBeInstanceOf(PreferencesServiceError)
})
it('rechaza IDs y PATCH vacío antes de fetch', async () => {
  const fetch = respond(saved)
  await expect(getDeliveryPreferences('../login')).rejects.toMatchObject({ kind: 'unexpected' })
  await expect(updateDeliveryPreferences(id, {})).rejects.toMatchObject({ kind: 'validation' })
  expect(fetch).not.toHaveBeenCalled()
})
it('controla red, configuración inválida, JSON ilegible y status exitoso inesperado', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('private')))
  await expect(getDeliveryPreferences(id)).rejects.toMatchObject({ kind: 'network' })
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('not-json', { status: 503 })))
  await expect(getDeliveryPreferences(id)).rejects.toMatchObject({ kind: 'unavailable' })
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('not-json', { status: 200 })))
  await expect(getDeliveryPreferences(id)).rejects.toMatchObject({ kind: 'unexpected' })
  respond(saved, 201)
  await expect(getDeliveryPreferences(id)).rejects.toMatchObject({ kind: 'unexpected' })
  vi.stubEnv('VITE_API_BASE_URL', '')
  await expect(getDeliveryPreferences(id)).rejects.toMatchObject({ kind: 'unexpected' })
})
