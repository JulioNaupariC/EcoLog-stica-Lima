import { buildApiUrl } from './api'
import type { ReportTransport } from './reportSync'
import type { StopSummary } from './offlineStorage'
import { isDeliveryDetails } from './offlineStorage'

export class DriverItineraryServiceError extends Error {
  constructor(
    message: string,
    readonly retryable: boolean,
    readonly status?: number,
  ) {
    super(message)
    this.name = 'DriverItineraryServiceError'
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function validUuid(value: unknown): value is string {
  return typeof value === 'string' &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/iu.test(value)
}

const STOP_STATES = new Set(['PENDIENTE', 'EN_RUTA', 'ENTREGADO', 'NO_ENTREGADO'])

function isStopStatus(value: unknown): value is StopSummary['status'] {
  return typeof value === 'string' && STOP_STATES.has(value)
}

async function requestJson(url: string, init?: RequestInit): Promise<unknown> {
  let response: Response
  try {
    response = await fetch(url, { ...init, credentials: 'include', cache: 'no-store' })
  } catch {
    throw new DriverItineraryServiceError('No se pudo conectar con el servicio.', true)
  }
  if (!response.ok) {
    throw new DriverItineraryServiceError(
      response.status === 401 || response.status === 403
        ? 'La sesión ya no permite consultar el itinerario.'
        : 'El servicio de itinerario no está disponible.',
      response.status >= 500,
      response.status,
    )
  }
  try {
    return await response.json()
  } catch {
    throw new DriverItineraryServiceError('El servicio devolvió una respuesta inválida.', false)
  }
}

export async function getDriverItinerary(expectedOwnerId?: string): Promise<StopSummary[]> {
  let url: string
  try {
    url = buildApiUrl('conductor/itinerario')
  } catch {
    throw new DriverItineraryServiceError('No se pudo configurar el servicio.', false)
  }
  const body = await requestJson(url)
  if (!isRecord(body) || !Array.isArray(body.stops)) {
    throw new DriverItineraryServiceError('El servicio devolvió un itinerario inválido.', false)
  }
  if (expectedOwnerId && body.owner_id !== expectedOwnerId) {
    throw new DriverItineraryServiceError('La sesión cambió. Vuelve a iniciar sesión.', false, 401)
  }
  return body.stops.map((item): StopSummary => {
    if (
      !isRecord(item) ||
      !validUuid(item.stop_id) ||
      !Number.isSafeInteger(item.position) ||
      Number(item.position) < 1 ||
      !isStopStatus(item.status)
    ) {
      throw new DriverItineraryServiceError('El servicio devolvió una parada inválida.', false)
    }
    const delivery = isRecord(item.delivery) ? {
      address: item.delivery.address,
      ...(item.delivery.reference === null ? {} : { reference: item.delivery.reference }),
      windowStart: item.delivery.window_start,
      windowEnd: item.delivery.window_end,
    } : undefined
    if (delivery !== undefined && !isDeliveryDetails(delivery)) {
      throw new DriverItineraryServiceError('El servicio devolvió datos de entrega inválidos.', false)
    }
    return {
      stopId: item.stop_id,
      position: Number(item.position),
      status: item.status,
      ...(isDeliveryDetails(delivery) ? { delivery } : {}),
    }
  })
}

export const driverReportTransport: ReportTransport = {
  async send(report) {
    let url: string
    try {
      url = buildApiUrl('conductor/reportes')
    } catch {
      throw new DriverItineraryServiceError('No se pudo configurar el servicio.', false)
    }
    const body = await requestJson(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        operation_id: report.operationId,
        stop_id: report.stopId,
        status: report.status,
      }),
    })
    if (
      !isRecord(body) ||
      body.acknowledged !== true ||
      body.operation_id !== report.operationId
    ) {
      throw new DriverItineraryServiceError('La confirmación del servidor es inválida.', false)
    }
    return { operationId: report.operationId, acknowledged: true }
  },
}
