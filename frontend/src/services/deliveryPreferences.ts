import { buildApiUrl } from './api'

export const PREFERENCE_FIELDS = ['horario_preferido', 'referencia', 'restriccion_acceso'] as const
export type PreferenceField = typeof PREFERENCE_FIELDS[number]
export type Preferences = Record<PreferenceField, string | null>
export interface DeliveryPreferences extends Preferences { cliente_id: string }
export type PreferencesPatch = Partial<Preferences>
export type PreferencesErrorKind = 'unauthorized' | 'forbidden' | 'not_found' | 'validation' | 'network' | 'unavailable' | 'unexpected'

const MESSAGES: Record<PreferencesErrorKind, string> = {
  unauthorized: 'Tu sesión ha vencido. Vuelve a iniciar sesión.',
  forbidden: 'No tienes permisos para gestionar las preferencias de entrega.',
  not_found: 'No se encontró el cliente. Revisa su identificador.',
  validation: 'Revisa los campos indicados antes de guardar.',
  network: 'No se pudo comunicar con el servicio. Revisa tu conexión.',
  unavailable: 'El servicio no está disponible. Intenta nuevamente más tarde.',
  unexpected: 'No se pudo completar la operación. Intenta nuevamente.',
}
export class PreferencesServiceError extends Error {
  constructor(readonly kind: PreferencesErrorKind, readonly fields: PreferenceField[] = []) {
    super(MESSAGES[kind])
    this.name = 'PreferencesServiceError'
  }
}
export function isClientId(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/iu.test(value)
}
function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
function validationFields(body: unknown): PreferenceField[] {
  if (!record(body) || !Array.isArray(body.detail)) return []
  const result = new Set<PreferenceField>()
  for (const issue of body.detail as unknown[]) {
    if (!record(issue) || !Array.isArray(issue.loc) || issue.loc[0] !== 'body') continue
    for (const field of PREFERENCE_FIELDS) if (issue.loc[1] === field) result.add(field)
  }
  return [...result]
}
async function request(method: 'GET' | 'PATCH', id: string, patch?: PreferencesPatch): Promise<DeliveryPreferences> {
  if (!isClientId(id)) throw new PreferencesServiceError('unexpected')
  let url: string
  try { url = buildApiUrl(`clientes/${id}/preferencias`) } catch { throw new PreferencesServiceError('unexpected') }
  let response: Response
  try {
    response = await fetch(url, {
      method, credentials: 'include', cache: 'no-store',
      ...(patch ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(patch) } : {}),
    })
  } catch { throw new PreferencesServiceError('network') }
  let body: unknown = null
  try { body = await response.json() } catch { /* Use status and safe messages. */ }
  if (!response.ok) {
    const kind: PreferencesErrorKind = response.status === 401 ? 'unauthorized' : response.status === 403 ? 'forbidden' :
      response.status === 404 ? 'not_found' : response.status === 422 ? 'validation' :
        response.status >= 500 ? 'unavailable' : 'unexpected'
    throw new PreferencesServiceError(kind, kind === 'validation' ? validationFields(body) : [])
  }
  if (response.status !== 200 || !record(body) || typeof body.cliente_id !== 'string' ||
    body.cliente_id.toLowerCase() !== id.toLowerCase() ||
    PREFERENCE_FIELDS.some(field => body[field] !== null && typeof body[field] !== 'string')) {
    throw new PreferencesServiceError('unexpected')
  }
  return { cliente_id: body.cliente_id, horario_preferido: body.horario_preferido as string | null,
    referencia: body.referencia as string | null, restriccion_acceso: body.restriccion_acceso as string | null }
}
export function getDeliveryPreferences(id: string): Promise<DeliveryPreferences> {
  return request('GET', id)
}
export function updateDeliveryPreferences(id: string, changes: PreferencesPatch): Promise<DeliveryPreferences> {
  const patch: PreferencesPatch = {}
  for (const field of PREFERENCE_FIELDS) {
    if (Object.hasOwn(changes, field) && changes[field] !== undefined) patch[field] = changes[field]
  }
  if (Object.keys(patch).length === 0) return Promise.reject(new PreferencesServiceError('validation'))
  return request('PATCH', id, patch)
}
