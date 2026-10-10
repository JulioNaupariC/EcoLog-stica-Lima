import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { listPendingReports } from '../services/reportQueue'
import { synchronizeReports } from '../services/reportSync'
import type { PendingDriverReport } from '../types/driverReport'
import { OfflineReportPanel } from './OfflineReportPanel'

vi.mock('../services/reportQueue', () => ({
  enqueueReport: vi.fn(),
  listPendingReports: vi.fn(),
}))

vi.mock('../services/reportSync', async importOriginal => ({
  ...await importOriginal<typeof import('../services/reportSync')>(),
  synchronizeReports: vi.fn(),
}))

const ownerId = '123e4567-e89b-42d3-a456-426614174000'
const stopId = '223e4567-e89b-42d3-a456-426614174000'
const pendingReport: PendingDriverReport = {
  ownerId,
  stopId,
  operationId: '323e4567-e89b-42d3-a456-426614174000',
  status: 'ENTREGADO',
  createdAt: 1000,
  attemptCount: 0,
}
const listPendingReportsMock = vi.mocked(listPendingReports)
const synchronizeReportsMock = vi.mocked(synchronizeReports)
const transport = {
  send: vi.fn(),
}

describe('OfflineReportPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    listPendingReportsMock.mockResolvedValue([pendingReport])
    synchronizeReportsMock.mockImplementation((_owner, _transport, onConfirmed) => {
      onConfirmed?.(pendingReport)
      return Promise.resolve({ sent: 1, pending: 0 })
    })
  })

  it('impide crear un segundo resultado para la misma parada pendiente', async () => {
    render(
      <OfflineReportPanel
        ownerId={ownerId}
        stopId={stopId}
        transport={transport}
      />,
    )

    expect(
      await screen.findByText(/esta parada ya tiene un reporte pendiente/i),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Registrar entrega pendiente' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Registrar no entregado' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Sincronizar pendientes' })).toBeEnabled()
  })

  it('no bloquea una parada distinta por reportes pendientes de otra parada', async () => {
    listPendingReportsMock.mockResolvedValue([
      { ...pendingReport, stopId: '423e4567-e89b-42d3-a456-426614174000' },
    ])

    render(
      <OfflineReportPanel
        ownerId={ownerId}
        stopId={stopId}
        transport={transport}
      />,
    )

    expect(await screen.findByText('Reportes pendientes: 1')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Registrar entrega pendiente' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Registrar no entregado' })).toBeEnabled()
  })

  it('mantiene bloqueado un nuevo reporte para la parada después de recibir ACK', async () => {
    const user = userEvent.setup()
    listPendingReportsMock
      .mockResolvedValueOnce([pendingReport])
      .mockResolvedValue([])

    render(
      <OfflineReportPanel
        ownerId={ownerId}
        stopId={stopId}
        transport={transport}
      />,
    )

    expect(await screen.findByText(/esta parada ya tiene un reporte pendiente/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Sincronizar pendientes' }))

    expect(await screen.findByText('Reportes pendientes: 0')).toBeInTheDocument()
    expect(screen.queryByText(/esta parada ya tiene un reporte pendiente/i)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Registrar entrega pendiente' })).toBeDisabled()
  })

  it('informa un fallo local y conserva bloqueada la parada pendiente', async () => {
    const user = userEvent.setup()
    synchronizeReportsMock.mockRejectedValueOnce(new Error('IndexedDB'))
    render(<OfflineReportPanel ownerId={ownerId} stopId={stopId} transport={transport} />)

    expect(await screen.findByText(/esta parada ya tiene un reporte pendiente/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Sincronizar pendientes' }))

    expect(await screen.findByText(/sincroniza los pendientes existentes con su mismo identificador/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Registrar entrega pendiente' })).toBeDisabled()
  })
})
