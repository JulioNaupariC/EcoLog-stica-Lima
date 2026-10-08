import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DEMO_ITINERARY } from '../data/demoDriverItinerary'
import { DriverItineraryPage } from './DriverItineraryPage'

describe('DriverItineraryPage — ECL-56, demostración', () => {
  it('distingue la siguiente parada, la alerta y el aviso de datos ficticios', () => {
    render(<DriverItineraryPage />)
    expect(screen.getByRole('note')).toHaveTextContent('Datos de demostración')
    expect(screen.getByRole('note')).toHaveTextContent('alertas ficticios')
    expect(within(screen.getByRole('region', { name: 'Siguiente parada' })).getByText('Mercado Central')).toBeInTheDocument()
    expect(within(screen.getByRole('region', { name: 'Alertas operativas de demostración' })).getByText('Av. Abancay: +15 min previstos.')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /^Ver parada/ })).toHaveLength(4)
  })

  it('abre el detalle de la siguiente parada y vuelve con foco en el título', async () => {
    const user = userEvent.setup()
    render(<DriverItineraryPage />)
    await user.click(screen.getByRole('button', { name: 'Ver detalle de parada' }))
    expect(screen.getByRole('heading', { name: 'Detalle de parada' })).toHaveFocus()
    expect(screen.getByText('DEMO-102')).toBeInTheDocument()
    expect(screen.getByText('Av. Abancay: +15 min previstos.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Volver al itinerario' }))
    expect(screen.getByRole('heading', { name: 'Mi itinerario' })).toHaveFocus()
  })

  it.each([
    ['PENDIENTE', 'Punto de distribución', '3'],
    ['EN_RUTA', 'Mercado Central', '2'],
    ['ENTREGADO', 'Almacén de salida', '1'],
    ['DEMORADO', 'Centro de acopio', '4'],
  ])('filtra %s sin cambiar la siguiente parada ni la secuencia', async (state, client, sequence) => {
    const user = userEvent.setup()
    render(<DriverItineraryPage />)
    await user.selectOptions(screen.getByLabelText('Filtrar por estado'), state)
    expect(screen.getAllByRole('button', { name: /^Ver parada/ })).toHaveLength(1)
    expect(screen.getByRole('button', { name: `Ver parada ${sequence}: ${client}` })).toBeInTheDocument()
    expect(within(screen.getByRole('region', { name: 'Siguiente parada' })).getByText('Mercado Central')).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Filtrar por estado'), 'TODAS')
    expect(screen.getAllByRole('button', { name: /^Ver parada/ })).toHaveLength(4)
  })

  it('conserva el filtro al volver del detalle y muestra solo alertas aplicables', async () => {
    const user = userEvent.setup()
    render(<DriverItineraryPage />)
    await user.selectOptions(screen.getByLabelText('Filtrar por estado'), 'PENDIENTE')
    await user.click(screen.getByRole('button', { name: 'Ver parada 3: Punto de distribución' }))
    expect(screen.getByText('DEMO-103')).toBeInTheDocument()
    expect(screen.getByText('No hay alertas operativas en este ejemplo.')).toBeInTheDocument()
    expect(screen.queryByText('Av. Abancay: +15 min previstos.')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Volver al itinerario' }))
    expect(screen.getByLabelText('Filtrar por estado')).toHaveValue('PENDIENTE')
  })

  it('navega al estado sin asignación y vuelve al ejemplo completo', async () => {
    const user = userEvent.setup()
    render(<DriverItineraryPage />)
    await user.selectOptions(screen.getByLabelText('Filtrar por estado'), 'DEMORADO')
    await user.click(screen.getByRole('button', { name: 'Ver ejemplo sin asignación' }))
    expect(screen.getByRole('heading', { name: 'Aún no tienes un itinerario' })).toBeInTheDocument()
    expect(screen.queryByText('Av. Abancay: +15 min previstos.')).not.toBeInTheDocument()
    expect(screen.getByRole('note')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Cargar ejemplo de itinerario' }))
    expect(screen.getByLabelText('Filtrar por estado')).toHaveValue('TODAS')
    expect(screen.getAllByRole('button', { name: /^Ver parada/ })).toHaveLength(4)
  })

  it('no inventa una ruta cuando no hay itinerario', () => {
    render(<DriverItineraryPage itinerary={null} />)
    expect(screen.getByRole('heading', { name: 'Aún no tienes un itinerario' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Cargar ejemplo de itinerario' })).not.toBeInTheDocument()
  })

  it('maneja una ruta completada, ausencia de alertas y un filtro vacío', async () => {
    const user = userEvent.setup()
    render(<DriverItineraryPage itinerary={{ ...DEMO_ITINERARY, alerts: [], stops: [{ ...DEMO_ITINERARY.stops[0], state: 'ENTREGADO' }] }} />)
    expect(screen.getByText('No hay paradas pendientes en este ejemplo.')).toBeInTheDocument()
    expect(screen.getByText('No hay alertas operativas en este ejemplo.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Ver parada 1: Almacén de salida' }))
    expect(screen.getByText('DEMO-101')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Volver al itinerario' }))
    await user.selectOptions(screen.getByLabelText('Filtrar por estado'), 'EN_RUTA')
    expect(screen.getByRole('status')).toHaveTextContent('No hay paradas con este estado.')
  })

  it('permite abrir y regresar del detalle con teclado', async () => {
    const user = userEvent.setup()
    render(<DriverItineraryPage />)
    await user.tab()
    expect(screen.getByRole('button', { name: 'Ver detalle de parada' })).toHaveFocus()
    await user.keyboard('{Enter}')
    expect(screen.getByRole('heading', { name: 'Detalle de parada' })).toHaveFocus()
    await user.tab()
    expect(screen.getByRole('button', { name: 'Volver al itinerario' })).toHaveFocus()
    await user.keyboard(' ')
    expect(screen.getByRole('heading', { name: 'Mi itinerario' })).toHaveFocus()
  })
})
