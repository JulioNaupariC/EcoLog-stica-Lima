/** Persistent pending-report outbox. Never store tokens or customer PII. */
import { validateReport, validUuid } from '../types/driverReport'
import type { PendingDriverReport } from '../types/driverReport'

const DATABASE = 'ecologistica-offline-v1'
const VERSION = 2
const REPORTS = 'pendingReports'
const MAX_PER_OWNER = 100

function openDb(): Promise<IDBDatabase> {
  if (typeof indexedDB === 'undefined') return Promise.reject(new Error('IndexedDB no disponible'))
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DATABASE, VERSION)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains('itineraries')) db.createObjectStore('itineraries')
      if (!db.objectStoreNames.contains(REPORTS)) db.createObjectStore(REPORTS, { keyPath: 'operationId' })
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(new Error('No se puede abrir IndexedDB'))
    req.onblocked = () => reject(new Error('Cierra las otras pestañas para actualizar IndexedDB'))
  })
}

function inStore<T>(db: IDBDatabase, mode: IDBTransactionMode, operation: (store: IDBObjectStore, done: (value: T) => void) => void): Promise<T> {
  return new Promise((resolve, reject) => {
    let value: T
    const tx = db.transaction(REPORTS, mode)
    try { operation(tx.objectStore(REPORTS), result => { value = result }) }
    catch { tx.abort(); reject(new Error('Operación local inválida')); return }
    tx.oncomplete = () => resolve(value)
    tx.onerror = () => reject(new Error('Error de transacción local'))
    tx.onabort = () => reject(new Error('Transacción local cancelada'))
  })
}

export async function listPendingReports(ownerId: string): Promise<PendingDriverReport[]> {
  if (!validUuid(ownerId)) throw new Error('Identidad inválida')
  const db = await openDb()
  try {
    const reports = await inStore<PendingDriverReport[]>(db, 'readonly', (store, done) => {
      const req = store.getAll()
      req.onsuccess = () => done((req.result as PendingDriverReport[])
        .filter(item => item.ownerId === ownerId)
        .sort((a, b) => a.createdAt - b.createdAt))
    })
    return reports
  } finally { db.close() }
}

export async function enqueueReport(report: PendingDriverReport): Promise<void> {
  validateReport(report)
  const db = await openDb()
  try {
    await inStore<void>(db, 'readwrite', (store, done) => {
      const req = store.getAll()
      req.onsuccess = () => {
        const items = req.result as PendingDriverReport[]
        if (items.some(item => item.operationId === report.operationId)) {
          done(undefined); return // stable retry identifier: never replace an existing report
        }
        if (items.filter(item => item.ownerId === report.ownerId).length >= MAX_PER_OWNER) {
          store.transaction.abort(); return
        }
        const add = store.add(report)
        add.onsuccess = () => done(undefined)
      }
    })
  } finally { db.close() }
}

export async function markAttempt(report: PendingDriverReport): Promise<void> {
  validateReport(report)
  const db = await openDb()
  try {
    await inStore<void>(db, 'readwrite', (store, done) => {
      const req = store.get(report.operationId)
      req.onsuccess = () => {
        const current = req.result as PendingDriverReport | undefined
        if (!current || current.ownerId !== report.ownerId) { done(undefined); return }
        const update = store.put({ ...current, attemptCount: current.attemptCount + 1 })
        update.onsuccess = () => done(undefined)
      }
    })
  } finally { db.close() }
}

export async function confirmReport(ownerId: string, operationId: string): Promise<void> {
  if (!validUuid(ownerId) || !validUuid(operationId)) throw new Error('Identificador inválido')
  const db = await openDb()
  try {
    await inStore<void>(db, 'readwrite', (store, done) => {
      const req = store.get(operationId)
      req.onsuccess = () => {
        const current = req.result as PendingDriverReport | undefined
        if (!current || current.ownerId !== ownerId) { done(undefined); return }
        const removal = store.delete(operationId)
        removal.onsuccess = () => done(undefined)
      }
    })
  } finally { db.close() }
}

/** Must be called on sign-out after the server-side session is invalidated. */
export async function clearPendingReports(ownerId: string): Promise<void> {
  for (const report of await listPendingReports(ownerId)) {
    await confirmReport(ownerId, report.operationId)
  }
}
