import {
  DriverItineraryServiceError,
  driverReportTransport,
  getDriverItinerary,
} from './driverItinerary'
import type { PendingDriverReport } from '../types/driverReport'

const stopId = '223e4567-e89b-42d3-a456-426614174000'
const operationId = '323e4567-e89b-42d3-a456-426614174000'
const ownerId = '123e4567-e89b-42d3-a456-426614174000'
const report: PendingDriverReport = {
  ownerId,
  stopId,
  operationId,
  status: 'ENTREGADO',
  createdAt: 1000,
  attemptCount: 0,
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('servicio de itinerario y reportes del conductor', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/v1')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('valida las asignaciones del usuario desde la respuesta autenticada', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({
      stops: [{ stop_id: stopId, position: 2, status: 'EN_RUTA' }],
    }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(getDriverItinerary()).resolves.toEqual([
      { stopId, position: 2, status: 'EN_RUTA' },
    ])
    expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
      'https://api.example.test/v1/conductor/itinerario',
      { credentials: 'include', cache: 'no-store' },
    )
  })

  it('no admite respuestas con paradas mal formadas', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({
      stops: [{ stop_id: 'not-a-uuid', position: 0, status: 'ENTREGADO' }],
    })))

    await expect(getDriverItinerary()).rejects.toMatchObject({
      name: 'DriverItineraryServiceError',
      retryable: false,
    })
  })

  it('usa cache solo ante errores recuperables de conexión o servidor', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('private network detail')))

    const error = await getDriverItinerary().catch((caught: unknown) => caught)
    expect(error).toBeInstanceOf(DriverItineraryServiceError)
    expect(error).toMatchObject({ retryable: true })
    expect(String(error)).not.toContain('private network detail')

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({}, 403)))
    await expect(getDriverItinerary()).rejects.toMatchObject({ retryable: false })
  })

  it('envía los campos mínimos y exige ACK del mismo operation_id', async () => {
    const fetchMock = vi.fn<
      (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
    >().mockResolvedValue(jsonResponse({
      operation_id: operationId,
      acknowledged: true,
    }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(driverReportTransport.send(report)).resolves.toEqual({
      operationId,
      acknowledged: true,
    })
    expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
      'https://api.example.test/v1/conductor/reportes',
      {
        method: 'POST',
        credentials: 'include',
        cache: 'no-store',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operation_id: operationId,
          stop_id: stopId,
          status: 'ENTREGADO',
        }),
      },
    )
  })

  it('retiene el reporte si el ACK falta o identifica otra operación', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({
      operation_id: ownerId,
      acknowledged: true,
    })))

    await expect(driverReportTransport.send(report)).rejects.toMatchObject({
      retryable: false,
      message: 'La confirmación del servidor es inválida.',
    })
  })

  it('refuses a different cookie owner before caching an itinerary', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ owner_id: stopId, stops: [] })))
    await expect(getDriverItinerary(ownerId)).rejects.toMatchObject({ status: 401, retryable: false })
  })

  it('maps only delivery address/reference/window from an authenticated order', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ owner_id: ownerId, stops: [{
      stop_id: stopId, position: 1, status: 'PENDIENTE', delivery: {
        address: 'Av. Sintetica 1', reference: null,
        window_start: '2026-10-09T10:00:00Z', window_end: '2026-10-09T11:00:00Z',
        cliente_id: 'not exported', telefono: 'not exported',
      },
    }] })))
    await expect(getDriverItinerary(ownerId)).resolves.toEqual([{ stopId, position: 1, status: 'PENDIENTE',
      delivery: { address: 'Av. Sintetica 1', windowStart: '2026-10-09T10:00:00Z', windowEnd: '2026-10-09T11:00:00Z' } }])
  })

  it('rejects invalid delivery times rather than storing them offline', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ stops: [{
      stop_id: stopId, position: 1, status: 'PENDIENTE',
      delivery: { address: 'Av. Sintetica', window_start: 'bad', window_end: 'bad' },
    }] })))
    await expect(getDriverItinerary()).rejects.toMatchObject({ retryable: false })
  })
})
