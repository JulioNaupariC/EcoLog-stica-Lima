import { getDriverItinerary, DriverItineraryServiceError } from './driverItinerary'
import { listIncidents, updateIncident } from './incidentStorage'
import { sendIncident, IncidentServiceError } from './incidents'

export const INCIDENTS_CHANGED = 'ecologistica-incidents-changed'
const running = new Set<string>()
export const isSynchronizingIncidents = (ownerId: string) => running.has(ownerId)

export function notifyIncidentsChanged() {
  window.dispatchEvent(new Event(INCIDENTS_CHANGED))
}

async function synchronize(ownerId: string, signal: AbortSignal, manual: boolean) {
  if (running.has(ownerId) || signal.aborted || !navigator.onLine) return
  running.add(ownerId)
  notifyIncidentsChanged()
  try {
    for (const incident of await listIncidents(ownerId)) {
      if (signal.aborted || incident.acknowledgement) continue
      if (incident.errorStatus && (!manual || incident.errorStatus === 401 || incident.errorStatus === 409)) continue
      try {
        // Cookie may belong to another account in another tab. Verify the owner
        // against the API before each send, as in the Sprint 2 coordinator.
        await getDriverItinerary(ownerId, signal)
        if (signal.aborted) return
        const acknowledgement = await sendIncident(incident.payload, ownerId, signal)
        await updateIncident({ ...incident, errorStatus: undefined, acknowledgement })
      } catch (error) {
        if (signal.aborted) return
        const status = error instanceof IncidentServiceError || error instanceof DriverItineraryServiceError
          ? error.status : undefined
        if (status && status >= 400 && status < 500) {
          await updateIncident({ ...incident, errorStatus: status })
          if (status === 401) break
        } else break // Timeout/5xx/response loss: preserve key + exact payload.
      }
    }
  } finally { running.delete(ownerId); notifyIncidentsChanged() }
}

export async function synchronizeIncidents(ownerId: string, signal: AbortSignal, manual = false) {
  if (navigator.locks) {
    await navigator.locks.request(`ecologistica-incidents-${ownerId}`, { signal },
      () => synchronize(ownerId, signal, manual))
  } else await synchronize(ownerId, signal, manual)
}
