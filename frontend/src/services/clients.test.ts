import { ClientsServiceError, searchClients, shortClientId } from './clients'

const client = { cliente_id: '123e4567-e89b-12d3-a456-426614174000', nombre: 'Bodega Ficticia Norte' }
function respond(body: unknown, status = 200) {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status }))
  vi.stubGlobal('fetch', fetch)
  return fetch
}
beforeEach(() => { vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/v1') })
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs() })

describe('searchClients', () => {
  it('ruta dorada: busca con cookie, sin caché y conserva solo identificador y nombre', async () => {
    const fetch = respond({ items: [{ ...client, telefono: 'privado' }], page: 1, page_size: 8, total: 1 })
    const page = await searchClients('  bodega ')
    expect(page.items).toEqual([client])
    const [url, options] = fetch.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('https://api.example.test/v1/clientes?page=1&page_size=8&buscar=bodega')
    expect(options).toMatchObject({ credentials: 'include', cache: 'no-store' })
  })

  it('ruta feliz: sin término no envía buscar y respeta la página solicitada', async () => {
    const fetch = respond({ items: [], page: 2, page_size: 5, total: 7 })
    expect(await searchClients('   ', { page: 2, pageSize: 5 })).toMatchObject({ total: 7, page: 2 })
    expect(fetch.mock.calls[0][0]).toBe('https://api.example.test/v1/clientes?page=2&page_size=5')
  })

  it.each([[401, 'unauthorized'], [403, 'forbidden'], [422, 'validation'], [503, 'unavailable'], [409, 'unexpected']] as const)(
    'ruta infeliz: traduce %s sin exponer el detalle del servidor', async (status, kind) => {
      respond({ detail: 'SQL privado' }, status)
      const error = await searchClients('a').catch((reason: unknown) => reason)
      expect(error).toBeInstanceOf(ClientsServiceError)
      expect(error).toMatchObject({ kind })
      expect((error as Error).message).not.toContain('privado')
    })

  it('ruta infeliz: fallo de red y respuesta con forma inesperada', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
    await expect(searchClients('a')).rejects.toMatchObject({ kind: 'network' })
    respond({ items: [{ cliente_id: 1 }], page: 1, page_size: 8, total: 1 })
    await expect(searchClients('a')).rejects.toMatchObject({ kind: 'unexpected' })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('no-json', { status: 200 })))
    await expect(searchClients('a')).rejects.toMatchObject({ kind: 'unexpected' })
  })

  it('ruta de borde: recorta a 160 caracteres, propaga la cancelación y abrevia el ID', async () => {
    const fetch = respond({ items: [], page: 1, page_size: 8, total: 0 })
    await searchClients('x'.repeat(200))
    expect(new URL(fetch.mock.calls[0][0] as string).searchParams.get('buscar')).toHaveLength(160)
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new DOMException('aborted', 'AbortError')))
    await expect(searchClients('a')).rejects.toMatchObject({ name: 'AbortError' })
    expect(shortClientId(client.cliente_id)).toBe('123e4567')
  })
})
