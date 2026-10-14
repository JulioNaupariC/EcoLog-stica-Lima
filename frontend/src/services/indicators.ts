import { buildApiUrl } from './api'

/** Aggregates computed by the API (GET /indicadores/operacion); no personal data. */
export interface OperationIndicators {
  generadoEn: string
  vigenciaSegundos: number
  vehiculos: { total: number, activos: number, capacidadKgActiva: number }
  conductores: { total: number, habilitadosAsignacion: number, noHabilitados: number }
  pedidos: { total: number, porEstado: Record<string, number>, porPrioridad: Record<string, number> }
}

export type IndicatorsErrorKind = 'unauthorized' | 'forbidden' | 'network' | 'unavailable' | 'unexpected'

const MESSAGES: Record<IndicatorsErrorKind, string> = {
  unauthorized: 'Tu sesión ha vencido. Vuelve a iniciar sesión.',
  forbidden: 'No tienes permisos para consultar los indicadores.',
  network: 'No se pudo comunicar con el servicio. Revisa tu conexión.',
  unavailable: 'El servicio no está disponible. Intenta nuevamente más tarde.',
  unexpected: 'No se pudieron cargar los indicadores.',
}

export class IndicatorsServiceError extends Error {
  constructor(readonly kind: IndicatorsErrorKind) {
    super(MESSAGES[kind])
    this.name = 'IndicatorsServiceError'
  }
}

type JsonRecord = Record<string, unknown>

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function count(value: unknown): number {
  if (typeof value !== 'number' || !Number.isInteger(value) || value < 0) throw new IndicatorsServiceError('unexpected')
  return value
}

function section(body: JsonRecord, key: string): JsonRecord {
  const value = body[key]
  if (!isRecord(value)) throw new IndicatorsServiceError('unexpected')
  return value
}

function counts(value: unknown): Record<string, number> {
  if (!isRecord(value)) throw new IndicatorsServiceError('unexpected')
  return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, count(item)]))
}

function kindFor(status: number): IndicatorsErrorKind {
  if (status === 401) return 'unauthorized'
  if (status === 403) return 'forbidden'
  if (status >= 500) return 'unavailable'
  return 'unexpected'
}

function parse(body: unknown): OperationIndicators {
  if (!isRecord(body) || typeof body.generado_en !== 'string') throw new IndicatorsServiceError('unexpected')
  const vehicles = section(body, 'vehiculos')
  const drivers = section(body, 'conductores')
  const orders = section(body, 'pedidos')
  const capacity = Number(vehicles.capacidad_kg_activa)
  if (typeof vehicles.capacidad_kg_activa !== 'string' || !Number.isFinite(capacity) || capacity < 0) {
    throw new IndicatorsServiceError('unexpected')
  }
  return {
    generadoEn: body.generado_en,
    vigenciaSegundos: count(body.vigencia_segundos),
    vehiculos: { total: count(vehicles.total), activos: count(vehicles.activos), capacidadKgActiva: capacity },
    conductores: {
      total: count(drivers.total),
      habilitadosAsignacion: count(drivers.habilitados_asignacion),
      noHabilitados: count(drivers.no_habilitados),
    },
    pedidos: { total: count(orders.total), porEstado: counts(orders.por_estado), porPrioridad: counts(orders.por_prioridad) },
  }
}

/** One request for the whole home summary; the browser may reuse it for 30 s (private cache). */
export async function getOperationIndicators(): Promise<OperationIndicators> {
  let url: string
  try { url = buildApiUrl('indicadores/operacion') } catch { throw new IndicatorsServiceError('unexpected') }
  let response: Response
  try {
    response = await fetch(url, { credentials: 'include' })
  } catch {
    throw new IndicatorsServiceError('network')
  }
  if (!response.ok) throw new IndicatorsServiceError(kindFor(response.status))
  let body: unknown
  try { body = await response.json() } catch { throw new IndicatorsServiceError('unexpected') }
  return parse(body)
}
