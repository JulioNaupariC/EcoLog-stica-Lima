import { useEffect } from 'react'
import { INCIDENTS_CHANGED, synchronizeIncidents } from '../services/incidentSync'
import { listIncidents, updateIncident } from '../services/incidentStorage'

/** Mounted once per authenticated driver, survives navigation between pages. */
export function useIncidentSynchronization(ownerId: string | undefined) {
  useEffect(() => {
    if (!ownerId) return
    const controller = new AbortController()
    let running = false
    const attempt = () => {
      if (running || controller.signal.aborted) return
      running = true
      void synchronizeIncidents(ownerId, controller.signal).catch(() => {
        // The page displays persistence errors; no false acknowledgement.
      }).finally(() => { running = false })
    }
    // A new authenticated session may resume a previous 401 for the same owner.
    void listIncidents(ownerId).then(async items => {
      for (const item of items) {
        if (item.errorStatus === 401 && !controller.signal.aborted) {
          await updateIncident({ ...item, errorStatus: undefined })
        }
      }
      attempt()
    }).catch(() => { /* Storage failure is visible on the form. */ })
    const timer = setInterval(attempt, 15_000)
    window.addEventListener('online', attempt)
    window.addEventListener(INCIDENTS_CHANGED, attempt)
    return () => {
      controller.abort(); clearInterval(timer)
      window.removeEventListener('online', attempt)
      window.removeEventListener(INCIDENTS_CHANGED, attempt)
    }
  }, [ownerId])
}
