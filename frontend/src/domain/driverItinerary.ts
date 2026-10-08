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
