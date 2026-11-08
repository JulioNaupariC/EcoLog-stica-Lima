import { buildApiUrl } from './api'
import { validUuid } from '../types/driverReport'
import { isAwareInstant } from '../domain/routeOutcomes'
import type { ClosedRoute, StopOutcome, UpdatedStop } from '../domain/routeOutcomes'

type ErrorKind = 'unauthorized' | 'forbidden' | 'not_found' | 'conflict' | 'invalid' | 'unavailable'
const MESSAGES: Record<ErrorKind, string> = {
  unauthorized: 'Tu sesión ha vencido. Vuelve a iniciar sesión.',
  forbidden: 'Solo el Operador puede registrar resultados y cerrar rutas.',
  not_found: 'La ruta o parada ya no está disponible. Actualiza el plan.',
  conflict: 'El estado de la ruta o parada cambió. Actualiza el plan antes de continuar.',
  invalid: 'Revisa el resultado y la hora real de atención (Lima).',
  unavailable: 'No se pudo confirmar la operación con el servicio. Actualiza el plan antes de reintentar.',
}
export class RouteOutcomeError extends Error {
  constructor(readonly kind: ErrorKind, message = MESSAGES[kind], readonly field?: 'atendida_en') {
    super(message); this.name = 'RouteOutcomeError'
  }
}
export interface RouteOutcomeSource {
  record: (routeId: string, stopId: string, outcome: StopOutcome, signal: AbortSignal) => Promise<UpdatedStop>
  close: (routeId: string, signal: AbortSignal) => Promise<ClosedRoute>
}
function object(value: unknown): Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) throw new RouteOutcomeError('unavailable')
  return value as Record<string, unknown>
}
const CONFLICTS = new Set(['La ruta ya está cerrada', 'La parada ya tiene un resultado final',
  'La ruta no tiene referencia secuencial; vuelve a optimizar la jornada'])
const TIME_ERRORS = new Set(['La hora de atención no puede ser futura', 'La hora de atención es anterior a la jornada de la ruta'])
function httpError(status: number, body: unknown): RouteOutcomeError {
  const detail = body !== null && typeof body === 'object' && 'detail' in body ? body.detail : undefined
  if (status === 409 && typeof detail === 'string' && (CONFLICTS.has(detail) || /^Faltan \d{1,6} paradas por registrar$/u.test(detail))) return new RouteOutcomeError('conflict', detail)
  if (status === 422) {
    const d = detail !== null && typeof detail === 'object' ? detail as Record<string, unknown> : {}
    if (d.campo === 'atendida_en' && typeof d.motivo === 'string' && TIME_ERRORS.has(d.motivo)) return new RouteOutcomeError('invalid', d.motivo, 'atendida_en')
    return new RouteOutcomeError('invalid')
  }
  const kind = status === 401 ? 'unauthorized' : status === 403 ? 'forbidden' : status === 404 ? 'not_found' : status === 409 ? 'conflict' : 'unavailable'
  return new RouteOutcomeError(kind)
}
async function write(path: string, method: 'PATCH' | 'POST', signal: AbortSignal, payload?: StopOutcome): Promise<Record<string, unknown>> {
  let response: Response
  try {
    response = await fetch(buildApiUrl(path), { method, credentials: 'include', cache: 'no-store',
      signal: AbortSignal.any([signal, AbortSignal.timeout(15_000)]),
      ...(payload ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) } : {}) })
  } catch (error) { if (signal.aborted) throw error; throw new RouteOutcomeError('unavailable') }
  let body: unknown
  try { body = await response.json() } catch { if (response.status === 200) throw new RouteOutcomeError('unavailable'); body = null }
  if (response.status !== 200) throw httpError(response.status, body)
  return object(body)
}
const count = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0
export const routeOutcomesApi: RouteOutcomeSource = {
  async record(routeId, stopId, outcome, signal) {
    if (!validUuid(routeId) || !validUuid(stopId) || !['ATENDIDA', 'NO_ATENDIDA'].includes(outcome.estado) ||
      (outcome.estado === 'ATENDIDA' && !isAwareInstant(outcome.atendida_en))) throw new RouteOutcomeError('invalid')
    const payload: StopOutcome = outcome.estado === 'ATENDIDA' ? { estado: outcome.estado, atendida_en: outcome.atendida_en } : { estado: 'NO_ATENDIDA' }
    const result = await write(`rutas/${routeId}/paradas/${stopId}`, 'PATCH', signal, payload)
    if (result.ruta_id !== routeId || result.parada_id !== stopId || result.estado !== outcome.estado || !['EN_CURSO', 'CERRADA'].includes(String(result.ruta_estado))) throw new RouteOutcomeError('unavailable')
    if (outcome.estado === 'ATENDIDA' ? !isAwareInstant(result.atendida_en) || Date.parse(result.atendida_en) !== Date.parse(outcome.atendida_en) : result.atendida_en !== null) throw new RouteOutcomeError('unavailable')
    return { ruta_id: routeId, parada_id: stopId, estado: outcome.estado, atendida_en: result.atendida_en as string | null, ruta_estado: result.ruta_estado as UpdatedStop['ruta_estado'] }
  },
  async close(routeId, signal) {
    if (!validUuid(routeId)) throw new RouteOutcomeError('invalid')
    const result = await write(`rutas/${routeId}/cierre`, 'POST', signal)
    if (result.ruta_id !== routeId || result.estado !== 'CERRADA' || !isAwareInstant(result.cerrada_en) ||
      !count(result.paradas_atendidas) || !count(result.paradas_no_atendidas)) throw new RouteOutcomeError('unavailable')
    return { ruta_id: routeId, estado: 'CERRADA', cerrada_en: result.cerrada_en, paradas_atendidas: result.paradas_atendidas, paradas_no_atendidas: result.paradas_no_atendidas }
  },
}
