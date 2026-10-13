import { useCallback, useEffect, useState } from 'react'
import { CloudUpload, PackageCheck, PackageX } from 'lucide-react'
import { ConnectionStatus } from './ConnectionStatus'
import { Button } from './ui'
import { createPendingReport } from '../types/driverReport'
import type { DriverReportStatus, PendingDriverReport } from '../types/driverReport'
import { enqueueReport, listPendingReports } from '../services/reportQueue'
import { AcknowledgedReportPendingError, synchronizeReports } from '../services/reportSync'
import type { ReportTransport } from '../services/reportSync'
import { REPORTS_CHANGED } from '../hooks/useReportSynchronization'

/**
 * Render only inside the existing CONDUCTOR-authorized itinerary route.
 * - full: report actions, connection, pending count and sync (standalone use).
 * - stop: only the report actions of one stop (itinerary cards).
 * - sync: one page-level block with connection, pending count and sync.
 */
export function OfflineReportPanel({ ownerId, stopId, transport, allowNewReport = true, onConfirmed, variant = 'full', stopLabel }: {
  ownerId: string
  stopId: string
  transport?: ReportTransport
  allowNewReport?: boolean
  onConfirmed?: (report: PendingDriverReport) => void
  variant?: 'full' | 'stop' | 'sync'
  stopLabel?: string
}) {
  const [pending, setPending] = useState<number | null>(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [hasPendingReportForStop, setHasPendingReportForStop] = useState(false)
  const [confirmedForStop, setConfirmedForStop] = useState(false)
  const reload = useCallback(async () => {
    const reports = await listPendingReports(ownerId)
    setPending(reports.length)
    setHasPendingReportForStop(reports.some(report => report.stopId === stopId))
  }, [ownerId, stopId])

  useEffect(() => {
    let active = true
    const refresh = () => { void listPendingReports(ownerId).then(items => {
      if (active) {
        setPending(items.length)
        setHasPendingReportForStop(items.some(report => report.stopId === stopId))
      }
    }).catch(() => {
      if (active) setMessage('No se pudo abrir el almacenamiento local.')
    }) }
    refresh()
    window.addEventListener(REPORTS_CHANGED, refresh)
    return () => { active = false; window.removeEventListener(REPORTS_CHANGED, refresh) }
  }, [ownerId, stopId])

  async function queue(status: DriverReportStatus) {
    if (busy || !allowNewReport || hasPendingReportForStop || confirmedForStop) return
    setBusy(true)
    try {
      await enqueueReport(createPendingReport(ownerId, stopId, status))
      window.dispatchEvent(new Event(REPORTS_CHANGED))
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
      const result = await synchronizeReports(ownerId, transport, report => {
        if (report.stopId === stopId) setConfirmedForStop(true)
        onConfirmed?.(report)
      })
      await reload()
      setMessage(`${result.sent} confirmados por el servidor; ${result.pending} pendientes.`)
      window.dispatchEvent(new Event(REPORTS_CHANGED))
    } catch (error) {
      setMessage(error instanceof AcknowledgedReportPendingError
        ? error.message
        : 'No se pudo comprobar el estado local. Vuelve a abrir el itinerario y sincroniza los pendientes existentes con su mismo identificador.')
    } finally { setBusy(false) }
  }

  const reportActions = variant !== 'sync'
  const syncControls = variant !== 'stop'
  const titleId = `offline-reports-title-${variant === 'sync' ? 'sync' : stopId}`
  const reportDisabled = busy || !allowNewReport || hasPendingReportForStop || confirmedForStop
  return (
    <section aria-labelledby={titleId} className={`report-panel report-panel--${variant}`}>
      {variant === 'stop'
        ? <h4 id={titleId} className="visually-hidden">Reportes de {stopLabel ?? 'la parada'}</h4>
        : <h2 id={titleId} className={variant === 'sync' ? 'card-title' : undefined}>{variant === 'sync' ? 'Sincronización de reportes' : 'Reportes de la parada'}</h2>}
      {syncControls ? <ConnectionStatus /> : null}
      {syncControls ? <p role="status" aria-live="polite" className="report-count">Reportes pendientes: {pending ?? 'consultando…'}</p> : null}
      <div className="report-actions">
        {reportActions ? <>
          <Button icon={PackageCheck} disabled={reportDisabled} onClick={() => { void queue('ENTREGADO') }}>Marcar como entregado</Button>
          <Button variant="secondary" icon={PackageX} disabled={reportDisabled} onClick={() => { void queue('NO_ENTREGADO') }}>Marcar como no entregado</Button>
        </> : null}
        {syncControls ? <Button variant={variant === 'sync' ? 'primary' : 'secondary'} icon={CloudUpload} disabled={busy || !transport} onClick={() => { void sync() }}>Sincronizar pendientes</Button> : null}
      </div>
      {reportActions && hasPendingReportForStop ? (
        <p role="status" className="report-note">Esta parada ya tiene un reporte pendiente. Sincronízalo antes de registrar otro resultado.</p>
      ) : null}
      {syncControls && !transport && <p className="report-note">La sincronización no está configurada para esta vista.</p>}
      {message && <p role="status" aria-live="polite" className="report-note">{message}</p>}
    </section>
  )
}
