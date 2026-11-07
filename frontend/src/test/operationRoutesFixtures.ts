import raw from './fixtures/rutas/optimizacion-completada.json'
import { parseOptimization } from '../domain/operationRoutes'
import type { OptimizationDetail, OptimizationPage, TrafficSnapshot } from '../domain/operationRoutes'

export const operationFixture = () => parseOptimization(structuredClone(raw))
export const operationPage = (): OptimizationPage => {
  const data = operationFixture()
  return { items: [{ optimizacion_id: data.optimizacion_id, estado: data.estado,
    fecha_operacion: data.fecha_operacion, solicitada_en: data.solicitada_en }], page: 1, page_size: 12, total: 1, simulado: true }
}
/** Synthetic presentation scenarios, not an unpublished backend contract. */
export function withSyntheticTraffic(data = operationFixture()): OptimizationDetail {
  return { ...data, alertasDisponibles: true, trafico: {
    estado: 'DISPONIBLE', fuente: 'Fuente sintética M02', actualizado_en: '2026-11-20T08:00:00-05:00',
    tramos: [{ rutaId: data.rutas[0].ruta_id, origen: 'Depósito', destino: 'Parada 1', tiempo_min: 12 }],
  }, alertas: [{ id: 'riesgo-sintetico', rutaId: data.rutas[0].ruta_id, paradaId: data.rutas[0].paradas[0].parada_id,
    tipo: 'Seguridad vial', texto: 'Riesgo sintético no bloqueante', severidad: 'MEDIA', fuente: 'Fixture M02',
    hora: '2026-11-20T07:55:00-05:00', alcance: 'Entorno de parada 1', bloqueo: false },
  { id: 'bloqueo-sintetico', rutaId: data.rutas[0].ruta_id, tipo: 'Restricción vial', texto: 'Bloqueo sintético configurado por Administrador',
    severidad: 'ALTA', fuente: 'Fixture M02', hora: '2026-11-20T07:56:00-05:00', alcance: 'Tramo alternativo', bloqueo: true }] }
}
export const degradedTraffic = (): TrafficSnapshot => ({ estado: 'DEGRADADO', fuente: null, actualizado_en: null, tramos: [] })
