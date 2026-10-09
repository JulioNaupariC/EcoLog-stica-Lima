import 'fake-indexeddb/auto'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DriverItineraryPage } from './DriverItineraryPage'
import {
  DriverItineraryServiceError,
  driverReportTransport,
  getDriverItinerary,
} from '../services/driverItinerary'
import { loadItinerary } from '../services/offlineStorage'
import { listPendingReports } from '../services/reportQueue'

vi.mock('../services/driverItinerary', async importOriginal => {
  const actual = await importOriginal<typeof import('../services/driverItinerary')>()
  return {
    ...actual,
    getDriverItinerary: vi.fn(),
    driverReportTransport: { send: vi.fn() },
  }
})

const ownerId = '123e4567-e89b-42d3-a456-426614174000'
const stopId = '223e4567-e89b-42d3-a456-426614174000'
const getItinerary = vi.mocked(getDriverItinerary)

it('parada pendiente, reporte y ACK: finaliza pantalla y snapshot sin permitir otro reporte', async () => {
  const user = userEvent.setup()
  getItinerary.mockResolvedValueOnce([{ stopId, position: 1, status: 'PENDIENTE' }])
  vi.mocked(driverReportTransport).send.mockImplementation(report =>
    Promise.resolve({ operationId: report.operationId, acknowledged: true }))

  const view = render(<DriverItineraryPage ownerId={ownerId} />)
  expect(await screen.findByText('Pendiente')).toBeInTheDocument()
  await waitFor(async () => expect((await loadItinerary(ownerId))?.stops[0].status).toBe('PENDIENTE'))
  await user.click(screen.getByRole('button', { name: 'Registrar entrega pendiente' }))
  expect(await screen.findByText(/esta parada ya tiene un reporte pendiente/i)).toBeInTheDocument()
  const [pending] = await listPendingReports(ownerId)

  await user.click(screen.getByRole('button', { name: 'Sincronizar pendientes' }))
  expect(await screen.findByText('Entregado')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Registrar entrega pendiente' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Registrar no entregado' })).toBeDisabled()
  expect(await listPendingReports(ownerId)).toEqual([])
  expect((await loadItinerary(ownerId))?.stops[0].status).toBe('ENTREGADO')
  expect(vi.mocked(driverReportTransport).send.mock.calls[0][0].operationId).toBe(pending.operationId)

  view.unmount()
  getItinerary.mockRejectedValueOnce(new DriverItineraryServiceError('Sin conexión', true))
  render(<DriverItineraryPage ownerId={ownerId} />)
  expect(await screen.findByText('Sin conexión: itinerario previamente guardado en este dispositivo.')).toBeInTheDocument()
  expect(screen.getByText('Entregado')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Registrar entrega pendiente' })).toBeDisabled()
})

it('informa el ACK local pendiente y recupera un snapshot vigente sin crear otro identificador', async () => {
  const recoveringOwnerId = '123e4567-e89b-42d3-a456-426614174004'
  const user = userEvent.setup()
  getItinerary.mockResolvedValueOnce([{ stopId, position: 1, status: 'PENDIENTE' }])
  vi.mocked(driverReportTransport).send.mockClear()
  vi.mocked(driverReportTransport).send.mockImplementation(report =>
    Promise.resolve({ operationId: report.operationId, acknowledged: true }))

  const view = render(<DriverItineraryPage ownerId={recoveringOwnerId} />)
  expect(await screen.findByText('Pendiente')).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Registrar entrega pendiente' }))
  expect(await screen.findByText(/esta parada ya tiene un reporte pendiente/i)).toBeInTheDocument()
  const [pending] = await listPendingReports(recoveringOwnerId)

  const db = await new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open('ecologistica-offline-v1', 2)
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(new Error('No se pudo abrir IndexedDB de prueba'))
  })
  const savedAt = Date.now() - 120_000
  await new Promise<void>((resolve, reject) => {
    const transaction = db.transaction('itineraries', 'readwrite')
    transaction.objectStore('itineraries').put({
      ownerId: recoveringOwnerId, savedAt, expiresAt: savedAt + 60_000,
      stops: [{ stopId, position: 1, status: 'PENDIENTE' }],
    }, recoveringOwnerId)
    transaction.oncomplete = () => resolve()
    transaction.onerror = () => reject(new Error('No se pudo vencer el snapshot de prueba'))
  })
  db.close()

  await user.click(screen.getByRole('button', { name: 'Sincronizar pendientes' }))
  expect(await screen.findByText(/el servidor confirmó el reporte, pero falta completar la confirmación en este dispositivo/i)).toBeInTheDocument()
  expect(await listPendingReports(recoveringOwnerId)).toEqual([pending])
  expect(await loadItinerary(recoveringOwnerId)).toBeNull()
  expect(screen.getByRole('button', { name: 'Registrar entrega pendiente' })).toBeDisabled()

  view.unmount()
  getItinerary.mockResolvedValueOnce([{ stopId, position: 1, status: 'ENTREGADO' }])
  render(<DriverItineraryPage ownerId={recoveringOwnerId} />)
  expect(await screen.findByText('Entregado')).toBeInTheDocument()
  await waitFor(async () => expect((await loadItinerary(recoveringOwnerId))?.stops[0].status).toBe('ENTREGADO'))
  await user.click(screen.getByRole('button', { name: 'Sincronizar pendientes' }))
  expect(await screen.findByText('Reportes pendientes: 0')).toBeInTheDocument()
  expect(await listPendingReports(recoveringOwnerId)).toEqual([])
  expect(vi.mocked(driverReportTransport).send.mock.calls.map(([sent]) => sent.operationId)).toEqual([
    pending.operationId, pending.operationId,
  ])
})
