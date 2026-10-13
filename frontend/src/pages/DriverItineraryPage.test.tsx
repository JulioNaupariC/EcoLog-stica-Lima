import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DEMO_ITINERARY } from '../data/demoDriverItinerary'
import { DriverItineraryPage } from './DriverItineraryPage'
import { getDriverItinerary } from '../services/driverItinerary'

vi.mock('../services/driverItinerary', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/driverItinerary')>()
  return { ...actual, getDriverItinerary: vi.fn() }
})

afterEach(() => { vi.unstubAllEnvs() })

describe('DriverItineraryPage — producción, sin datos de demostración', () => {
  it('ruta dorada: por defecto no muestra el itinerario ficticio', () => {
    render(<DriverItineraryPage />)
    expect(screen.getByRole('heading', { name: 'Aún no tienes paradas asignadas' })).toBeInTheDocument()
    expect(screen.queryByRole('note')).not.toBeInTheDocument()
    expect(screen.queryByText('Mercado Central')).not.toBeInTheDocument()
    expect(screen.queryByText(/demostración/u)).not.toBeInTheDocument()
  })

  it('ruta feliz: con sesión y sin paradas asignadas muestra un estado vacío claro', async () => {
    vi.mocked(getDriverItinerary).mockResolvedValueOnce([])
    render(<DriverItineraryPage ownerId="123e4567-e89b-12d3-a456-426614174000" />)
    expect(await screen.findByRole('heading', { name: 'Aún no tienes paradas asignadas' })).toBeInTheDocument()
    expect(screen.getByText(/El servidor no tiene paradas asignadas/u)).toBeInTheDocument()
    expect(screen.queryByRole('note')).not.toBeInTheDocument()
  })

  it('ruta infeliz: si falla la carga sin itinerario guardado ofrece reintentar, sin ejemplo ficticio', async () => {
    vi.mocked(getDriverItinerary).mockRejectedValueOnce(new Error('sin red'))
      .mockResolvedValueOnce([{ stopId: '223e4567-e89b-42d3-a456-426614174000', position: 1, status: 'PENDIENTE' }])
    render(<DriverItineraryPage ownerId="123e4567-e89b-12d3-a456-426614174000" />)
    expect(await screen.findByRole('heading', { name: 'No se pudo cargar tu itinerario' })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('No se pudo cargar el itinerario asignado.')
    expect(screen.queryByRole('heading', { name: 'Aún no tienes paradas asignadas' })).not.toBeInTheDocument()
    expect(screen.queryByText(/ejemplo ficticio/u)).not.toBeInTheDocument()
    expect(screen.queryByText('Mercado Central')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByRole('heading', { name: 'Parada 1' })).toBeInTheDocument()
    expect(getDriverItinerary).toHaveBeenCalledTimes(2)
  })

  it.each(['false', 'TRUE', '1', ''])('ruta de borde: VITE_DEMO_ITINERARY=%j no activa el demo', (value) => {
    vi.stubEnv('VITE_DEMO_ITINERARY', value)
    render(<DriverItineraryPage />)
    expect(screen.queryByRole('note')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Aún no tienes paradas asignadas' })).toBeInTheDocument()
  })
})

describe('DriverItineraryPage — ECL-56, demostración (VITE_DEMO_ITINERARY=true)', () => {
  beforeEach(() => { vi.stubEnv('VITE_DEMO_ITINERARY', 'true') })

  it('ruta de borde: con sesión y sin paradas reales muestra el ejemplo; el error sigue ofreciendo reintentar', async () => {
    vi.mocked(getDriverItinerary).mockResolvedValueOnce([])
    const view = render(<DriverItineraryPage ownerId="123e4567-e89b-12d3-a456-426614174000" />)
    expect(await screen.findByRole('note')).toHaveTextContent('Datos de demostración')
    view.unmount()
    vi.mocked(getDriverItinerary).mockRejectedValueOnce(new Error('sin red'))
    render(<DriverItineraryPage ownerId="123e4567-e89b-12d3-a456-426614174000" />)
    expect(await screen.findByRole('heading', { name: 'No se pudo cargar tu itinerario' })).toBeInTheDocument()
    expect(screen.queryByRole('note')).not.toBeInTheDocument()
  })

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
