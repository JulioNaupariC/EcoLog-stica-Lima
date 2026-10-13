import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { HomePage } from './HomePage'
import { listVehicles } from '../services/vehicles'
import type { VehicleResponse } from '../services/vehicles'
import { listDrivers } from '../services/drivers'
import { loadItinerary } from '../services/offlineStorage'
import { listPendingReports } from '../services/reportQueue'

vi.mock('../services/vehicles', async original => ({ ...await original<typeof import('../services/vehicles')>(), listVehicles: vi.fn() }))
vi.mock('../services/drivers', async original => ({ ...await original<typeof import('../services/drivers')>(), listDrivers: vi.fn() }))
vi.mock('../services/offlineStorage', async original => ({ ...await original<typeof import('../services/offlineStorage')>(), loadItinerary: vi.fn() }))
vi.mock('../services/reportQueue', async original => ({ ...await original<typeof import('../services/reportQueue')>(), listPendingReports: vi.fn() }))

const owner = '123e4567-e89b-42d3-a456-426614174000'
const vehicle = (estado: string): VehicleResponse => ({
  vehiculo_id: crypto.randomUUID(), placa: 'DEMO-001', tipo: 'CAMIONETA', capacidad_kg: '1', capacidad_m3: '1',
  rendimiento_km_l: '1', factor_co2_kg_km: '0', anio_fabricacion: 2024, estado,
})
const driver = (habilitado: boolean) => ({
  conductor_id: crypto.randomUUID(), nombre: 'X', disponible_desde: null, disponible_hasta: null, estado: 'ACTIVO' as const,
  habilitado_asignacion: habilitado,
})

function show(role: Parameters<typeof HomePage>[0]['role']) {
  render(<MemoryRouter><HomePage role={role} ownerId={owner} /></MemoryRouter>)
}

beforeEach(() => {
  vi.mocked(listVehicles).mockReset().mockResolvedValue([vehicle('ACTIVO'), vehicle('ACTIVO'), vehicle('INACTIVO')])
  vi.mocked(listDrivers).mockReset().mockResolvedValue({ items: [driver(true), driver(false)], page: 1, page_size: 100, total: 2 })
  vi.mocked(loadItinerary).mockReset()
  vi.mocked(listPendingReports).mockReset()
})

describe('HomePage — inicio por rol con datos reales', () => {
  it('ruta dorada: el operador ve totales reales de flota y conductores, y accesos rápidos', async () => {
    show('OPERADOR')
    expect(screen.getByRole('heading', { level: 1, name: 'Inicio' })).toBeInTheDocument()
    expect(await screen.findByText('2 activos')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(await screen.findByText('1 habilitado para asignación')).toBeInTheDocument()
    expect(listDrivers).toHaveBeenCalledWith(1, 100)
    expect(screen.getByRole('link', { name: /Registrar pedido/u })).toHaveAttribute('href', '/pedidos/nuevo')
    expect(screen.getAllByText('Próximamente')).toHaveLength(2)
    // No invented sustainability figures.
    expect(screen.queryByText(/kg CO₂/u)).not.toBeInTheDocument()
  })

  it('ruta feliz: el auditor solo ve la flota; el analista no recibe listados', async () => {
    show('AUDITOR')
    expect(await screen.findByText('2 activos')).toBeInTheDocument()
    expect(listDrivers).not.toHaveBeenCalled()
    expect(screen.queryByRole('link', { name: /Registrar pedido/u })).not.toBeInTheDocument()
  })

  it('ruta infeliz: si un endpoint falla se indica «No disponible» sin estimar cifras', async () => {
    vi.mocked(listVehicles).mockRejectedValue(new Error('caído'))
    vi.mocked(listDrivers).mockRejectedValue(new Error('caído'))
    show('ADMINISTRADOR')
    expect(await screen.findAllByText('No disponible en este momento')).toHaveLength(2)
    expect(screen.getAllByText('—')).toHaveLength(2)
  })

  it('ruta de borde: el analista no tiene listados y el conductor usa datos locales', async () => {
    const view = render(<MemoryRouter><HomePage role="ANALISTA" ownerId={owner} /></MemoryRouter>)
    expect(screen.getByText(/Tu rol no tiene acceso a los listados/u)).toBeInTheDocument()
    expect(listVehicles).not.toHaveBeenCalled()
    view.unmount()

    vi.mocked(loadItinerary).mockResolvedValue({
      ownerId: owner, savedAt: 1, expiresAt: 2,
      stops: [{ stopId: 'a', position: 1, status: 'PENDIENTE' }, { stopId: 'b', position: 2, status: 'ENTREGADO' }],
    })
    vi.mocked(listPendingReports).mockResolvedValue([])
    show('CONDUCTOR')
    expect(await screen.findByText('1 por atender · último itinerario guardado')).toBeInTheDocument()
    expect(await screen.findByText('Todo sincronizado')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Abrir mi itinerario' })).toHaveAttribute('href', '/conductor/itinerario')
  })

  it('ruta de borde: conductor sin itinerario guardado recibe una indicación', async () => {
    vi.mocked(loadItinerary).mockResolvedValue(null)
    vi.mocked(listPendingReports).mockResolvedValue([])
    show('CONDUCTOR')
    expect(await screen.findByText('Abre tu itinerario para cargarlo')).toBeInTheDocument()
  })
})
