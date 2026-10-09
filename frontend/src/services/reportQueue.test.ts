import 'fake-indexeddb/auto'
import { confirmReport, enqueueReport, listPendingReports, markAttempt } from './reportQueue'
import type { PendingDriverReport } from '../types/driverReport'

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
})
