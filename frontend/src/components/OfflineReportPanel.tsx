import { useCallback, useEffect, useState } from 'react'
import { ConnectionStatus } from './ConnectionStatus'
import { createPendingReport } from '../types/driverReport'
import type { DriverReportStatus } from '../types/driverReport'
import { enqueueReport, listPendingReports } from '../services/reportQueue'
import { synchronizeReports } from '../services/reportSync'
import type { ReportTransport } from '../services/reportSync'

/** Embed ONLY inside the existing CONDUCTOR-authorized route after ST-030 is merged. */
export function OfflineReportPanel({ ownerId, stopId, transport }: {
  ownerId: string
  stopId: string
  transport?: ReportTransport
}) {
  const [pending, setPending] = useState<number | null>(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const reload = useCallback(async () => {
    setPending((await listPendingReports(ownerId)).length)
  }, [ownerId])

  useEffect(() => {
    let active = true
    void listPendingReports(ownerId).then(items => {
      if (active) setPending(items.length)
    }).catch(() => {
      if (active) setMessage('No se pudo abrir el almacenamiento local.')
    })
    return () => { active = false }
  }, [ownerId])

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
    <section aria-labelledby="offline-reports-title">
      <h2 id="offline-reports-title">Reportes de la parada</h2>
      <ConnectionStatus />
      <p role="status" aria-live="polite">Reportes pendientes: {pending ?? 'consultando…'}</p>
      <div className="offline-report-actions">
        <button type="button" disabled={busy} onClick={() => { void queue('ENTREGADO') }}>Registrar entrega pendiente</button>
        <button type="button" disabled={busy} onClick={() => { void queue('NO_ENTREGADO') }}>Registrar no entregado</button>
        <button type="button" disabled={busy || !transport} onClick={() => { void sync() }}>Sincronizar pendientes</button>
      </div>
      {!transport && <p>Sincronización con servidor pendiente: falta el endpoint autenticado e idempotente.</p>}
      {message && <p role="status" aria-live="polite">{message}</p>}
    </section>
  )
}
