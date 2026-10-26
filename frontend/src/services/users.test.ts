import {
  changePassword, isPasswordChangeRequired, listUsers, PASSWORD_CHANGE_REQUIRED_DETAIL, resetPassword, UserServiceError,
} from './users'

const id = '123e4567-e89b-12d3-a456-426614174000'
const user = { usuario_id: id, email: 'operador.demo@example.test', rol: 'OPERADOR', estado: 'ACTIVO', debe_cambiar_contrasena: false }
const fetchMock = vi.fn<typeof fetch>()

function reply(status: number, body?: unknown) {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status, headers: { 'Content-Type': 'application/json' },
  })
}

beforeEach(() => {
  vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/v1')
  vi.stubGlobal('fetch', fetchMock)
  fetchMock.mockReset()
})
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals() })

it('fija el detalle exacto del 403 de cambio obligatorio', () => {
  expect(PASSWORD_CHANGE_REQUIRED_DETAIL).toBe('Cambio de contraseña requerido')
  expect(isPasswordChangeRequired(403, { detail: 'Cambio de contraseña requerido' })).toBe(true)
  expect(isPasswordChangeRequired(403, { detail: 'Acceso denegado' })).toBe(false)
  expect(isPasswordChangeRequired(401, { detail: 'Cambio de contraseña requerido' })).toBe(false)
})

it('lista usuarios paginados con cookie y sin caché', async () => {
  fetchMock.mockResolvedValue(reply(200, { items: [user], page: 2, page_size: 20, total: 21 }))
  await expect(listUsers(2, 20)).resolves.toEqual({ items: [user], page: 2, page_size: 20, total: 21 })
  const [url, init] = fetchMock.mock.calls[0]
  expect(url).toBe('https://api.example.test/v1/usuarios?page=2&page_size=20')
  expect(init).toMatchObject({ method: 'GET', credentials: 'include', cache: 'no-store' })
})

it.each([
  [{ items: [{ ...user, rol: 'ROOT' }], page: 1, page_size: 20, total: 1 }],
  [{ items: [{ ...user, usuario_id: 'x' }], page: 1, page_size: 20, total: 1 }],
  [{ items: [user], page: 3, page_size: 20, total: 1 }],
  [null],
])('rechaza listados inválidos', async body => {
  fetchMock.mockResolvedValue(reply(200, body))
  await expect(listUsers()).rejects.toMatchObject({ kind: 'unexpected' })
})

it('rechaza páginas inválidas sin llamar al API', async () => {
  await expect(listUsers(0)).rejects.toBeInstanceOf(UserServiceError)
  await expect(listUsers(1, 101)).rejects.toBeInstanceOf(UserServiceError)
  expect(fetchMock).not.toHaveBeenCalled()
})

it.each([
  [401, {}, 'unauthorized'],
  [403, { detail: 'Acceso denegado' }, 'forbidden'],
  [403, { detail: 'Cambio de contraseña requerido' }, 'password_change_required'],
  [404, {}, 'not_found'],
  [409, {}, 'conflict'],
  [422, {}, 'validation'],
  [400, {}, 'current_invalid'],
  [503, {}, 'unavailable'],
  [418, {}, 'unexpected'],
])('traduce HTTP %i a un mensaje sin culpar', async (status, body, kind) => {
  fetchMock.mockResolvedValue(reply(status, body))
  const error = await resetPassword(id).catch((caught: unknown) => caught)
  expect(error).toMatchObject({ kind })
  expect((error as Error).message).not.toMatch(/error tuyo|culpa/iu)
})

it('restablece y devuelve la temporal una sola vez', async () => {
  fetchMock.mockResolvedValue(reply(200, { contrasena_temporal: 'Synthetic16Chars', expira_en: '2026-10-26T12:00:00Z' }))
  await expect(resetPassword(id)).resolves.toEqual({ contrasena_temporal: 'Synthetic16Chars', expira_en: '2026-10-26T12:00:00Z' })
  expect(fetchMock.mock.calls[0][0]).toBe(`https://api.example.test/v1/usuarios/${id}/restablecer-contrasena`)
  expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'POST', cache: 'no-store' })
})

it('valida el id y la respuesta del restablecimiento', async () => {
  await expect(resetPassword('../x')).rejects.toMatchObject({ kind: 'unexpected' })
  fetchMock.mockResolvedValue(reply(200, { contrasena_temporal: 'short', expira_en: 'mañana' }))
  await expect(resetPassword(id)).rejects.toMatchObject({ kind: 'unexpected' })
})

it('cambia la contraseña con 204 y avisa de red caída', async () => {
  fetchMock.mockResolvedValue(new Response(null, { status: 204 }))
  await expect(changePassword('temporal-actual', 'definitiva-larga')).resolves.toBeUndefined()
  const init = fetchMock.mock.calls[0][1]!
  expect(JSON.parse(init.body as string)).toEqual({ contrasena_actual: 'temporal-actual', contrasena_nueva: 'definitiva-larga' })
  fetchMock.mockRejectedValue(new TypeError('offline'))
  await expect(changePassword('a', 'b')).rejects.toMatchObject({ kind: 'network' })
  fetchMock.mockResolvedValue(reply(200, {}))
  await expect(changePassword('a', 'b')).rejects.toMatchObject({ kind: 'unexpected' })
})

it('sin URL del API falla de forma controlada', async () => {
  vi.stubEnv('VITE_API_BASE_URL', '')
  await expect(listUsers()).rejects.toMatchObject({ kind: 'unexpected' })
})
