import { useCallback, useEffect, useState } from 'react'
import { ConnectionStatus } from './ConnectionStatus'
import { createPendingReport } from '../types/driverReport'
import type { DriverReportStatus } from '../types/driverReport'
import { enqueueReport, listPendingReports } from '../services/reportQueue'
import { synchronizeReports } from '../services/reportSync'
import type { ReportTransport } from '../services/reportSync'

/** Render only inside the existing CONDUCTOR-authorized itinerary route. */
export function OfflineReportPanel({ ownerId, stopId, transport, allowNewReport = true }: {
  ownerId: string
  stopId: string
  transport?: ReportTransport
  allowNewReport?: boolean
}) {
  const [pending, setPending] = useState<number | null>(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [hasPendingReportForStop, setHasPendingReportForStop] = useState(false)
  const reload = useCallback(async () => {
    const reports = await listPendingReports(ownerId)
    setPending(reports.length)
    setHasPendingReportForStop(reports.some(report => report.stopId === stopId))
  }, [ownerId, stopId])

  useEffect(() => {
    let active = true
    void listPendingReports(ownerId).then(items => {
      if (active) {
        setPending(items.length)
        setHasPendingReportForStop(items.some(report => report.stopId === stopId))
      }
    }).catch(() => {
      if (active) setMessage('No se pudo abrir el almacenamiento local.')
    })
    return () => { active = false }
  }, [ownerId, stopId])

  async function queue(status: DriverReportStatus) {
    if (busy) return
    setBusy(true)
    try {
      await enqueueReport(createPendingReport(ownerId, stopId, status))
      await reload()
      setMessage('Reporte guardado en este dispositivo; aún no se envió al servidor.')
    } catch {
      setMessage('No se pudo guardar el reporte. Intenta nuevamente.')
    } finally { setBusy(false) }
  }

  async function sync() {
    if (!transport || busy) return
    setBusy(true)
    try {
      const result = await synchronizeReports(ownerId, transport)
      setPending(result.pending)
      setMessage(`${result.sent} confirmados por el servidor; ${result.pending} pendientes.`)
    } catch {
      setMessage('Sincronización no disponible. Los reportes se conservaron localmente.')
    } finally { setBusy(false) }
  }

  return (
    <section aria-labelledby={`offline-reports-title-${stopId}`}>
      <h2 id={`offline-reports-title-${stopId}`}>Reportes de la parada</h2>
      <ConnectionStatus />
      <p role="status" aria-live="polite">Reportes pendientes: {pending ?? 'consultando…'}</p>
      <div className="offline-report-actions">
        <button type="button" disabled={busy || !allowNewReport || hasPendingReportForStop} onClick={() => { void queue('ENTREGADO') }}>Registrar entrega pendiente</button>
        <button type="button" disabled={busy || !allowNewReport || hasPendingReportForStop} onClick={() => { void queue('NO_ENTREGADO') }}>Registrar no entregado</button>
        <button type="button" disabled={busy || !transport} onClick={() => { void sync() }}>Sincronizar pendientes</button>
      </div>
      {hasPendingReportForStop ? (
        <p role="status">Esta parada ya tiene un reporte pendiente. Sincronízalo antes de registrar otro resultado.</p>
      ) : null}
      {!transport && <p>La sincronización no está configurada para esta vista.</p>}
      {message && <p role="status" aria-live="polite">{message}</p>}
    </section>
  )
}
