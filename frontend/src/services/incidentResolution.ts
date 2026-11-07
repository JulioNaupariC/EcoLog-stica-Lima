import { buildApiUrl } from './api'
import { validUuid } from '../types/driverReport'

export type IncidentAction = 'VALIDAR' | 'DESCARTAR'
type ErrorKind = 'unauthorized' | 'forbidden' | 'conflict' | 'unavailable' | 'invalid'
const messages: Record<ErrorKind, string> = {
  unauthorized: 'Tu sesión ha vencido. Vuelve a iniciar sesión.',
  forbidden: 'Solo Administrador y Operador pueden resolver incidencias.',
  conflict: 'Otra persona ya resolvió esta incidencia. Se actualizó el listado.',
  unavailable: 'No se pudo confirmar la resolución. Actualiza el listado antes de reintentar.',
  invalid: 'Revisa la acción y el motivo (máximo 300 caracteres).',
}
export class IncidentResolutionError extends Error {
  constructor(readonly kind: ErrorKind) { super(messages[kind]); this.name = 'IncidentResolutionError' }
}

export interface ResolvedIncident {
  incidencia_id: string
  estado: 'VALIDADA' | 'DESCARTADA'
  resuelta_por: string
  resuelta_en: string
}

export async function resolveIncident(id: string, accion: IncidentAction, motivo: string): Promise<ResolvedIncident> {
  if (!validUuid(id) || !['VALIDAR', 'DESCARTAR'].includes(accion) || [...motivo].length > 300) {
    throw new IncidentResolutionError('invalid')
  }
  let response: Response
  try {
    response = await fetch(buildApiUrl(`incidencias/${id}`), {
      method: 'PATCH', credentials: 'include', cache: 'no-store',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ accion, motivo }), signal: AbortSignal.timeout(15_000),
    })
  } catch { throw new IncidentResolutionError('unavailable') }
  if (response.status !== 200) throw new IncidentResolutionError(
    response.status === 401 ? 'unauthorized' : response.status === 403 ? 'forbidden'
      : response.status === 409 ? 'conflict' : response.status === 422 ? 'invalid' : 'unavailable')
  let body: unknown
  try { body = await response.json() } catch { throw new IncidentResolutionError('unavailable') }
  if (!body || typeof body !== 'object' || !('incidencia_id' in body) || body.incidencia_id !== id ||
    !('estado' in body) || body.estado !== (accion === 'VALIDAR' ? 'VALIDADA' : 'DESCARTADA') ||
    !('resuelta_por' in body) || !validUuid(body.resuelta_por) ||
    !('resuelta_en' in body) || typeof body.resuelta_en !== 'string' ||
    !/(?:Z|[+-]\d{2}:\d{2})$/u.test(body.resuelta_en) || !Number.isFinite(Date.parse(body.resuelta_en))) {
    throw new IncidentResolutionError('unavailable')
  }
  return { incidencia_id: id, estado: accion === 'VALIDAR' ? 'VALIDADA' : 'DESCARTADA',
    resuelta_por: body.resuelta_por, resuelta_en: body.resuelta_en }
}
