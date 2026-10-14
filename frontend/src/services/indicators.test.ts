import { getOperationIndicators, IndicatorsServiceError } from './indicators'

const body = {
  generado_en: '2026-10-14T09:30:00-05:00',
  vigencia_segundos: 30,
  vehiculos: { total: 50, activos: 45, capacidad_kg_activa: '76500.00' },
  conductores: { total: 200, habilitados_asignacion: 145, no_habilitados: 55 },
  pedidos: { total: 30000, por_estado: { PENDIENTE: 30000 }, por_prioridad: { EXPRESS: 6000, ESTANDAR: 15000, ECONOMICO: 9000 } },
}

function respond(payload: unknown, status = 200) {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status }))
  vi.stubGlobal('fetch', fetch)
  return fetch
}
beforeEach(() => { vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/v1') })
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs() })

describe('getOperationIndicators', () => {
  it('ruta dorada: una petición con cookie que respeta la caché privada del servidor', async () => {
    const fetch = respond(body)
    const result = await getOperationIndicators()
    expect(result).toEqual({
      generadoEn: '2026-10-14T09:30:00-05:00',
      vigenciaSegundos: 30,
      vehiculos: { total: 50, activos: 45, capacidadKgActiva: 76500 },
      conductores: { total: 200, habilitadosAsignacion: 145, noHabilitados: 55 },
      pedidos: { total: 30000, porEstado: { PENDIENTE: 30000 }, porPrioridad: { EXPRESS: 6000, ESTANDAR: 15000, ECONOMICO: 9000 } },
    })
    expect(fetch).toHaveBeenCalledTimes(1)
    const [url, options] = fetch.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('https://api.example.test/v1/indicadores/operacion')
    expect(options).toEqual({ credentials: 'include' })
  })

  it('ruta feliz: descarta campos no previstos', async () => {
    respond({ ...body, extra: 'x', conductores: { ...body.conductores, dni: '00000000' } })
    const result = await getOperationIndicators()
    expect(JSON.stringify(result)).not.toMatch(/dni|extra/u)
  })

  it.each([[401, 'unauthorized'], [403, 'forbidden'], [503, 'unavailable'], [500, 'unavailable'], [404, 'unexpected']] as const)(
    'ruta infeliz: traduce %s sin exponer el detalle del servidor', async (status, kind) => {
      respond({ detail: 'SQL privado' }, status)
      const error = await getOperationIndicators().catch((reason: unknown) => reason)
      expect(error).toBeInstanceOf(IndicatorsServiceError)
      expect(error).toMatchObject({ kind })
      expect((error as Error).message).not.toContain('privado')
    })

  it('ruta infeliz: fallo de red, JSON inválido o URL base inválida', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
    await expect(getOperationIndicators()).rejects.toMatchObject({ kind: 'network' })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('no-json', { status: 200 })))
    await expect(getOperationIndicators()).rejects.toMatchObject({ kind: 'unexpected' })
    vi.stubEnv('VITE_API_BASE_URL', 'notaurl')
    await expect(getOperationIndicators()).rejects.toMatchObject({ kind: 'unexpected' })
  })

  it.each([
    ['sin secciones', { generado_en: 'x', vigencia_segundos: 30 }],
    ['conteo negativo', { ...body, vehiculos: { ...body.vehiculos, total: -1 } }],
    ['conteo decimal', { ...body, conductores: { ...body.conductores, total: 1.5 } }],
    ['capacidad no numérica', { ...body, vehiculos: { ...body.vehiculos, capacidad_kg_activa: 'abc' } }],
    ['capacidad como número', { ...body, vehiculos: { ...body.vehiculos, capacidad_kg_activa: 10 } }],
    ['por_estado no es objeto', { ...body, pedidos: { ...body.pedidos, por_estado: [1] } }],
    ['cuerpo que no es objeto', [body]],
  ])('ruta de borde: rechaza respuesta con forma inesperada (%s)', async (_name, payload) => {
    respond(payload)
    await expect(getOperationIndicators()).rejects.toMatchObject({ kind: 'unexpected' })
  })

  it('ruta de borde: base vacía con ceros es válida', async () => {
    respond({
      ...body,
      vehiculos: { total: 0, activos: 0, capacidad_kg_activa: '0' },
      conductores: { total: 0, habilitados_asignacion: 0, no_habilitados: 0 },
      pedidos: { total: 0, por_estado: {}, por_prioridad: { EXPRESS: 0, ESTANDAR: 0, ECONOMICO: 0 } },
    })
    expect((await getOperationIndicators()).pedidos.porEstado).toEqual({})
  })
})
