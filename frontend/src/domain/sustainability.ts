import { validOperationDate } from './operationRoutes'

export interface Period { desde: string; hasta: string }
export const METRICS = [
  { key: 'distancia_km', label: 'Distancia', unit: 'km' },
  { key: 'co2_kg', label: 'Emisiones de CO₂', unit: 'kg CO₂' },
  { key: 'combustible_l', label: 'Combustible', unit: 'L' },
  { key: 'costo_soles', label: 'Costo', unit: 'S/' },
] as const
export type MetricKey = typeof METRICS[number]['key']
export type Metrics = Record<MetricKey, number>
export interface Sustainability {
  periodo: Period
  con_datos: boolean
  rutas_cerradas: number
  metricas: Metrics | null
  ahorro: (Metrics & { pct: number | null }) | null
  cumplimiento_ventanas_pct: number | null
  parametros_versiones: string[]
  simulado: boolean
}

export class InvalidSustainability extends Error {
  constructor() { super('La respuesta de indicadores está incompleta o no corresponde al periodo. Intenta nuevamente.'); this.name = 'InvalidSustainability' }
}
function ensure(value: unknown): asserts value { if (!value) throw new InvalidSustainability() }
function object(value: unknown): Record<string, unknown> {
  ensure(value !== null && typeof value === 'object' && !Array.isArray(value)); return value as Record<string, unknown>
}
function number(value: unknown): number { ensure(typeof value === 'number' && Number.isFinite(value)); return value }
function metrics(value: Record<string, unknown>, nonnegative: boolean): Metrics {
  return Object.fromEntries(METRICS.map(({ key }) => {
    const n = number(value[key]); ensure(!nonnegative || n >= 0); return [key, n]
  })) as Metrics
}
export function validPeriod(period: Period): boolean {
  return validOperationDate(period.desde) && validOperationDate(period.hasta) && period.desde <= period.hasta
}

/** Validate only published aggregates; never transport route geometry or personal data. */
export function parseSustainability(raw: unknown, requested: Period): Sustainability {
  const body = object(raw), period = object(body.periodo)
  ensure(validPeriod(requested) && period.desde === requested.desde && period.hasta === requested.hasta)
  ensure(typeof body.con_datos === 'boolean' && typeof body.simulado === 'boolean')
  const routes = number(body.rutas_cerradas)
  ensure(Number.isSafeInteger(routes) && routes >= 0)
  ensure(Array.isArray(body.parametros_versiones) && body.parametros_versiones.every(v => typeof v === 'string' && v.trim()))
  const versions = [...new Set(body.parametros_versiones as string[])]
  let totals: Metrics | null = null, savings: Sustainability['ahorro'] = null, compliance: number | null = null
  if (body.con_datos) {
    ensure(routes > 0 && versions.length > 0)
    totals = metrics(body, true)
    const saved = object(body.ahorro_vs_secuencial), values = metrics(saved, false)
    const pct = saved.pct === null ? null : number(saved.pct)
    ensure(pct === null || pct <= 100)
    // A negative saving is a valid increase; an impossible negative baseline is not.
    ensure(METRICS.every(({ key }) => Number.isFinite(totals![key] + values[key]) && totals![key] + values[key] >= 0))
    savings = { ...values, pct }
    compliance = body.cumplimiento_ventanas_pct === null ? null : number(body.cumplimiento_ventanas_pct)
    ensure(compliance === null || (compliance >= 0 && compliance <= 100))
  } else {
    ensure(routes === 0 && versions.length === 0 && METRICS.every(({ key }) => body[key] === null))
    ensure(body.ahorro_vs_secuencial === null && body.cumplimiento_ventanas_pct === null)
  }
  return { periodo: { ...requested }, con_datos: body.con_datos, rutas_cerradas: routes, metricas: totals,
    ahorro: savings, cumplimiento_ventanas_pct: compliance, parametros_versiones: versions, simulado: body.simulado }
}
