export type DeliveryState = 'PENDIENTE' | 'EN_RUTA' | 'ENTREGADO' | 'DEMORADO'
export interface DriverStop {
  id: string
  sequence: number
  order: string
  client: string
  address: string
  window: string
  load: string
  reception: string
  instructions: readonly string[]
  state: DeliveryState
}
export interface DriverAlert {
  id: string
  title: string
  description: string
  instruction: string
  stopIds: readonly string[]
}
// Modelo de demostración; no define un contrato de API.
export interface DemoItinerary {
  id: string
  stops: readonly DriverStop[]
  alerts: readonly DriverAlert[]
}
export const DELIVERY_LABEL: Record<DeliveryState, string> = {
  PENDIENTE: 'Pendiente', EN_RUTA: 'En ruta', ENTREGADO: 'Completada', DEMORADO: 'Demora prevista',
}
export function getNextStop(stops: readonly DriverStop[]): DriverStop | undefined {
  return [...stops].sort((a, b) => a.sequence - b.sequence).find((stop) => stop.state !== 'ENTREGADO')
}
export function getStopAlerts(alerts: readonly DriverAlert[], stopId: string): DriverAlert[] {
  return alerts.filter((alert) => alert.stopIds.includes(stopId))
}

const LIMA_DAY = new Intl.DateTimeFormat('es-PE', { timeZone: 'America/Lima', weekday: 'short', day: '2-digit', month: '2-digit' })
const LIMA_TIME = new Intl.DateTimeFormat('es-PE', { timeZone: 'America/Lima', hour: '2-digit', minute: '2-digit', hour12: false })

/** "mar. 14/10 · 09:00–11:00" in Lima time; spans days when needed. */
export function formatWindow(start: string, end: string): string {
  const from = new Date(start)
  const to = new Date(end)
  const sameDay = LIMA_DAY.format(from) === LIMA_DAY.format(to)
  return sameDay
    ? `${LIMA_DAY.format(from)} · ${LIMA_TIME.format(from)}–${LIMA_TIME.format(to)}`
    : `${LIMA_DAY.format(from)} ${LIMA_TIME.format(from)} – ${LIMA_DAY.format(to)} ${LIMA_TIME.format(to)}`
}
