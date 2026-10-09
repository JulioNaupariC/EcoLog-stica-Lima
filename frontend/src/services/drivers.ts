import { buildApiUrl } from './api'

export interface DriverProfile {
  nombre: string
  dni: string
  licencia_numero: string
  licencia_vigente_hasta: string
  experiencia_anios: number
  telefono: string
  punto_partida: string
  disponible_desde: string | null
  disponible_hasta: string | null
}
export interface DriverCreate extends DriverProfile { email: string; password: string }
export interface DriverListItem {
  conductor_id: string
  nombre: string
  disponible_desde: string | null
  disponible_hasta: string | null
  estado: 'ACTIVO' | 'INACTIVO'
  habilitado_asignacion: boolean
}
export interface DriverSummary extends DriverListItem { usuario_id: string }
export interface DriverDetail extends DriverSummary, DriverProfile {}
export interface DriverPage { items: DriverListItem[]; page: number; page_size: number; total: number }
export type DriverField = keyof DriverCreate
type ErrorKind = 'unauthorized' | 'forbidden' | 'conflict' | 'validation' | 'not_found' | 'network' | 'unavailable' | 'unexpected'

const MESSAGES: Record<ErrorKind, string> = {
  unauthorized: 'Tu sesión ha vencido. Vuelve a iniciar sesión.',
  forbidden: 'No tienes permisos para gestionar conductores.',
  conflict: 'El DNI o el correo ya están registrados. Revisa los datos.',
  validation: 'Revisa los campos indicados y la disponibilidad.',
  not_found: 'El conductor ya no está disponible. Actualiza el listado.',
  network: 'No se pudo comunicar con el servicio.',
  unavailable: 'El servicio no está disponible. Intenta nuevamente más tarde.',
  unexpected: 'No se pudo completar la operación.',
}
export class DriverServiceError extends Error {
  constructor(readonly kind: ErrorKind, readonly fields: DriverField[] = []) {
    super(MESSAGES[kind]); this.name = 'DriverServiceError'
  }
}
const PROFILE_FIELDS = ['nombre', 'dni', 'licencia_numero', 'licencia_vigente_hasta', 'experiencia_anios', 'telefono', 'punto_partida', 'disponible_desde', 'disponible_hasta'] as const
const CREATE_FIELDS = [...PROFILE_FIELDS, 'email', 'password'] as const
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/iu
function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
function identifier(value: unknown): value is string { return typeof value === 'string' && UUID.test(value) }
function timestamp(value: unknown): value is string | null {
  return value === null || (typeof value === 'string' && /(?:Z|[+-]\d{2}:\d{2})$/u.test(value) && Number.isFinite(Date.parse(value)))
}
function listItem(value: unknown): DriverListItem {
  if (!record(value) || !identifier(value.conductor_id) || typeof value.nombre !== 'string' ||
    !timestamp(value.disponible_desde) || !timestamp(value.disponible_hasta) ||
    (value.estado !== 'ACTIVO' && value.estado !== 'INACTIVO') || typeof value.habilitado_asignacion !== 'boolean') {
    throw new DriverServiceError('unexpected')
  }
  return { conductor_id: value.conductor_id, nombre: value.nombre, disponible_desde: value.disponible_desde,
    disponible_hasta: value.disponible_hasta, estado: value.estado, habilitado_asignacion: value.habilitado_asignacion }
}
function summary(value: unknown): DriverSummary {
  const item = listItem(value)
  if (!record(value) || !identifier(value.usuario_id)) throw new DriverServiceError('unexpected')
  return { ...item, usuario_id: value.usuario_id }
}
function detail(value: unknown): DriverDetail {
  const item = summary(value)
  if (!record(value) || typeof value.dni !== 'string' || typeof value.licencia_numero !== 'string' ||
    typeof value.licencia_vigente_hasta !== 'string' || !/^\d{4}-\d{2}-\d{2}$/u.test(value.licencia_vigente_hasta) ||
    typeof value.experiencia_anios !== 'number' || !Number.isInteger(value.experiencia_anios) ||
    typeof value.telefono !== 'string' || typeof value.punto_partida !== 'string') throw new DriverServiceError('unexpected')
  return { ...item, dni: value.dni, licencia_numero: value.licencia_numero, licencia_vigente_hasta: value.licencia_vigente_hasta,
    experiencia_anios: value.experiencia_anios, telefono: value.telefono, punto_partida: value.punto_partida }
}
function validationFields(body: unknown): DriverField[] {
  if (!record(body) || !Array.isArray(body.detail)) return []
  const fields = new Set<DriverField>()
  for (const issue of body.detail as unknown[]) {
    if (!record(issue) || !Array.isArray(issue.loc)) continue
    const loc: unknown[] = issue.loc
    if (loc[0] === 'body' && typeof loc[1] === 'string' && CREATE_FIELDS.some(field => field === loc[1])) {
      fields.add(loc[1] as DriverField)
    }
  }
  return [...fields]
}
async function request(method: 'GET' | 'POST' | 'PATCH', path: string, payload?: object): Promise<unknown> {
  let response: Response
  let url: string
  try { url = buildApiUrl(path) } catch { throw new DriverServiceError('unexpected') }
  try {
    response = await fetch(url, { method, credentials: 'include',
      ...(payload ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) } : {}) })
  } catch { throw new DriverServiceError('network') }
  let body: unknown = null
  try { body = await response.json() } catch { /* Status still determines the safe message. */ }
  if (!response.ok) {
    const kind: ErrorKind = response.status === 401 ? 'unauthorized' : response.status === 403 ? 'forbidden' :
      response.status === 404 ? 'not_found' : response.status === 409 ? 'conflict' :
        response.status === 422 ? 'validation' : response.status >= 500 ? 'unavailable' : 'unexpected'
    throw new DriverServiceError(kind, kind === 'validation' ? validationFields(body) : [])
  }
  if (response.status !== (method === 'POST' ? 201 : 200)) throw new DriverServiceError('unexpected')
  return body
}
function checkedId(id: string): string {
  if (!identifier(id)) throw new DriverServiceError('unexpected')
  return id
}
export async function listDrivers(page = 1): Promise<DriverPage> {
  if (!Number.isInteger(page) || page < 1) throw new DriverServiceError('unexpected')
  const body = await request('GET', 'conductores?page=' + page + '&page_size=10')
  if (!record(body) || body.page !== page || body.page_size !== 10 || typeof body.total !== 'number' ||
    !Number.isInteger(body.total) || body.total < 0 || !Array.isArray(body.items) || body.items.length > 10) {
    throw new DriverServiceError('unexpected')
  }
  return { items: (body.items as unknown[]).map(listItem), page, page_size: 10, total: body.total }
}
export async function getDriver(id: string): Promise<DriverDetail> {
  return detail(await request('GET', 'conductores/' + checkedId(id)))
}
export async function createDriver(payload: DriverCreate): Promise<DriverSummary> {
  const body = Object.fromEntries(CREATE_FIELDS.map(field => [field, payload[field]]))
  return summary(await request('POST', 'conductores', body))
}
export async function updateDriver(id: string, payload: Partial<DriverProfile>): Promise<DriverDetail> {
  const body = Object.fromEntries(PROFILE_FIELDS.filter(field => Object.hasOwn(payload, field)).map(field => [field, payload[field]]))
  return detail(await request('PATCH', 'conductores/' + checkedId(id), body))
}
