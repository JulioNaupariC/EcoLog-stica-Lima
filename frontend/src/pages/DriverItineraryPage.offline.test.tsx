import 'fake-indexeddb/auto'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DriverItineraryPage } from './DriverItineraryPage'
import { DriverItineraryServiceError, driverReportTransport, getDriverItinerary } from '../services/driverItinerary'
import { loadItinerary, saveItinerary } from '../services/offlineStorage'
import { listPendingReports } from '../services/reportQueue'

vi.mock('../services/driverItinerary', async importOriginal => ({
  ...await importOriginal<typeof import('../services/driverItinerary')>(),
  getDriverItinerary: vi.fn(), driverReportTransport: { send: vi.fn() },
}))
const owner = '123e4567-e89b-42d3-a456-426614174010'
const stop = { stopId: '223e4567-e89b-42d3-a456-426614174010', position: 1, status: 'PENDIENTE' as const,
  delivery: { address: 'Av. Sintetica 10', reference: 'Puerta de prueba', windowStart: '2026-10-09T10:00:00Z', windowEnd: '2026-10-09T11:00:00Z' } }
afterEach(() => { vi.restoreAllMocks(); vi.clearAllMocks() })

it('preserves delivery details and automatically updates page/outbox/snapshot after reconnection', async () => {
  const online = vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false)
  vi.mocked(getDriverItinerary).mockResolvedValue([stop])
  vi.mocked(driverReportTransport).send.mockImplementation(report => Promise.resolve({ operationId: report.operationId, acknowledged: true }))
  render(<DriverItineraryPage ownerId={owner} />)
  expect(await screen.findByText(stop.delivery.address)).toBeInTheDocument()
  expect(screen.getByText('Horario de entrega')).toBeInTheDocument()
  await userEvent.setup().click(screen.getByRole('button', { name: 'Registrar entrega pendiente' }))
  expect(await screen.findByText('Reportes pendientes: 1')).toBeInTheDocument()
  online.mockReturnValue(true)
  act(() => { window.dispatchEvent(new Event('online')) })
  expect(await screen.findByText('Entregado')).toBeInTheDocument()
  await waitFor(async () => expect(await listPendingReports(owner)).toEqual([]))
  expect((await loadItinerary(owner))?.stops[0]).toMatchObject({ status: 'ENTREGADO', delivery: stop.delivery })
})

it('retrieves address/window offline from a previously saved snapshot', async () => {
  const cachedOwner = '123e4567-e89b-42d3-a456-426614174011', savedAt = Date.now()
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false)
  await saveItinerary({ ownerId: cachedOwner, savedAt, expiresAt: savedAt + 60_000, stops: [stop] })
  vi.mocked(getDriverItinerary).mockRejectedValueOnce(new DriverItineraryServiceError('Sin red', true))
  render(<DriverItineraryPage ownerId={cachedOwner} />)
  expect(await screen.findByText('Sin conexión: itinerario previamente guardado en este dispositivo.')).toBeInTheDocument()
  expect(screen.getByText(stop.delivery.address)).toBeInTheDocument()
})

it('rejects an expired server session instead of exposing a cached itinerary', async () => {
  const expired = vi.fn()
  vi.mocked(getDriverItinerary).mockRejectedValueOnce(new DriverItineraryServiceError('Sesión vencida', false, 401))
  render(<DriverItineraryPage ownerId={owner} onSessionExpired={expired} />)
  await waitFor(() => expect(expired).toHaveBeenCalledOnce())
  expect(screen.queryByText(stop.delivery.address)).not.toBeInTheDocument()
})
