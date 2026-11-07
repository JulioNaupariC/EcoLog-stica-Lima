import completed from '../test/fixtures/rutas/optimizacion-completada.json'
import inProgress from '../test/fixtures/rutas/optimizacion-en-proceso.json'
import failed from '../test/fixtures/rutas/optimizacion-fallida.json'
import listing from '../test/fixtures/rutas/optimizaciones-pagina.json'
import { InvalidRouteData, mapPositions, noTraffic, operationDateInLima, parseOptimization, parseOptimizationPage, retainTraffic, routeTime, validOperationDate } from './operationRoutes'
import { degradedTraffic, operationFixture, withSyntheticTraffic } from '../test/operationRoutesFixtures'

it('M01: consume ST-045, conserva el orden y convierte GeoJSON a Leaflet sin invertir las paradas', () => {
  const detail = parseOptimization(completed)
  expect(detail.simulado).toBe(true)
  expect(detail.rutas[0].paradas.map(p => p.secuencia)).toEqual(completed.rutas[0].paradas.map(p => p.secuencia))
  expect(mapPositions(detail.rutas[0])[0]).toEqual([-12.047, -76.968])
  expect(detail.rutas[0].paradas[0].latitud).toBe(completed.rutas[0].paradas[0].latitud)
  expect(detail.trafico).toEqual(noTraffic())
  expect(detail.alertasDisponibles).toBe(false)
})
it.each([inProgress, failed])('M06: admite estado $estado sin dibujar rutas', body => {
  expect(parseOptimization(body).rutas).toEqual([])
})
it('admite ruta sin conductor y no conserva datos personales extra', () => {
  const data = structuredClone(completed)
  const value = { ...data, rutas: [{ ...data.rutas[0], conductor: null }] }
  expect(parseOptimization(value).rutas[0].conductor).toBeNull()
  expect(parseOptimization({ ...value, error: 'PRIVATE_TRACE' })).not.toHaveProperty('error')
})
it.each([
  (v: typeof completed) => { v.rutas[0].trazado.coordinates[0] = [181, 0] },
  (v: typeof completed) => { v.rutas[0].trazado.coordinates[0] = [0, -91] },
  (v: typeof completed) => { v.rutas[0].trazado.type = 'Polygon' },
  (v: typeof completed) => { v.rutas[0].trazado.coordinates = [[0, 0]] },
  (v: typeof completed) => { v.rutas[0].paradas[0].secuencia = 2 },
  (v: typeof completed) => { v.rutas[0].paradas[1].secuencia = 1 },
  (v: typeof completed) => { v.rutas[0].paradas[0].latitud = NaN },
  (v: typeof completed) => { v.rutas[0].paradas[0].eta = '2026-11-20T10:00:00Z' },
  (v: typeof completed) => { v.rutas[0].paradas[0].ventana_fin = v.rutas[0].paradas[0].ventana_inicio },
  (v: typeof completed) => { v.rutas[0].metricas.co2_kg = -1 },
  (v: typeof completed) => { v.rutas[0].paradas[1].pedido_id = v.rutas[0].paradas[0].pedido_id },
  (v: typeof completed) => { v.no_asignados[0].pedido_id = v.rutas[0].paradas[0].pedido_id },
  (v: typeof completed) => { v.rutas[0].regreso = '2026-11-20T01:00:00-05:00' },
  (v: typeof completed) => { v.estado = 'UNKNOWN' },
])('M04: rechaza datos incoherentes antes de representar', mutate => {
  const data = structuredClone(completed); mutate(data)
  expect(() => parseOptimization(data)).toThrow(InvalidRouteData)
})
it.each([null, [], {}, { ...listing, total: -1 }, { ...listing, page: 0 }, { ...listing, page_size: 101 },
  { ...listing, items: [listing.items[0], listing.items[0]] }, { ...listing, simulado: 'true' }])('rechaza páginas inválidas', value => {
  expect(() => parseOptimizationPage(value)).toThrow(InvalidRouteData)
})
it('acepta el índice original ST-045 sin transformarlo en detalle', () => {
  expect(parseOptimizationPage(listing).items).toHaveLength(3)
})
it('M03: conserva la fuente, hora T0 y medición al fallar en T1', () => {
  const previous = withSyntheticTraffic()
  const incoming = { ...operationFixture(), trafico: degradedTraffic() }
  expect(retainTraffic(previous, incoming).trafico).toEqual({ ...previous.trafico, estado: 'DEGRADADO' })
  expect(retainTraffic(null, incoming).trafico).toEqual(noTraffic())
  expect(retainTraffic(operationFixture(), incoming).trafico).toEqual(noTraffic())
  expect(retainTraffic(previous, { ...incoming, optimizacion_id: 'other' }).trafico).toEqual(noTraffic())
  expect(retainTraffic(previous, previous)).toBe(previous)
})
it('M05: sin historial no inventa tráfico y permite horas de Lima', () => {
  expect(noTraffic().actualizado_en).toBeNull()
  expect(routeTime('2026-11-20T09:22:00-05:00')).toContain('09:22')
  expect(validOperationDate(operationDateInLima())).toBe(true)
  expect(validOperationDate('2026-02-30')).toBe(false)
  expect(validOperationDate('private')).toBe(false)
})
