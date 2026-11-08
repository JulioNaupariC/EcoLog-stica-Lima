import { validOperationDate } from './operationRoutes'

export type StopOutcome = { estado: 'ATENDIDA'; atendida_en: string } | { estado: 'NO_ATENDIDA' }
export interface UpdatedStop {
  ruta_id: string; parada_id: string; estado: 'ATENDIDA' | 'NO_ATENDIDA'
  atendida_en: string | null; ruta_estado: 'EN_CURSO' | 'CERRADA'
}
export interface ClosedRoute {
  ruta_id: string; estado: 'CERRADA'; cerrada_en: string
  paradas_atendidas: number; paradas_no_atendidas: number
}

/** datetime-local has no zone: always display and submit the explicit Lima offset. */
export function limaDateTimeInput(now = Date.now()): string {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima', year: 'numeric', month: '2-digit',
    day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' }).formatToParts(new Date(now))
  const part = (type: string) => parts.find(p => p.type === type)!.value
  return `${part('year')}-${part('month')}-${part('day')}T${part('hour')}:${part('minute')}:${part('second')}`
}

export function attendanceTime(value: string, operationDate: string, now = Date.now()): string {
  if (!/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$/u.test(value) ||
    !validOperationDate(value.slice(0, 10)) || !validOperationDate(operationDate)) throw new Error('Indica una fecha y hora de atención válida (Lima).')
  const timestamp = `${value.length === 16 ? value + ':00' : value}-05:00`
  if (Date.parse(timestamp) < Date.parse(`${operationDate}T00:00:00-05:00`)) throw new Error('La hora de atención es anterior a la jornada de la ruta.')
  if (Date.parse(timestamp) > now) throw new Error('La hora de atención no puede ser futura.')
  return timestamp
}

export function isAwareInstant(value: unknown): value is string {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/u.test(value) &&
    validOperationDate(value.slice(0, 10)) && Number.isFinite(Date.parse(value))
}
