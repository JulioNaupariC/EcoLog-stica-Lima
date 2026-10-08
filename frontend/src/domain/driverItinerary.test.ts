import { DEMO_ITINERARY } from '../data/demoDriverItinerary'
import { getNextStop, getStopAlerts } from './driverItinerary'

describe('Siguiente parada y alertas', () => {
  it('elige la primera parada no completada por secuencia sin modificar la entrada', () => {
    const unordered = [DEMO_ITINERARY.stops[3], DEMO_ITINERARY.stops[0], DEMO_ITINERARY.stops[2], DEMO_ITINERARY.stops[1]]
    const original = [...unordered]
    expect(getNextStop(unordered)?.id).toBe('dos')
    expect(unordered).toEqual(original)
  })
  it('no devuelve siguiente parada para una ruta vacía o completada', () => {
    expect(getNextStop([])).toBeUndefined()
    expect(getNextStop([{ ...DEMO_ITINERARY.stops[0], state: 'ENTREGADO' }])).toBeUndefined()
  })
  it('asocia alertas únicamente a las paradas afectadas', () => {
    expect(getStopAlerts(DEMO_ITINERARY.alerts, 'dos')).toHaveLength(1)
    expect(getStopAlerts(DEMO_ITINERARY.alerts, 'tres')).toEqual([])
    expect(getStopAlerts([], 'dos')).toEqual([])
  })
})
