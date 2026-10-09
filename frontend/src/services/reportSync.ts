/** Sync orchestration. A real authenticated/idempotent backend adapter is REQUIRED. */
import { confirmReport, listPendingReports, markAttempt } from './reportQueue'
import type { PendingDriverReport } from '../types/driverReport'

export interface ReportTransport {
  /** Resolve ONLY after backend acknowledges the same operationId. Throw on timeout/network/HTTP errors. */
  send(report: PendingDriverReport): Promise<{ operationId: string; acknowledged: true }>
}

const inProgress = new Set<string>()

export async function synchronizeReports(ownerId: string, transport: ReportTransport): Promise<{ sent: number; pending: number }> {
  if (inProgress.has(ownerId)) throw new Error('Sincronización ya en curso')
  inProgress.add(ownerId)
  let sent = 0
  try {
    // Verify connectivity against API through the transport; navigator.onLine is not proof.
    const pending = await listPendingReports(ownerId)
    for (const report of pending) {
      try {
        const ack = await transport.send(report)
        if (ack.acknowledged !== true || ack.operationId !== report.operationId) {
          throw new Error('Confirmación inválida del servidor')
        }
        await confirmReport(ownerId, report.operationId)
        sent += 1
      } catch {
        await markAttempt(report)
        // Preserve order and stop to avoid retry storms while server is unavailable.
        break
      }
    }
    const remaining = await listPendingReports(ownerId)
    return { sent, pending: remaining.length }
  } finally { inProgress.delete(ownerId) }
}
