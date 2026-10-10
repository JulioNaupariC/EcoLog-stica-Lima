import { useEffect, useState } from 'react'
import { synchronizeReports } from '../services/reportSync'
import { driverReportTransport } from '../services/driverItinerary'
import { listPendingReports } from '../services/reportQueue'
import type { PendingDriverReport } from '../types/driverReport'

export const REPORTS_CHANGED = 'ecologistica-reports-changed'

/** One coordinator per itinerary, not one per stop. Timers stop on unmount/offline. */
export function useReportSynchronization(
  ownerId: string | undefined,
  ready: boolean,
  verify: () => Promise<boolean>,
  onConfirmed: (report: PendingDriverReport) => void,
): string {
  const [message, setMessage] = useState('')
  useEffect(() => {
    if (!ownerId || !ready) return
    let active = true, running = false, delay = 2000
    let timer: ReturnType<typeof setTimeout> | undefined
    async function attempt() {
      if (!active || running || !navigator.onLine) return
      running = true
      setMessage('Comprobando conexión y reportes pendientes…')
      try {
        if (!await verify() || !active) return
        const result = await synchronizeReports(ownerId!, driverReportTransport, report => {
          if (active) onConfirmed(report)
        })
        window.dispatchEvent(new Event(REPORTS_CHANGED))
        if (active) {
          setMessage(`${result.sent} confirmados automáticamente; ${result.pending} pendientes.`)
          if (result.pending) retry()
        }
      } catch {
        if (active) {
          setMessage('Sincronización pendiente. Se reintentará cuando el servicio esté disponible.')
          retry()
        }
      } finally { running = false }
    }
    function retry() {
      if (!active || !navigator.onLine) return
      clearTimeout(timer)
      timer = setTimeout(() => { void attempt() }, delay)
      delay = Math.min(delay * 2, 60_000)
    }
    function online() { delay = 2000; clearTimeout(timer); void attempt() }
    function offline() { clearTimeout(timer); setMessage('Sin conexión: los reportes permanecen pendientes.') }
    window.addEventListener('online', online)
    window.addEventListener('offline', offline)
    // Delay avoids competing with the initial authenticated itinerary fetch.
    void listPendingReports(ownerId).then(reports => {
      if (active && reports.length) timer = setTimeout(() => { void attempt() }, 500)
    }).catch(() => { if (active) retry() })
    return () => {
      active = false; clearTimeout(timer)
      window.removeEventListener('online', online)
      window.removeEventListener('offline', offline)
    }
  }, [ownerId, ready, verify, onConfirmed])
  return message
}
