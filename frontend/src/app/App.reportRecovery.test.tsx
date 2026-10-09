import 'fake-indexeddb/auto'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { App } from './App'
import { login } from '../services/auth'
import { driverReportTransport, getDriverItinerary } from '../services/driverItinerary'
import { loadItinerary } from '../services/offlineStorage'
import { listPendingReports } from '../services/reportQueue'

vi.mock('../services/auth', async importOriginal => ({
  ...await importOriginal<typeof import('../services/auth')>(),
  login: vi.fn(),
}))

vi.mock('../services/driverItinerary', async importOriginal => ({
  ...await importOriginal<typeof import('../services/driverItinerary')>(),
  getDriverItinerary: vi.fn(),
  driverReportTransport: { send: vi.fn() },
}))

const ownerId = '123e4567-e89b-42d3-a456-426614174005'
const stopId = '223e4567-e89b-42d3-a456-426614174000'
const recoveryMessage = 'El servidor confirmó el reporte, pero falta completar la confirmación en este dispositivo. Con conexión, ve a Inicio y vuelve a Mi itinerario para actualizarlo. Después pulsa Sincronizar pendientes. Tu reporte conserva el mismo identificador.'

function CurrentPath() {
  const location = useLocation()
  return <span data-testid="current-path">{location.pathname}</span>
}

async function expireSnapshot(): Promise<void> {
  const db = await new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open('ecologistica-offline-v1', 2)
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(new Error('No se pudo abrir IndexedDB de prueba'))
  })
  try {
    const savedAt = Date.now() - 120_000
    await new Promise<void>((resolve, reject) => {
      const transaction = db.transaction('itineraries', 'readwrite')
      transaction.objectStore('itineraries').put({
        ownerId, savedAt, expiresAt: savedAt + 60_000,
        stops: [{ stopId, position: 1, status: 'PENDIENTE' }],
      }, ownerId)
      transaction.oncomplete = () => resolve()
      transaction.onerror = () => reject(new Error('No se pudo vencer el snapshot de prueba'))
    })
  } finally { db.close() }
}

it('recupera el snapshot al navegar por Inicio y Mi itinerario dentro de App', async () => {
  const user = userEvent.setup()
  vi.mocked(login).mockResolvedValue({ usuario_id: ownerId, rol: 'CONDUCTOR' })
  vi.mocked(getDriverItinerary)
    .mockResolvedValueOnce([{ stopId, position: 1, status: 'PENDIENTE' }])
    .mockResolvedValueOnce([{ stopId, position: 1, status: 'ENTREGADO' }])
  vi.mocked(driverReportTransport).send.mockImplementation(report =>
    Promise.resolve({ operationId: report.operationId, acknowledged: true }))

  render(<MemoryRouter initialEntries={['/login']}><CurrentPath /><App /></MemoryRouter>)
  await user.type(screen.getByLabelText('Correo electrónico'), 'driver@example.test')
  await user.type(screen.getByLabelText('Contraseña'), 'test-password')
  await user.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
  expect(await screen.findByRole('heading', { name: 'Rutas sostenibles para Lima' })).toBeInTheDocument()

  await user.click(screen.getByRole('link', { name: 'Mi itinerario' }))
  expect(screen.getByTestId('current-path')).toHaveTextContent('/conductor/itinerario')
  expect(await screen.findByText('Pendiente')).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Registrar entrega pendiente' }))
  expect(await screen.findByText(/esta parada ya tiene un reporte pendiente/i)).toBeInTheDocument()
  const [pending] = await listPendingReports(ownerId)

  await expireSnapshot()
  await user.click(screen.getByRole('button', { name: 'Sincronizar pendientes' }))
  expect(await screen.findByText(recoveryMessage)).toBeInTheDocument()
  expect(await listPendingReports(ownerId)).toEqual([pending])
  expect(await loadItinerary(ownerId)).toBeNull()
  expect(screen.getByRole('button', { name: 'Registrar entrega pendiente' })).toBeDisabled()

  await user.click(screen.getByRole('link', { name: 'EcoLogística Lima' }))
  expect(screen.getByTestId('current-path')).toHaveTextContent('/')
  expect(screen.getByText('Rol: CONDUCTOR')).toBeInTheDocument()
  await user.click(screen.getByRole('link', { name: 'Mi itinerario' }))
  expect(screen.getByTestId('current-path')).toHaveTextContent('/conductor/itinerario')
  expect(await screen.findByText('Entregado')).toBeInTheDocument()
  await waitFor(async () => expect((await loadItinerary(ownerId))?.stops[0].status).toBe('ENTREGADO'))
  expect(getDriverItinerary).toHaveBeenCalledTimes(2)

  await user.click(screen.getByRole('button', { name: 'Sincronizar pendientes' }))
  expect(await screen.findByText('Reportes pendientes: 0')).toBeInTheDocument()
  expect(await listPendingReports(ownerId)).toEqual([])
  expect((await loadItinerary(ownerId))?.stops[0].status).toBe('ENTREGADO')
  expect(screen.getByRole('button', { name: 'Registrar entrega pendiente' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Registrar no entregado' })).toBeDisabled()
  expect(vi.mocked(driverReportTransport).send.mock.calls.map(([sent]) => sent.operationId)).toEqual([
    pending.operationId, pending.operationId,
  ])
})
