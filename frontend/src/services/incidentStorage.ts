import type { IncidentDraft, IncidentPayload, StoredIncident } from '../domain/incident'
import { validUuid } from '../types/driverReport'

// Independent database: never upgrades or deletes the Sprint 2 itinerary/outbox.
const DATABASE = 'ecologistica-incidents-v1'
type StoreName = 'drafts' | 'incidents'

async function transaction<T>(name: StoreName | StoreName[], mode: IDBTransactionMode,
  operation: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open(DATABASE, 1)
    request.onupgradeneeded = () => {
      request.result.createObjectStore('drafts')
      request.result.createObjectStore('incidents', { keyPath: ['ownerId', 'payload.operation_id'] })
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = request.onblocked = () => reject(new Error('No se pudo abrir el almacenamiento de incidencias.'))
  })
  try {
    return await new Promise<T>((resolve, reject) => {
      const tx = db.transaction(name, mode)
      const request = operation(tx.objectStore(Array.isArray(name) ? name[0] : name))
      tx.oncomplete = () => resolve(request.result)
      tx.onerror = tx.onabort = () => reject(new Error('No se pudo guardar en este dispositivo.'))
    })
  } finally { db.close() }
}
function ownerKey(ownerId: string): string {
  if (!validUuid(ownerId)) throw new Error('Identidad inválida.')
  return ownerId
}
export async function loadIncidentDraft(ownerId: string): Promise<IncidentDraft | undefined> {
  return transaction('drafts', 'readonly', store => store.get(ownerKey(ownerId)) as IDBRequest<IncidentDraft | undefined>)
}
export async function saveIncidentDraft(ownerId: string, draft: IncidentDraft): Promise<void> {
  // Explicit projection excludes credentials and accidental identity/contact fields.
  const { tipo, severidad, ocurrida_en, ubicacion, observacion, operation_id } = draft
  await transaction('drafts', 'readwrite', store => store.put(
    { tipo, severidad, ocurrida_en, ubicacion, observacion, operation_id }, ownerKey(ownerId)))
}
export async function removeIncidentDraft(ownerId: string): Promise<void> {
  await transaction('drafts', 'readwrite', store => store.delete(ownerKey(ownerId)))
}
export async function listIncidents(ownerId: string): Promise<StoredIncident[]> {
  const owner = ownerKey(ownerId)
  const items = await transaction('incidents', 'readonly', store => store.getAll() as IDBRequest<StoredIncident[]>)
  return items.filter(item => item.ownerId === owner).sort((a, b) => a.createdAt - b.createdAt)
}
export async function enqueueIncident(incident: StoredIncident): Promise<void> {
  ownerKey(incident.ownerId)
  // add, never put: a repeated key must not silently replace its original content.
  await transaction(['incidents', 'drafts'], 'readwrite', store => {
    const request = store.add(incident)
    store.transaction.objectStore('drafts').delete(incident.ownerId)
    return request
  })
}
export async function updateIncident(incident: StoredIncident): Promise<void> {
  ownerKey(incident.ownerId)
  await transaction('incidents', 'readwrite', store => store.put(incident))
}

/** Only a rejected, unregistered 422 may change content under its original key. */
export async function correctRejectedIncident(ownerId: string, payload: IncidentPayload): Promise<void> {
  ownerKey(ownerId)
  await transaction(['incidents', 'drafts'], 'readwrite', store => {
    const request = store.get([ownerId, payload.operation_id]) as IDBRequest<StoredIncident | undefined>
    request.onsuccess = () => {
      const previous = request.result
      if (!previous || previous.errorStatus !== 422 || previous.acknowledgement) {
        store.transaction.abort(); return
      }
      store.put({ ...previous, payload, errorStatus: undefined })
      store.transaction.objectStore('drafts').delete(ownerId)
    }
    return request
  })
}
