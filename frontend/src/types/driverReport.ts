/** Minimal operational event; do not include customer name, address, DNI or credentials. */
export type DriverReportStatus = 'ENTREGADO' | 'NO_ENTREGADO'

export type PendingDriverReport = {
  operationId: string
  ownerId: string
  stopId: string
  status: DriverReportStatus
  createdAt: number
  attemptCount: number
}

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export function validUuid(value: unknown): value is string {
  return typeof value === 'string' && UUID_PATTERN.test(value)
}

export function validateReport(report: PendingDriverReport): void {
  if (!validUuid(report.ownerId) || !validUuid(report.operationId) ||
      !validUuid(report.stopId) ||
      !['ENTREGADO', 'NO_ENTREGADO'].includes(report.status) ||
      !Number.isSafeInteger(report.createdAt) || report.createdAt <= 0 ||
      !Number.isSafeInteger(report.attemptCount) || report.attemptCount < 0) {
    throw new Error('Reporte pendiente inválido')
  }
}

export function createPendingReport(ownerId: string, stopId: string, status: DriverReportStatus): PendingDriverReport {
  const report: PendingDriverReport = {
    operationId: crypto.randomUUID(), ownerId, stopId, status,
    createdAt: Date.now(), attemptCount: 0,
  }
  validateReport(report)
  return report
}
