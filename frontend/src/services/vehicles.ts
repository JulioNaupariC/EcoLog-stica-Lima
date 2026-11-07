import { buildApiUrl } from './api'

export type VehicleType = 'CAMIONETA' | 'FURGON' | 'MOTO'

export interface VehicleCreatePayload {
  placa: string
  tipo: VehicleType
  capacidad_kg: string
  capacidad_m3: string
  rendimiento_km_l: string
  factor_co2_kg_km: string
  anio_fabricacion: number
}

export interface VehicleResponse extends VehicleCreatePayload {
  vehiculo_id: string
  estado: string
}

export type VehicleServiceErrorKind =
  | 'unauthorized'
  | 'forbidden'
  | 'conflict'
  | 'validation'
  | 'unavailable'
  | 'network'
  | 'unexpected'

export interface VehicleValidationIssue {
  field: keyof VehicleCreatePayload
  message: string
}

const ERROR_MESSAGES: Record<VehicleServiceErrorKind, string> = {
  unauthorized: 'Tu sesión no está disponible o ha vencido.',
  forbidden: 'No tienes permisos para realizar esta acción.',
  conflict: 'La placa ya está registrada.',
  validation: 'Revisa los datos ingresados.',
  unavailable: 'El servicio no está disponible en este momento.',
  network: 'No se pudo comunicar con el servicio.',
  unexpected: 'No se pudo completar la operación.',
}

const FIELD_MESSAGES: Record<keyof VehicleCreatePayload, string> = {
  placa: 'Revisa la placa.',
  tipo: 'Selecciona un tipo de vehículo válido.',
  capacidad_kg: 'Revisa la capacidad en kg.',
  capacidad_m3: 'Revisa la capacidad en m³.',
  rendimiento_km_l: 'Revisa el rendimiento en km/L.',
  factor_co2_kg_km: 'Revisa el factor CO₂ en kg/km.',
  anio_fabricacion: 'Revisa el año de fabricación.',
}

export class VehicleServiceError extends Error {
  readonly kind: VehicleServiceErrorKind
  readonly status?: number
  readonly issues: VehicleValidationIssue[]

  constructor(
    kind: VehicleServiceErrorKind,
    options: { status?: number; issues?: VehicleValidationIssue[] } = {},
  ) {
    super(ERROR_MESSAGES[kind])
    this.name = 'VehicleServiceError'
    this.kind = kind
    this.status = options.status
    this.issues = options.issues ?? []
  }
}

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/iu
// Decimal JSON can include an exponent (for example "0E-5"). Never coerce to Number.
const DECIMAL_PATTERN = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/iu

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isDecimalString(value: unknown): value is string {
  return typeof value === 'string' && DECIMAL_PATTERN.test(value)
}

function vehicleResponse(body: unknown): VehicleResponse {
  if (
    !isRecord(body) ||
    typeof body.vehiculo_id !== 'string' || !UUID_PATTERN.test(body.vehiculo_id) ||
    typeof body.placa !== 'string' ||
    (body.tipo !== 'CAMIONETA' && body.tipo !== 'FURGON' && body.tipo !== 'MOTO') ||
    !isDecimalString(body.capacidad_kg) ||
    !isDecimalString(body.capacidad_m3) ||
    !isDecimalString(body.rendimiento_km_l) ||
    !isDecimalString(body.factor_co2_kg_km) ||
    typeof body.anio_fabricacion !== 'number' || !Number.isInteger(body.anio_fabricacion) ||
    typeof body.estado !== 'string'
  ) {
    throw new VehicleServiceError('unexpected')
  }
  return {
    vehiculo_id: body.vehiculo_id,
    placa: body.placa,
    tipo: body.tipo,
    capacidad_kg: body.capacidad_kg,
    capacidad_m3: body.capacidad_m3,
    rendimiento_km_l: body.rendimiento_km_l,
    factor_co2_kg_km: body.factor_co2_kg_km,
    anio_fabricacion: body.anio_fabricacion,
    estado: body.estado,
  }
}

function validationIssues(body: unknown): VehicleValidationIssue[] {
  if (!isRecord(body) || !Array.isArray(body.detail)) return []

  const fields = new Set<keyof VehicleCreatePayload>()
  for (const detail of body.detail as unknown[]) {
    if (!isRecord(detail) || !Array.isArray(detail.loc)) continue
    const location: unknown[] = detail.loc
    if (location.length !== 2 || location[0] !== 'body') continue
    const field = location[1]
    if (typeof field === 'string' && Object.hasOwn(FIELD_MESSAGES, field)) {
      fields.add(field as keyof VehicleCreatePayload)
    }
  }
  return [...fields].map((field) => ({ field, message: FIELD_MESSAGES[field] }))
}

function httpError(status: number, body: unknown, method: 'GET' | 'POST'): VehicleServiceError {
  if (status === 401) return new VehicleServiceError('unauthorized', { status })
  if (status === 403) return new VehicleServiceError('forbidden', { status })
  if (status === 503) return new VehicleServiceError('unavailable', { status })
  if (method === 'POST' && status === 409) {
    return new VehicleServiceError('conflict', { status })
  }
  if (method === 'POST' && status === 422) {
    return new VehicleServiceError('validation', { status, issues: validationIssues(body) })
  }
  return new VehicleServiceError('unexpected', { status })
}

// ECL-109: GET /vehiculos is paginated (12 rows by default). Until ECL-111 adds
// the page controls, the list asks for the first 100 vehicles in one page.
export const VEHICLE_LIST_PAGE_SIZE = 100

async function requestVehicles(method: 'GET' | 'POST', body?: string): Promise<unknown> {
  let url: string
  try {
    url = buildApiUrl(method === 'GET' ? `vehiculos?page=1&page_size=${VEHICLE_LIST_PAGE_SIZE}` : 'vehiculos')
  } catch {
    throw new VehicleServiceError('unexpected')
  }

  let response: Response
  try {
    response = await fetch(url, method === 'GET' ? {
      method,
      credentials: 'include',
    } : {
      method,
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body,
    })
  } catch {
    throw new VehicleServiceError('network')
  }

  let result: unknown = null
  try {
    result = await response.json()
  } catch {
    // HTTP errors still have a useful status even when the body is not JSON.
  }
  if (!response.ok) throw httpError(response.status, result, method)
  if (response.status !== (method === 'GET' ? 200 : 201)) {
    throw new VehicleServiceError('unexpected', { status: response.status })
  }
  return result
}

export async function listVehicles(): Promise<VehicleResponse[]> {
  const body = await requestVehicles('GET')
  if (typeof body !== 'object' || body === null || !('items' in body) || !Array.isArray(body.items)) {
    throw new VehicleServiceError('unexpected')
  }
  return (body.items as unknown[]).map(vehicleResponse)
}

export async function createVehicle(payload: VehicleCreatePayload): Promise<VehicleResponse> {
  const body = await requestVehicles('POST', JSON.stringify({
    placa: payload.placa,
    tipo: payload.tipo,
    capacidad_kg: payload.capacidad_kg,
    capacidad_m3: payload.capacidad_m3,
    rendimiento_km_l: payload.rendimiento_km_l,
    factor_co2_kg_km: payload.factor_co2_kg_km,
    anio_fabricacion: payload.anio_fabricacion,
  }))
  return vehicleResponse(body)
}
