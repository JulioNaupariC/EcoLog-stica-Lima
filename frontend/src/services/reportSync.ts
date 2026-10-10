/** Sync orchestration. A real authenticated/idempotent backend adapter is REQUIRED. */
import { confirmAcknowledgedReport, listPendingReports, markAttempt } from './reportQueue'
import type { PendingDriverReport } from '../types/driverReport'

export interface ReportTransport {
  /** Resolve ONLY after backend acknowledges the same operationId. Throw on timeout/network/HTTP errors. */
  send(report: PendingDriverReport): Promise<{ operationId: string; acknowledged: true }>
}

const inProgress = new Set<string>()

export class AcknowledgedReportPendingError extends Error {
  constructor() {
    super('El servidor confirmó el reporte, pero falta completar la confirmación en este dispositivo. Con conexión, ve a Inicio y vuelve a Mi itinerario para actualizarlo. Después pulsa Sincronizar pendientes. Tu reporte conserva el mismo identificador.')
    this.name = 'AcknowledgedReportPendingError'
  }
}

async function performSynchronization(
  ownerId: string,
  transport: ReportTransport,
  onConfirmed?: (report: PendingDriverReport) => void,
): Promise<{ sent: number; pending: number }> {
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
      } catch {
        await markAttempt(report)
        // Preserve order and stop to avoid retry storms while server is unavailable.
        break
      }
      // A local failure keeps the original operation ID for an idempotent retry.
      try {
        await confirmAcknowledgedReport(report)
      } catch {
        throw new AcknowledgedReportPendingError()
      }
      sent += 1
      onConfirmed?.(report)
    }
    const remaining = await listPendingReports(ownerId)
    return { sent, pending: remaining.length }
  } finally { inProgress.delete(ownerId) }
}

/** Web Locks coordinates tabs; backend operation_id remains the final duplicate guard. */
export async function synchronizeReports(
  ownerId: string,
  transport: ReportTransport,
  onConfirmed?: (report: PendingDriverReport) => void,
): Promise<{ sent: number; pending: number }> {
  if (typeof navigator !== 'undefined' && navigator.locks) {
    return navigator.locks.request(`ecologistica-sync-${ownerId}`, () =>
      performSynchronization(ownerId, transport, onConfirmed))
  }
  return performSynchronization(ownerId, transport, onConfirmed)
}
