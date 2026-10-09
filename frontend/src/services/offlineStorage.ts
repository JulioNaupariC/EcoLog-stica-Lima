/**
 * ST-032 - Minimal offline itinerary snapshot store.
 * No credentials, DNI, phone numbers or personal customer details are stored.
 * IndexedDB is scoped by verified user UUID and a snapshot may expire.
 * This is NOT the pending-report queue or the synchronization implementation.
 */
export type StopSummary = {
  stopId: string
  position: number
  status: 'PENDIENTE' | 'EN_RUTA' | 'ENTREGADO'
}

export type ItinerarySnapshot = {
  ownerId: string
  savedAt: number
  expiresAt: number
  stops: StopSummary[]
}

const DB_NAME = 'ecologistica-offline-v1'
const DB_VERSION = 2
const STORE_NAME = 'itineraries'

function openDatabase(): Promise<IDBDatabase> {
  if (typeof indexedDB === 'undefined') return Promise.reject(new Error('IndexedDB no disponible'))
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE_NAME)) db.createObjectStore(STORE_NAME)
      if (!db.objectStoreNames.contains("pendingReports")) db.createObjectStore("pendingReports", { keyPath: "operationId" })
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(new Error('No se pudo abrir el almacenamiento local'))
    request.onblocked = () => reject(new Error('La base local está bloqueada por otra pestaña'))
  })
}

function validUserId(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
}

function transactionResult<T>(db: IDBDatabase, mode: IDBTransactionMode, task: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    let result!: T
    const transaction = db.transaction(STORE_NAME, mode)
    const request = task(transaction.objectStore(STORE_NAME))
    request.onsuccess = () => {
      result = request.result
    }
    request.onerror = () => { /* transaction error below */ }
    transaction.oncomplete = () => resolve(result)
    transaction.onerror = () => reject(new Error('Falló el almacenamiento local'))
    transaction.onabort = () => reject(new Error('Se canceló el almacenamiento local'))
  })
}

export async function saveItinerary(snapshot: ItinerarySnapshot): Promise<void> {
  if (!validUserId(snapshot.ownerId) || !Number.isFinite(snapshot.savedAt) ||
      !Number.isFinite(snapshot.expiresAt) || snapshot.expiresAt <= snapshot.savedAt ||
      snapshot.expiresAt <= Date.now() || !Array.isArray(snapshot.stops) ||
      snapshot.stops.length > 100 || snapshot.stops.some(stop =>
        !stop.stopId || !Number.isInteger(stop.position) || stop.position < 1 ||
        !['PENDIENTE', 'EN_RUTA', 'ENTREGADO'].includes(stop.status))) {
    throw new Error('Itinerario local inválido')
  }
  const db = await openDatabase()
  try {
    await transactionResult<unknown>(db, 'readwrite', (store: IDBObjectStore): IDBRequest<unknown> =>
      store.put(snapshot, snapshot.ownerId) as IDBRequest<unknown>,
    )
  } finally { db.close() }
}

export async function loadItinerary(ownerId: string): Promise<ItinerarySnapshot | null> {
  if (!validUserId(ownerId)) throw new Error('Identidad inválida')
  const db = await openDatabase()
  try {
    const snapshot = await transactionResult<ItinerarySnapshot | undefined>(db, 'readonly', (store: IDBObjectStore): IDBRequest<ItinerarySnapshot | undefined> =>
      store.get(ownerId) as IDBRequest<ItinerarySnapshot | undefined>,
    )
    if (!snapshot) return null
    if (snapshot.ownerId !== ownerId || snapshot.expiresAt <= Date.now()) {
      await transactionResult<unknown>(db, 'readwrite', (store: IDBObjectStore): IDBRequest<unknown> =>
        store.delete(ownerId) as IDBRequest<unknown>,
      )
      return null
    }
    return snapshot
  } finally { db.close() }
}

export async function clearItinerary(ownerId: string): Promise<void> {
  if (!validUserId(ownerId)) throw new Error('Identidad inválida')
  const db = await openDatabase()
  try {
    await transactionResult<unknown>(db, 'readwrite', (store: IDBObjectStore): IDBRequest<unknown> =>
      store.delete(ownerId) as IDBRequest<unknown>,
    )
  } finally { db.close() }
}
