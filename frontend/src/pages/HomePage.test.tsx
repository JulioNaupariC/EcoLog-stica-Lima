import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { HomePage } from './HomePage'
import { getOperationIndicators } from '../services/indicators'
import type { OperationIndicators } from '../services/indicators'
import { listVehicles } from '../services/vehicles'
import { listDrivers } from '../services/drivers'
import { loadItinerary } from '../services/offlineStorage'
import { listPendingReports } from '../services/reportQueue'

vi.mock('../services/indicators', async original => ({ ...await original<typeof import('../services/indicators')>(), getOperationIndicators: vi.fn() }))
vi.mock('../services/vehicles', async original => ({ ...await original<typeof import('../services/vehicles')>(), listVehicles: vi.fn() }))
vi.mock('../services/drivers', async original => ({ ...await original<typeof import('../services/drivers')>(), listDrivers: vi.fn() }))
vi.mock('../services/offlineStorage', async original => ({ ...await original<typeof import('../services/offlineStorage')>(), loadItinerary: vi.fn() }))
vi.mock('../services/reportQueue', async original => ({ ...await original<typeof import('../services/reportQueue')>(), listPendingReports: vi.fn() }))

const owner = '123e4567-e89b-42d3-a456-426614174000'
const indicators = (overrides: Partial<OperationIndicators> = {}): OperationIndicators => ({
  generadoEn: '2026-10-14T09:30:00-05:00',
  vigenciaSegundos: 30,
  vehiculos: { total: 50, activos: 45, capacidadKgActiva: 76500 },
  conductores: { total: 200, habilitadosAsignacion: 145, noHabilitados: 55 },
  pedidos: { total: 30000, porEstado: { PENDIENTE: 30000 }, porPrioridad: { EXPRESS: 6000, ESTANDAR: 15000, ECONOMICO: 9000 } },
  ...overrides,
})

function show(role: Parameters<typeof HomePage>[0]['role']) {
  render(<MemoryRouter><HomePage role={role} ownerId={owner} /></MemoryRouter>)
}

beforeEach(() => {
  vi.mocked(getOperationIndicators).mockReset().mockResolvedValue(indicators())
  vi.mocked(listVehicles).mockReset()
  vi.mocked(listDrivers).mockReset()
  vi.mocked(loadItinerary).mockReset()
  vi.mocked(listPendingReports).mockReset()
})

describe('HomePage — inicio por rol con datos reales', () => {
  it('ruta dorada: el operador ve agregados reales con una sola petición y accesos rápidos', async () => {
    show('OPERADOR')
    expect(screen.getByRole('heading', { level: 1, name: 'Inicio' })).toBeInTheDocument()
    expect(await screen.findByText('45 activos')).toBeInTheDocument()
    expect(screen.getByText('50')).toBeInTheDocument()
    expect(screen.getByText('145 habilitados para asignación')).toBeInTheDocument()
    expect(screen.getByText('30,000 pendientes')).toBeInTheDocument()
    expect(screen.getByText(/^Cifras agregadas a las 9:30/u)).toBeInTheDocument()
    // ECL-25: the lists are no longer downloaded to count them.
    expect(getOperationIndicators).toHaveBeenCalledTimes(1)
    expect(listVehicles).not.toHaveBeenCalled()
    expect(listDrivers).not.toHaveBeenCalled()
    expect(screen.queryByText(/primeros 100/u)).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Registrar pedido/u })).toHaveAttribute('href', '/pedidos/nuevo')
    // Card title plus one badge per planned feature; no sprint names in the UI.
    expect(screen.getAllByText('Próximamente')).toHaveLength(3)
    expect(screen.queryByText(/Sprint/u)).not.toBeInTheDocument()
    // No invented sustainability figures.
    expect(screen.queryByText(/kg CO₂/u)).not.toBeInTheDocument()
  })

  it('ruta feliz: analista y auditor ven el resumen agregado sin accesos de gestión', async () => {
    const view = render(<MemoryRouter><HomePage role="ANALISTA" ownerId={owner} /></MemoryRouter>)
    expect(await screen.findByText('145 habilitados para asignación')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Vehículos/u })).not.toBeInTheDocument()
    view.unmount()
    show('AUDITOR')
    expect(await screen.findByText('45 activos')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Vehículos/u })).toHaveAttribute('href', '/vehiculos')
    expect(screen.queryByRole('link', { name: /Registrar pedido/u })).not.toBeInTheDocument()
  })

  it('ruta infeliz: si el endpoint falla se indica «No disponible» sin estimar cifras', async () => {
    vi.mocked(getOperationIndicators).mockRejectedValue(new Error('caído'))
    show('ADMINISTRADOR')
    expect(await screen.findAllByText('No disponible en este momento')).toHaveLength(3)
    expect(screen.getAllByText('—')).toHaveLength(3)
    expect(screen.queryByText(/Cifras agregadas/u)).not.toBeInTheDocument()
  })

  it('ruta de borde: base vacía muestra ceros y más de 100 conductores se cuentan completos', async () => {
    vi.mocked(getOperationIndicators).mockResolvedValue(indicators({
      vehiculos: { total: 0, activos: 0, capacidadKgActiva: 0 },
      conductores: { total: 0, habilitadosAsignacion: 0, noHabilitados: 0 },
      pedidos: { total: 0, porEstado: {}, porPrioridad: { EXPRESS: 0, ESTANDAR: 0, ECONOMICO: 0 } },
    }))
    const view = render(<MemoryRouter><HomePage role="ADMINISTRADOR" ownerId={owner} /></MemoryRouter>)
    expect(await screen.findByText('0 activos')).toBeInTheDocument()
    expect(screen.getByText('0 pendientes')).toBeInTheDocument()
    view.unmount()
    vi.mocked(getOperationIndicators).mockResolvedValue(indicators({
      conductores: { total: 250, habilitadosAsignacion: 101, noHabilitados: 149 },
    }))
    show('ADMINISTRADOR')
    expect(await screen.findByText('101 habilitados para asignación')).toBeInTheDocument()
    expect(screen.getByText('250')).toBeInTheDocument()
  })

  it('ruta de borde: el conductor usa datos locales y no pide indicadores', async () => {
    vi.mocked(loadItinerary).mockResolvedValue({
      ownerId: owner, savedAt: 1, expiresAt: 2,
      stops: [{ stopId: 'a', position: 1, status: 'PENDIENTE' }, { stopId: 'b', position: 2, status: 'ENTREGADO' }],
    })
    vi.mocked(listPendingReports).mockResolvedValue([])
    show('CONDUCTOR')
    expect(await screen.findByText('1 por atender · último itinerario guardado')).toBeInTheDocument()
    expect(await screen.findByText('Todo sincronizado')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Abrir mi itinerario' })).toHaveAttribute('href', '/conductor/itinerario')
    expect(getOperationIndicators).not.toHaveBeenCalled()
  })

  it('ruta de borde: conductor sin itinerario guardado recibe una indicación', async () => {
    vi.mocked(loadItinerary).mockResolvedValue(null)
    vi.mocked(listPendingReports).mockResolvedValue([])
    show('CONDUCTOR')
    expect(await screen.findByText('Abre tu itinerario para cargarlo')).toBeInTheDocument()
  })
})
