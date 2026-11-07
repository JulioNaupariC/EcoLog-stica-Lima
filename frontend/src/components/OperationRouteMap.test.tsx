import { act, render, screen, waitFor } from '@testing-library/react'
import * as L from 'leaflet'
import { OperationRouteMap } from './OperationRouteMap'
import { operationFixture, withSyntheticTraffic } from '../test/operationRoutesFixtures'

const mock = vi.hoisted(() => {
  const map = { fitBounds: vi.fn(), remove: vi.fn(), invalidateSize: vi.fn() }
  const layer = { on: vi.fn(), addTo: vi.fn(), bindPopup: vi.fn(), openPopup: vi.fn() }
  return { map, layer, tileError: null as null | (() => void), resize: null as null | (() => void), disconnect: vi.fn() }
})
const scrollMock = vi.fn()
vi.mock('leaflet', () => ({
  map: vi.fn(() => mock.map), control: { zoom: vi.fn(() => mock.layer) },
  tileLayer: vi.fn(() => mock.layer), polyline: vi.fn(() => mock.layer),
  marker: vi.fn(() => mock.layer), divIcon: vi.fn(), latLngBounds: vi.fn((value: unknown) => value),
}))
beforeEach(() => {
  vi.clearAllMocks()
  mock.layer.addTo.mockReturnValue(mock.layer)
  mock.layer.bindPopup.mockReturnValue(mock.layer)
  mock.layer.on.mockImplementation((_event, callback: () => void) => { mock.tileError = callback; return mock.layer })
  vi.mocked(L.map).mockReturnValue(mock.map as unknown as L.Map)
  Element.prototype.scrollIntoView = scrollMock
  vi.stubGlobal('ResizeObserver', class {
    constructor(callback: () => void) { mock.resize = callback }
    observe() {}
    disconnect() { mock.disconnect() }
  })
})
afterEach(() => vi.unstubAllGlobals())

it('M01: dibuja coordenadas y marcadores numerados con popup seguro y atribución OSM', () => {
  const data = withSyntheticTraffic(), route = data.rutas[0]
  route.conductor = { nombre: '<img src=x onerror=alert(1)>' }
  data.alertas[0].texto = '<script>PRIVATE</script>'
  const { unmount } = render(<OperationRouteMap route={route} alerts={data.alertas} />)
  expect(L.polyline).toHaveBeenCalledWith(expect.arrayContaining([[-12.047, -76.968]]), expect.any(Object))
  expect(L.marker).toHaveBeenCalledTimes(route.paradas.length)
  expect(L.marker).toHaveBeenNthCalledWith(1, [route.paradas[0].latitud, route.paradas[0].longitud], expect.objectContaining({ title: 'Parada 1' }))
  const popup = mock.layer.bindPopup.mock.calls[0][0] as HTMLParagraphElement
  expect(popup.textContent).toContain('<script>PRIVATE</script>')
  expect(popup.querySelector('script')).toBeNull()
  expect(screen.getByRole('link', { name: 'OpenStreetMap contributors' })).toHaveAttribute('href', 'https://www.openstreetmap.org/copyright')
  expect(screen.getByText(/©/)).toBeInTheDocument()
  act(() => mock.resize?.())
  expect(mock.map.invalidateSize).toHaveBeenCalledOnce()
  unmount()
  expect(mock.map.remove).toHaveBeenCalledOnce()
  expect(mock.disconnect).toHaveBeenCalledOnce()
})
it('M05: avisa si las teselas fallan sin retirar el contenedor ni el trazado', () => {
  render(<OperationRouteMap route={operationFixture().rutas[0]} alerts={[]} />)
  act(() => mock.tileError?.())
  expect(screen.getByRole('status')).toHaveTextContent('la lista de paradas siguen disponibles')
  expect(screen.getByRole('region', { name: 'Mapa de ruta ECO-101' })).toBeInTheDocument()
})
it('selecciona una parada mediante el control equivalente de la lista', () => {
  const route = operationFixture().rutas[0]
  render(<OperationRouteMap route={route} alerts={[]} selectedStopId={route.paradas[0].parada_id} />)
  expect(mock.layer.openPopup).toHaveBeenCalledOnce()
  expect(scrollMock).toHaveBeenCalledOnce()
})
it('M05: un fallo de inicialización ofrece la alternativa accesible', async () => {
  vi.mocked(L.map).mockImplementationOnce(() => { throw new Error('PRIVATE') })
  render(<OperationRouteMap route={operationFixture().rutas[0]} alerts={[]} />)
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Consulta la lista de paradas'))
  expect(document.body).not.toHaveTextContent('PRIVATE')
})
