import { validUuid } from '../types/driverReport'

export type OptimizationState = 'EN_PROCESO' | 'COMPLETADA' | 'FALLIDA'
export interface OptimizationSummary {
  optimizacion_id: string
  estado: OptimizationState
  fecha_operacion: string
  solicitada_en: string
}
export interface OptimizationPage {
  items: OptimizationSummary[]; page: number; page_size: number; total: number; simulado: boolean
}
export interface RouteStop {
  parada_id: string; pedido_id: string; secuencia: number
  latitud: number; longitud: number
  ventana_inicio: string; ventana_fin: string; eta: string
  estado: 'PENDIENTE' | 'ATENDIDA' | 'NO_ATENDIDA'
}
export interface OperationRoute {
  ruta_id: string
  vehiculo: { placa: string }
  conductor: { nombre: string } | null
  estado: 'PLANIFICADA' | 'EN_CURSO' | 'CERRADA'
  salida: string; regreso: string; tiempo_min: number
  metricas: { distancia_km: number; co2_kg: number; combustible_l: number; costo_soles: number }
  trazado: { type: 'LineString'; coordinates: [number, number][] }
  paradas: RouteStop[]
}
export const UNASSIGNED_REASONS = {
  EXCEDE_CAPACIDAD: 'Excede la capacidad disponible', VENTANA_INVIABLE: 'Ventana de entrega inviable',
  SIN_UBICACION: 'Sin ubicación válida', SIN_VEHICULO: 'Sin vehículo utilizable',
}

/** Internal presentation port. ST-045 does not yet publish traffic/alert fields. */
export interface RouteAlert {
  id: string; rutaId: string; paradaId?: string; tipo: string; texto: string
  severidad: 'BAJA' | 'MEDIA' | 'ALTA'; fuente: string; hora: string; alcance: string; bloqueo: boolean
}
export interface TrafficSnapshot {
  estado: 'DISPONIBLE' | 'DEGRADADO' | 'SIN_DATOS'
  fuente: string | null; actualizado_en: string | null
  tramos: { rutaId: string; origen: string; destino: string; tiempo_min: number }[]
}
export interface OptimizationDetail extends OptimizationSummary {
  simulado: boolean; finalizada_en: string | null
  rutas: OperationRoute[]
  no_asignados: { pedido_id: string; motivo: keyof typeof UNASSIGNED_REASONS }[]
  trafico: TrafficSnapshot
  alertas: RouteAlert[]
  alertasDisponibles: boolean
}

export class InvalidRouteData extends Error {
  constructor() { super('Los datos de rutas son incoherentes. No se puede representar el recorrido.'); this.name = 'InvalidRouteData' }
}
function ensure(value: unknown): asserts value { if (!value) throw new InvalidRouteData() }
function object(value: unknown): Record<string, unknown> {
  ensure(value !== null && typeof value === 'object' && !Array.isArray(value)); return value as Record<string, unknown>
}
function array(value: unknown): unknown[] { ensure(Array.isArray(value)); return value }
function text(value: unknown): string { ensure(typeof value === 'string' && value.trim()); return value }
function id(value: unknown): string { ensure(validUuid(value)); return value }
function nonnegative(value: unknown): number { ensure(typeof value === 'number' && Number.isFinite(value) && value >= 0); return value }
function integer(value: unknown, min = 0): number { const n = nonnegative(value); ensure(Number.isSafeInteger(n) && n >= min); return n }
function boolean(value: unknown): boolean { ensure(typeof value === 'boolean'); return value }
function choice<const T extends string>(value: unknown, values: readonly T[]): T {
  ensure(typeof value === 'string' && values.includes(value as T)); return value as T
}
export function validOperationDate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/u.test(value) && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value
}
function date(value: unknown): string { const d = text(value); ensure(validOperationDate(d)); return d }
function instant(value: unknown): string {
  const t = text(value)
  ensure(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?-05:00$/u.test(t) && validOperationDate(t.slice(0, 10)) && Number.isFinite(Date.parse(t)))
  return t
}
function coordinate(value: unknown, limit: number): number {
  ensure(typeof value === 'number' && Number.isFinite(value) && Math.abs(value) <= limit); return value
}
function unique(values: string[]) { ensure(new Set(values).size === values.length) }
function summary(value: unknown): OptimizationSummary {
  const v = object(value)
  return { optimizacion_id: id(v.optimizacion_id), estado: choice(v.estado, ['EN_PROCESO', 'COMPLETADA', 'FALLIDA']),
    fecha_operacion: date(v.fecha_operacion), solicitada_en: instant(v.solicitada_en) }
}
export function parseOptimizationPage(value: unknown): OptimizationPage {
  const v = object(value), items = array(v.items).map(summary)
  const page_size = integer(v.page_size, 1), total = integer(v.total)
  ensure(page_size <= 100 && items.length <= page_size && items.length <= total)
  unique(items.map(item => item.optimizacion_id))
  return { items, page: integer(v.page, 1), page_size, total, simulado: boolean(v.simulado) }
}
function stop(value: unknown, index: number): RouteStop {
  const s = object(value)
  ensure(integer(s.secuencia, 1) === index + 1)
  const ventana_inicio = instant(s.ventana_inicio), ventana_fin = instant(s.ventana_fin)
  ensure(Date.parse(ventana_inicio) < Date.parse(ventana_fin))
  return { parada_id: id(s.parada_id), pedido_id: id(s.pedido_id), secuencia: index + 1,
    latitud: coordinate(s.latitud, 90), longitud: coordinate(s.longitud, 180), ventana_inicio, ventana_fin,
    eta: instant(s.eta), estado: choice(s.estado, ['PENDIENTE', 'ATENDIDA', 'NO_ATENDIDA']) }
}
function route(value: unknown): OperationRoute {
  const r = object(value), geometry = object(r.trazado), m = object(r.metricas)
  ensure(geometry.type === 'LineString')
  const coordinates = array(geometry.coordinates).map((point): [number, number] => {
    const p = array(point); ensure(p.length === 2); return [coordinate(p[0], 180), coordinate(p[1], 90)]
  })
  ensure(coordinates.length >= 2)
  const paradas = array(r.paradas).map(stop)
  ensure(paradas.length > 0); unique(paradas.map(s => s.parada_id)); unique(paradas.map(s => s.pedido_id))
  const salida = instant(r.salida), regreso = instant(r.regreso)
  ensure(Date.parse(salida) <= Date.parse(regreso))
  const conductor = r.conductor === null ? null : { nombre: text(object(r.conductor).nombre) }
  return { ruta_id: id(r.ruta_id), vehiculo: { placa: text(object(r.vehiculo).placa) }, conductor,
    estado: choice(r.estado, ['PLANIFICADA', 'EN_CURSO', 'CERRADA']), salida, regreso, tiempo_min: nonnegative(r.tiempo_min),
    metricas: { distancia_km: nonnegative(m.distancia_km), co2_kg: nonnegative(m.co2_kg),
      combustible_l: nonnegative(m.combustible_l), costo_soles: nonnegative(m.costo_soles) },
    trazado: { type: 'LineString', coordinates }, paradas }
}
export function noTraffic(): TrafficSnapshot { return { estado: 'SIN_DATOS', fuente: null, actualizado_en: null, tramos: [] } }

/** Project the published ST-045 contract only. Never pretend absent traffic is live. */
export function parseOptimization(value: unknown): OptimizationDetail {
  const v = object(value), base = summary(v), rutas = array(v.rutas).map(route)
  const no_asignados = array(v.no_asignados).map(value => {
    const row = object(value)
    return { pedido_id: id(row.pedido_id), motivo: choice(row.motivo, Object.keys(UNASSIGNED_REASONS) as (keyof typeof UNASSIGNED_REASONS)[]) }
  })
  unique(rutas.map(r => r.ruta_id))
  unique([...rutas.flatMap(r => r.paradas.map(s => s.pedido_id)), ...no_asignados.map(p => p.pedido_id)])
  unique(rutas.flatMap(r => r.paradas.map(s => s.parada_id)))
  ensure(base.estado === 'COMPLETADA' || (rutas.length === 0 && no_asignados.length === 0))
  return { ...base, simulado: boolean(v.simulado), finalizada_en: v.finalizada_en === null ? null : instant(v.finalizada_en),
    rutas, no_asignados, trafico: noTraffic(), alertas: [], alertasDisponibles: false }
}

/** A refresh must never stamp an old traffic measurement with the query time. */
export function retainTraffic(previous: OptimizationDetail | null, incoming: OptimizationDetail): OptimizationDetail {
  if (incoming.trafico.estado !== 'DEGRADADO' || incoming.trafico.actualizado_en) return incoming
  const cached = previous?.optimizacion_id === incoming.optimizacion_id ? previous.trafico : null
  return { ...incoming, trafico: cached?.actualizado_en ? { ...cached, estado: 'DEGRADADO' } : noTraffic() }
}
export const routeTime = (value: string) => new Intl.DateTimeFormat('es-PE', {
  timeZone: 'America/Lima', dateStyle: 'short', timeStyle: 'short', hourCycle: 'h23',
}).format(new Date(value))
export const operationDateInLima = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
export function mapPositions(route: OperationRoute): [number, number][] {
  return route.trazado.coordinates.map(([longitude, latitude]) => [latitude, longitude])
}
