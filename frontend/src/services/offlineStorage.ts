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
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

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
  return UUID_PATTERN.test(value)
}

function isItinerarySnapshot(value: unknown): value is ItinerarySnapshot {
  if (typeof value !== 'object' || value === null) return false
  const snapshot = value as Record<string, unknown>
  if (typeof snapshot.ownerId !== 'string' || !validUserId(snapshot.ownerId) ||
      typeof snapshot.savedAt !== 'number' || !Number.isSafeInteger(snapshot.savedAt) ||
      typeof snapshot.expiresAt !== 'number' || !Number.isSafeInteger(snapshot.expiresAt) ||
      snapshot.expiresAt <= snapshot.savedAt || !Array.isArray(snapshot.stops) ||
      snapshot.stops.length > 100) return false

  const stopIds = new Set<string>()
  const positions = new Set<number>()
  return snapshot.stops.every(stop => {
    if (typeof stop !== 'object' || stop === null) return false
    const item = stop as Record<string, unknown>
    const stopId = item.stopId
    const position = item.position
    const status = item.status
    if (typeof stopId !== 'string' || !UUID_PATTERN.test(stopId) ||
        typeof position !== 'number' || !Number.isSafeInteger(position) || position < 1 ||
        typeof status !== 'string' || !['PENDIENTE', 'EN_RUTA', 'ENTREGADO'].includes(status) ||
        stopIds.has(stopId) || positions.has(position)) return false
    stopIds.add(stopId)
    positions.add(position)
    return true
  })
}

function transactionResult<T>(
  db: IDBDatabase,
  mode: IDBTransactionMode,
  task: (store: IDBObjectStore, done: (value: T) => void) => void,
): Promise<T> {
  return new Promise((resolve, reject) => {
    let result: T
    const transaction = db.transaction(STORE_NAME, mode)
    try {
      task(transaction.objectStore(STORE_NAME), value => { result = value })
    } catch (error) {
      transaction.abort()
      reject(error instanceof Error ? error : new Error('No se pudo iniciar la transacción local'))
      return
    }
    transaction.oncomplete = () => resolve(result)
    transaction.onerror = () => reject(new Error('Falló el almacenamiento local'))
    transaction.onabort = () => reject(new Error('Se canceló el almacenamiento local'))
  })
}

export async function saveItinerary(snapshot: ItinerarySnapshot): Promise<void> {
  if (!isItinerarySnapshot(snapshot) || snapshot.expiresAt <= Date.now()) {
    throw new Error('Itinerario local inválido')
  }
  const db = await openDatabase()
  try {
    await transactionResult<void>(db, 'readwrite', (store, done) => {
      const request = store.put(snapshot, snapshot.ownerId)
      request.onsuccess = () => done(undefined)
    })
  }
  finally { db.close() }
}

export async function loadItinerary(ownerId: string): Promise<ItinerarySnapshot | null> {
  if (!validUserId(ownerId)) throw new Error('Identidad inválida')
  const db = await openDatabase()
  try {
    const snapshot = await transactionResult<unknown>(db, 'readonly', (store, done) => {
      const request = store.get(ownerId)
      request.onsuccess = () => done(request.result)
    })
    if (snapshot === undefined) return null
    if (!isItinerarySnapshot(snapshot) || snapshot.ownerId !== ownerId || snapshot.expiresAt <= Date.now()) {
      await transactionResult<void>(db, 'readwrite', (store, done) => {
        const request = store.delete(ownerId)
        request.onsuccess = () => done(undefined)
      })
      return null
    }
    return snapshot
  } finally { db.close() }
}

export async function clearItinerary(ownerId: string): Promise<void> {
  if (!validUserId(ownerId)) throw new Error('Identidad inválida')
  const db = await openDatabase()
  try {
    await transactionResult<void>(db, 'readwrite', (store, done) => {
      const request = store.delete(ownerId)
      request.onsuccess = () => done(undefined)
    })
  }
  finally { db.close() }
}
