import { synchronizeReports } from './reportSync'
import { listPendingReports, confirmReport, markAttempt } from './reportQueue'
import type { PendingDriverReport } from '../types/driverReport'

vi.mock('./reportQueue', () => ({ listPendingReports: vi.fn(), confirmReport: vi.fn(), markAttempt: vi.fn() }))
const owner = '123e4567-e89b-42d3-a456-426614174000'
const report: PendingDriverReport = {
  ownerId: owner, stopId: '223e4567-e89b-42d3-a456-426614174000',
  operationId: '323e4567-e89b-42d3-a456-426614174000',
  status: 'ENTREGADO', createdAt: 10000, attemptCount: 0,
}
const list = vi.mocked(listPendingReports)
const confirm = vi.mocked(confirmReport)
const attempt = vi.mocked(markAttempt)

beforeEach(() => { vi.clearAllMocks() })

describe('Sincronización segura ST-032', () => {
  it('borra únicamente cuando el backend reconoce la operación correcta', async () => {
    list.mockResolvedValueOnce([report]).mockResolvedValueOnce([])
    const result = await synchronizeReports(owner, { send: vi.fn().mockResolvedValue({ operationId: report.operationId, acknowledged: true }) })
    expect(result).toEqual({ sent: 1, pending: 0 })
    expect(confirm).toHaveBeenCalledWith(owner, report.operationId)
  })
  it('conserva pendiente cuando falla la red', async () => {
    list.mockResolvedValueOnce([report]).mockResolvedValueOnce([report])
    const result = await synchronizeReports(owner, { send: vi.fn().mockRejectedValue(new Error('offline')) })
    expect(result).toEqual({ sent: 0, pending: 1 })
    expect(confirm).not.toHaveBeenCalled()
    expect(attempt).toHaveBeenCalledWith(report)
  })
  it('rechaza confirmación con ID diferente y mantiene el reporte', async () => {
    list.mockResolvedValueOnce([report]).mockResolvedValueOnce([report])
    await synchronizeReports(owner, { send: vi.fn().mockResolvedValue({ operationId: owner, acknowledged: true }) })
    expect(confirm).not.toHaveBeenCalled()
    expect(attempt).toHaveBeenCalledWith(report)
  })
})
