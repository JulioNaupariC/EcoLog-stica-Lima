import { act, renderHook } from '@testing-library/react'
import { useReportSynchronization } from './useReportSynchronization'
import { synchronizeReports } from '../services/reportSync'
import { listPendingReports } from '../services/reportQueue'
import type { PendingDriverReport } from '../types/driverReport'

vi.mock('../services/reportSync', () => ({ synchronizeReports: vi.fn() }))
vi.mock('../services/reportQueue', () => ({ listPendingReports: vi.fn() }))
const owner = '123e4567-e89b-42d3-a456-426614174005'
const pending: PendingDriverReport = { ownerId: owner, stopId: '223e4567-e89b-42d3-a456-426614174001', operationId: '323e4567-e89b-42d3-a456-426614174001', status: 'ENTREGADO', createdAt: 1, attemptCount: 0 }
beforeEach(() => {
  vi.useFakeTimers(); vi.clearAllMocks()
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true)
  vi.mocked(listPendingReports).mockResolvedValue([])
  vi.mocked(synchronizeReports).mockResolvedValue({ sent: 1, pending: 0 })
})
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks() })

it('automatically syncs on reconnection after verifying the server', async () => {
  const verify = vi.fn().mockResolvedValue(true), confirmed = vi.fn()
  const view = renderHook(() => useReportSynchronization(owner, true, verify, confirmed))
  await act(async () => { await Promise.resolve() })
  expect(verify).not.toHaveBeenCalled()
  await act(async () => { window.dispatchEvent(new Event('online')); await Promise.resolve() })
  expect(verify).toHaveBeenCalledOnce()
  expect(synchronizeReports).toHaveBeenCalledWith(owner, expect.anything(), expect.any(Function))
  expect(view.result.current).toContain('1 confirmados automáticamente; 0 pendientes')
  view.unmount()
})

it('recovers persisted pending reports on mount', async () => {
  vi.mocked(listPendingReports).mockResolvedValue([pending])
  const verify = vi.fn().mockResolvedValue(true)
  const confirmed = vi.fn()
  const view = renderHook(() => useReportSynchronization(owner, true, verify, confirmed))
  await act(async () => { await Promise.resolve(); await vi.advanceTimersByTimeAsync(500) })
  expect(synchronizeReports).toHaveBeenCalledOnce()
  view.unmount()
})

it('backs off after server failure and cancels retries when offline or unmounted', async () => {
  const verify = vi.fn().mockRejectedValueOnce(new Error('503')).mockResolvedValue(true)
  const confirmed = vi.fn()
  const view = renderHook(() => useReportSynchronization(owner, true, verify, confirmed))
  await act(async () => { window.dispatchEvent(new Event('online')); await Promise.resolve() })
  expect(synchronizeReports).not.toHaveBeenCalled()
  await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
  expect(synchronizeReports).toHaveBeenCalledOnce()
  act(() => { window.dispatchEvent(new Event('offline')) })
  expect(view.result.current).toContain('Sin conexión')
  view.unmount()
  await act(async () => { window.dispatchEvent(new Event('online')); await vi.advanceTimersByTimeAsync(60_000) })
  expect(synchronizeReports).toHaveBeenCalledOnce()
})

it('never sends when session verification fails or itinerary is not ready', async () => {
  const verify = vi.fn().mockResolvedValue(false)
  const confirmed = vi.fn()
  const view = renderHook(() => useReportSynchronization(owner, true, verify, confirmed))
  await act(async () => { window.dispatchEvent(new Event('online')); await Promise.resolve() })
  expect(synchronizeReports).not.toHaveBeenCalled()
  view.unmount()
  const disabled = renderHook(() => useReportSynchronization(undefined, false, verify, confirmed))
  act(() => { window.dispatchEvent(new Event('online')) })
  expect(verify).toHaveBeenCalledOnce()
  disabled.unmount()
})

it('notifies the page of confirmations and retries only remaining reports', async () => {
  const verify = vi.fn().mockResolvedValue(true), confirmed = vi.fn()
  vi.mocked(synchronizeReports).mockImplementationOnce((_owner, _transport, callback) => {
    callback?.(pending)
    return Promise.resolve({ sent: 1, pending: 1 })
  })
  const view = renderHook(() => useReportSynchronization(owner, true, verify, confirmed))
  await act(async () => { window.dispatchEvent(new Event('online')); await Promise.resolve() })
  expect(confirmed).toHaveBeenCalledWith(pending)
  await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
  expect(synchronizeReports).toHaveBeenCalledTimes(2)
  view.unmount()
})

it('does not send while offline, even when a stale online event arrives', async () => {
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false)
  const verify = vi.fn(), confirmed = vi.fn()
  const view = renderHook(() => useReportSynchronization(owner, true, verify, confirmed))
  await act(async () => { window.dispatchEvent(new Event('online')); await vi.advanceTimersByTimeAsync(60_000) })
  expect(verify).not.toHaveBeenCalled()
  view.unmount()
})
