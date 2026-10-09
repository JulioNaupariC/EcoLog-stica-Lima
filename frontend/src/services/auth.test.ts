import { AuthServiceError, login, logout } from './auth'
import type { AuthRole, LoginRequest } from './auth'

const payload: LoginRequest = {
  email: 'User@example.test',
  password: 'private-password',
}

const usuario_id = '123e4567-e89b-12d3-a456-426614174000'

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('servicio de autenticación', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('usa la URL base, POST, JSON, credenciales y únicamente los campos del contrato', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/v1')
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ usuario_id, rol: 'OPERADOR' }, 200))
    vi.stubGlobal('fetch', fetchMock)

    await expect(login({ ...payload, usuario_id: 'not-sent' } as LoginRequest)).resolves.toEqual({
      usuario_id,
      rol: 'OPERADOR',
    })
    expect(fetchMock).toHaveBeenCalledExactlyOnceWith('https://api.example.test/v1/login', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  })

  it.each<AuthRole>([
    'ADMINISTRADOR',
    'OPERADOR',
    'CONDUCTOR',
    'ANALISTA',
    'AUDITOR',
  ])('acepta la identidad real con rol %s', async (rol) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ usuario_id, rol }, 200)))
    await expect(login(payload)).resolves.toEqual({ usuario_id, rol })
  })

  it.each([
    { usuario_id, rol: 'SUPERUSUARIO' },
    { usuario_id },
    { rol: 'OPERADOR' },
    { usuario_id: 'no-es-uuid', rol: 'OPERADOR' },
    null,
    [],
  ])('rechaza respuestas incompletas o con identidad desconocida', async (body) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(body, 200)))
    await expect(login(payload)).rejects.toMatchObject({
      kind: 'unexpected',
      message: 'El servicio devolvió una respuesta inválida.',
      status: 200,
    })
  })

  it('rechaza JSON inválido y un status de éxito diferente de 200', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response('no-json', { status: 200 }))
      .mockResolvedValueOnce(jsonResponse({ usuario_id, rol: 'OPERADOR' }, 201))
    vi.stubGlobal('fetch', fetchMock)
    await expect(login(payload)).rejects.toMatchObject({ kind: 'unexpected', status: 200 })
    await expect(login(payload)).rejects.toMatchObject({ kind: 'unexpected', status: 201 })
  })

  it.each([
    [401, 'unauthorized', 'Credenciales inválidas.'],
    [403, 'unexpected', 'No se pudo iniciar sesión.'],
    [503, 'unavailable', 'El servicio no está disponible en este momento.'],
    [500, 'unexpected', 'No se pudo iniciar sesión.'],
  ] as const)('mapea HTTP %s sin revelar detalles del servidor', async (status, kind, message) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'private-password' }, status)))
    const error = await login(payload).catch((caught: unknown) => caught)
    expect(error).toBeInstanceOf(AuthServiceError)
    expect(error).toMatchObject({ kind, message, status, issues: [] })
    expect(String(error)).not.toContain(payload.password)
  })

  it('tolera errores HTTP con cuerpo no JSON', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('internal detail', { status: 500 })))
    await expect(login(payload)).rejects.toMatchObject({
      kind: 'unexpected',
      message: 'No se pudo iniciar sesión.',
    })
  })

  it('mapea solo campos conocidos del 422 con mensajes propios', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({
      detail: [
        { loc: ['body', 'email'], msg: 'Valor recibido: private-password', input: payload.password },
        { loc: ['body', 'password'], msg: 'Valor recibido: private-password', ctx: { secret: payload.password } },
        { loc: ['body', 'rol'], msg: 'desconocido' },
        { loc: ['query', 'email'], msg: 'otro lugar' },
        { loc: ['body'], msg: 'global' },
        { loc: ['body', 'password'], msg: { secret: payload.password } },
        null,
      ],
    }, 422)))

    const error = await login(payload).catch((caught: unknown) => caught)
    expect(error).toMatchObject({
      kind: 'validation',
      message: 'Revisa los datos ingresados.',
      status: 422,
      issues: [
        { field: 'email', message: 'Revisa el correo electrónico.' },
        { field: 'password', message: 'Revisa la contraseña.' },
      ],
    })
    expect(JSON.stringify(error)).not.toContain(payload.password)
  })

  it.each([{ detail: 'private-password' }, { detail: [{ loc: 'body' }] }, null])(
    'tolera un 422 no estructurado',
    async (body) => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(body, 422)))
      await expect(login(payload)).rejects.toMatchObject({
        kind: 'validation',
        issues: [],
      })
    },
  )

  it('distingue un fallo de red sin exponer el error del transporte', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error(payload.password)))
    const error = await login(payload).catch((caught: unknown) => caught)
    expect(error).toMatchObject({ kind: 'network', message: 'No se pudo conectar con el servicio.' })
    expect(String(error)).not.toContain(payload.password)
  })

  it('no inicia fetch si la URL base no es válida', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'ftp://example.test')
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    await expect(login(payload)).rejects.toMatchObject({
      kind: 'unexpected',
      message: 'No se pudo iniciar sesión.',
    })
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('revoca la sesión autenticada y exige la respuesta 204 de logout', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(logout()).resolves.toBeUndefined()

    expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
      'http://127.0.0.1:8000/logout',
      { method: 'POST', credentials: 'include' },
    )
  })

  it.each([
    [401, 'unexpected', 'No se pudo cerrar la sesión.'],
    [503, 'unavailable', 'El servicio no está disponible para cerrar la sesión.'],
    [500, 'unexpected', 'No se pudo cerrar la sesión.'],
  ] as const)('maneja cierre de sesión HTTP %s sin aceptar la operación', async (status, kind, message) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status })))

    await expect(logout()).rejects.toMatchObject({ kind, message, status })
  })

  it('conserva el error de sesión si falla el transporte de logout', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('private details')))

    await expect(logout()).rejects.toMatchObject({
      kind: 'network',
      message: 'No se pudo conectar para cerrar la sesión.',
    })
  })
})
