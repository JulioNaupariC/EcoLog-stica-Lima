import { render, screen } from '@testing-library/react'
import { listPendingReports } from '../services/reportQueue'
import type { PendingDriverReport } from '../types/driverReport'
import { OfflineReportPanel } from './OfflineReportPanel'

vi.mock('../services/reportQueue', () => ({
  enqueueReport: vi.fn(),
  listPendingReports: vi.fn(),
}))

vi.mock('../services/reportSync', () => ({
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
const transport = {
  send: vi.fn(),
}

describe('OfflineReportPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    listPendingReportsMock.mockResolvedValue([pendingReport])
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
})
