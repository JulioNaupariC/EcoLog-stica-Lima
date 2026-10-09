import 'fake-indexeddb/auto'
import { ConfirmedReportSnapshotUnavailableError, confirmAcknowledgedReport, confirmReport, enqueueReport, listPendingReports, markAttempt } from './reportQueue'
import type { PendingDriverReport } from '../types/driverReport'
import { loadItinerary, saveItinerary } from './offlineStorage'

const databaseName = 'ecologistica-offline-v1'
const ownerId = '123e4567-e89b-42d3-a456-426614174000'
const otherOwnerId = '223e4567-e89b-42d3-a456-426614174000'
const stopId = '323e4567-e89b-42d3-a456-426614174000'
const operationId = '423e4567-e89b-42d3-a456-426614174000'

function report(overrides: Partial<PendingDriverReport> = {}): PendingDriverReport {
  return {
    operationId,
    ownerId,
    stopId,
    status: 'ENTREGADO',
    createdAt: 1_000,
    attemptCount: 0,
    ...overrides,
  }
}

async function deleteDatabase(): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const request = indexedDB.deleteDatabase(databaseName)
    request.onsuccess = () => resolve()
    request.onerror = () => reject(new Error('No se pudo limpiar IndexedDB de prueba'))
    request.onblocked = () => reject(new Error('IndexedDB de prueba está bloqueado'))
  })
}

async function writeRawSnapshot(snapshot: unknown): Promise<void> {
  const db = await new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open(databaseName, 2)
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(new Error('No se pudo abrir IndexedDB de prueba'))
  })
  try {
    await new Promise<void>((resolve, reject) => {
      const transaction = db.transaction('itineraries', 'readwrite')
      transaction.objectStore('itineraries').put(snapshot, ownerId)
      transaction.oncomplete = () => resolve()
      transaction.onerror = () => reject(new Error('No se pudo escribir el snapshot de prueba'))
    })
  } finally { db.close() }
}

beforeEach(async () => {
  await deleteDatabase()
})

describe('pending report queue', () => {
  it('persists events in creation order and isolates owners', async () => {
    await enqueueReport(report())
    await enqueueReport(report({
      operationId: '523e4567-e89b-42d3-a456-426614174000',
      createdAt: 2_000,
    }))
    await enqueueReport(report({
      operationId: '623e4567-e89b-42d3-a456-426614174000',
      ownerId: otherOwnerId,
    }))

    expect(await listPendingReports(ownerId)).toEqual([
      report(),
      report({ operationId: '523e4567-e89b-42d3-a456-426614174000', createdAt: 2_000 }),
    ])
    expect(await listPendingReports(otherOwnerId)).toEqual([
      report({ operationId: '623e4567-e89b-42d3-a456-426614174000', ownerId: otherOwnerId }),
    ])
  })

  it('does not replace an event on an idempotent local enqueue', async () => {
    await enqueueReport(report())
    await enqueueReport(report({ status: 'NO_ENTREGADO', createdAt: 2_000 }))

    expect(await listPendingReports(ownerId)).toEqual([report()])
  })

  it('increments attempts and removes only the matching owner operation', async () => {
    await enqueueReport(report())
    await enqueueReport(report({
      operationId: '523e4567-e89b-42d3-a456-426614174000',
      ownerId: otherOwnerId,
    }))

    await markAttempt(report())
    await confirmReport(otherOwnerId, operationId)

    expect(await listPendingReports(ownerId)).toEqual([report({ attemptCount: 1 })])
    expect(await listPendingReports(otherOwnerId)).toHaveLength(1)

    await confirmReport(ownerId, operationId)
    expect(await listPendingReports(ownerId)).toEqual([])
  })

  it('rejects invalid event identifiers without opening a queue entry', async () => {
    await expect(enqueueReport(report({ stopId: 'not-a-uuid' }))).rejects.toThrow('Reporte pendiente inválido')
    expect(await listPendingReports(ownerId)).toEqual([])
  })

  it('confirms only the matching event and updates only its owner snapshot', async () => {
    const savedAt = Date.now()
    await saveItinerary({ ownerId, savedAt, expiresAt: savedAt + 60_000,
      stops: [{ stopId, position: 1, status: 'PENDIENTE' }] })
    await saveItinerary({ ownerId: otherOwnerId, savedAt, expiresAt: savedAt + 60_000,
      stops: [{ stopId, position: 1, status: 'PENDIENTE' }] })
    await enqueueReport(report())

    await expect(confirmAcknowledgedReport(report({ ownerId: otherOwnerId }))).rejects.toThrow()
    expect(await listPendingReports(ownerId)).toEqual([report()])
    await confirmAcknowledgedReport(report())

    expect(await listPendingReports(ownerId)).toEqual([])
    expect((await loadItinerary(ownerId))?.stops[0].status).toBe('ENTREGADO')
    expect((await loadItinerary(otherOwnerId))?.stops[0].status).toBe('PENDIENTE')
  })

  it('keeps the same pending operation when the snapshot write cannot complete', async () => {
    await enqueueReport(report())
    await writeRawSnapshot({ ownerId, stops: 'invalid' })

    await expect(confirmAcknowledgedReport(report())).rejects.toBeInstanceOf(ConfirmedReportSnapshotUnavailableError)
    expect(await listPendingReports(ownerId)).toEqual([report()])

    const savedAt = Date.now()
    await saveItinerary({ ownerId, savedAt, expiresAt: savedAt + 60_000,
      stops: [{ stopId, position: 1, status: 'PENDIENTE' }] })
    await confirmAcknowledgedReport(report())
    expect(await listPendingReports(ownerId)).toEqual([])
    expect((await loadItinerary(ownerId))?.stops[0].status).toBe('ENTREGADO')
  })

  it('does not discard an acknowledged report if there is no snapshot to update', async () => {
    await enqueueReport(report())
    await expect(confirmAcknowledgedReport(report())).rejects.toBeInstanceOf(ConfirmedReportSnapshotUnavailableError)
    expect(await listPendingReports(ownerId)).toEqual([report()])
  })

  it('keeps an expired snapshot expired and retries with the same operation after a fresh server snapshot', async () => {
    const savedAt = Date.now() - 120_000
    await enqueueReport(report())
    await writeRawSnapshot({ ownerId, savedAt, expiresAt: savedAt + 60_000,
      stops: [{ stopId, position: 1, status: 'PENDIENTE' }] })

    await expect(confirmAcknowledgedReport(report())).rejects.toBeInstanceOf(ConfirmedReportSnapshotUnavailableError)
    expect(await listPendingReports(ownerId)).toEqual([report()])
    expect(await loadItinerary(ownerId)).toBeNull()

    const freshSavedAt = Date.now()
    await saveItinerary({ ownerId, savedAt: freshSavedAt, expiresAt: freshSavedAt + 60_000,
      stops: [{ stopId, position: 1, status: 'ENTREGADO' }] })
    await confirmAcknowledgedReport(report())
    expect(await listPendingReports(ownerId)).toEqual([])
    expect((await loadItinerary(ownerId))?.stops[0].status).toBe('ENTREGADO')
  })

  it('rolls back both writes when the transaction aborts after put and delete succeed', async () => {
    const savedAt = Date.now()
    await saveItinerary({ ownerId, savedAt, expiresAt: savedAt + 60_000,
      stops: [{ stopId, position: 1, status: 'PENDIENTE' }] })
    await enqueueReport(report())

    const originalPut = Reflect.get(IDBObjectStore.prototype, 'put')
    const originalDelete = Reflect.get(IDBObjectStore.prototype, 'delete')
    let putSucceeded = false
    let deleteSucceeded = false
    let settled: 'pending' | 'resolved' | 'rejected' = 'pending'
    let settlementAtPut = ''
    let settlementAtDelete = ''
    vi.spyOn(IDBObjectStore.prototype, 'put').mockImplementation(function (this: IDBObjectStore, value, key) {
      const request = Reflect.apply(originalPut, this, [value, key])
      if (this.name === 'itineraries') request.addEventListener('success', () => {
        putSucceeded = true
        settlementAtPut = settled
      })
      return request
    })
    vi.spyOn(IDBObjectStore.prototype, 'delete').mockImplementation(function (this: IDBObjectStore, key) {
      const request = Reflect.apply(originalDelete, this, [key])
      if (this.name === 'pendingReports') request.addEventListener('success', () => {
        deleteSucceeded = true
        settlementAtDelete = settled
        this.transaction.abort()
      })
      return request
    })

    try {
      const confirmation = confirmAcknowledgedReport(report())
      const settlement = confirmation.then(
        () => { settled = 'resolved' },
        () => { settled = 'rejected' },
      )
      await expect(confirmation).rejects.toThrow('almacenamiento local')
      await settlement
      expect(putSucceeded).toBe(true)
      expect(deleteSucceeded).toBe(true)
      expect(settlementAtPut).toBe('pending')
      expect(settlementAtDelete).toBe('pending')
      expect(settled).toBe('rejected')
    } finally { vi.restoreAllMocks() }

    expect(await listPendingReports(ownerId)).toEqual([report()])
    expect((await loadItinerary(ownerId))?.stops[0].status).toBe('PENDIENTE')
  })
})
