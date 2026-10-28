import { INCIDENT_SEVERITIES, INCIDENT_TYPES, validLocation } from '../domain/incident'
import { validUuid } from '../types/driverReport'
import { buildApiUrl } from './api'

export interface PendingIncident {
  incidencia_id: string
  tipo: keyof typeof INCIDENT_TYPES
  severidad: keyof typeof INCIDENT_SEVERITIES
  ocurrida_en: string
  registrada_en: string
  conductor: { conductor_id: string; nombre: string }
  latitud: number
  longitud: number
  observacion: string
  estado: 'PENDIENTE_VALIDACION'
}

export interface IncidentPage {
  items: PendingIncident[]
  page: number
  page_size: number
  total: number
}

type ErrorKind = 'unauthorized' | 'forbidden' | 'network' | 'unavailable' | 'unexpected'
const MESSAGES: Record<ErrorKind, string> = {
  unauthorized: 'Tu sesión ha vencido. Vuelve a iniciar sesión.',
  forbidden: 'Solo Administrador y Operador pueden consultar las incidencias pendientes.',
  network: 'No se pudo conectar con el servicio. Revisa tu conexión e intenta de nuevo.',
  unavailable: 'El servicio no está disponible en este momento. Intenta de nuevo en unos minutos.',
  unexpected: 'No se pudo cargar el listado. Intenta de nuevo.',
}

export class IncidentListError extends Error {
  constructor(readonly kind: ErrorKind) {
    super(MESSAGES[kind])
    this.name = 'IncidentListError'
  }
}

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function zonedDate(value: unknown): value is string {
  return typeof value === 'string' && /(?:Z|[+-]\d{2}:\d{2})$/u.test(value) && Number.isFinite(Date.parse(value))
}

/** Project only the approved list fields; never retain extra driver information. */
function incident(value: unknown): PendingIncident {
  if (!record(value) || !validUuid(value.incidencia_id) ||
    typeof value.tipo !== 'string' || !Object.hasOwn(INCIDENT_TYPES, value.tipo) ||
    typeof value.severidad !== 'string' || !Object.hasOwn(INCIDENT_SEVERITIES, value.severidad) ||
    !zonedDate(value.ocurrida_en) || !zonedDate(value.registrada_en) ||
    !record(value.conductor) || !validUuid(value.conductor.conductor_id) ||
    typeof value.conductor.nombre !== 'string' || !value.conductor.nombre.trim() ||
    typeof value.latitud !== 'number' || typeof value.longitud !== 'number' ||
    !validLocation({ latitud: value.latitud, longitud: value.longitud }) ||
    typeof value.observacion !== 'string' || [...value.observacion].length > 500 ||
    value.estado !== 'PENDIENTE_VALIDACION') throw new IncidentListError('unexpected')
  return {
    incidencia_id: value.incidencia_id,
    tipo: value.tipo as PendingIncident['tipo'], severidad: value.severidad as PendingIncident['severidad'],
    ocurrida_en: value.ocurrida_en, registrada_en: value.registrada_en,
    conductor: { conductor_id: value.conductor.conductor_id, nombre: value.conductor.nombre },
    latitud: value.latitud, longitud: value.longitud, observacion: value.observacion, estado: value.estado,
  }
}

/** ECL-73 / RN-022: server pagination, newest occurrence first, ID ascending on ties. */
export async function listPendingIncidents(page = 1, pageSize = 20, signal?: AbortSignal): Promise<IncidentPage> {
  if (!Number.isInteger(page) || page < 1 || !Number.isInteger(pageSize) || pageSize < 1 || pageSize > 100) {
    throw new IncidentListError('unexpected')
  }
  let url: string
  try {
    url = buildApiUrl(`incidencias?estado=PENDIENTE_VALIDACION&page=${page}&page_size=${pageSize}`)
  } catch { throw new IncidentListError('unexpected') }
  let response: Response
  try {
    const timeout = AbortSignal.timeout(15_000)
    response = await fetch(url, {
      credentials: 'include', cache: 'no-store', signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    })
  } catch (error) {
    if (signal?.aborted) throw error
    throw new IncidentListError('network')
  }
  if (!response.ok) {
    throw new IncidentListError(response.status === 401 ? 'unauthorized'
      : response.status === 403 ? 'forbidden' : response.status >= 500 ? 'unavailable' : 'unexpected')
  }
  if (response.status !== 200) throw new IncidentListError('unexpected')
  let body: unknown
  try { body = await response.json() } catch { throw new IncidentListError('unexpected') }
  if (!record(body) || body.page !== page || body.page_size !== pageSize ||
    typeof body.total !== 'number' || !Number.isSafeInteger(body.total) || body.total < 0 ||
    !Array.isArray(body.items) || body.items.length > pageSize || body.items.length > body.total) {
    throw new IncidentListError('unexpected')
  }
  const items = body.items.map(incident).sort((a, b) =>
    Date.parse(b.ocurrida_en) - Date.parse(a.ocurrida_en) || a.incidencia_id.localeCompare(b.incidencia_id))
  return { items, page, page_size: pageSize, total: body.total }
}
