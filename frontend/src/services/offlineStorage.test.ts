import 'fake-indexeddb/auto'
import { clearItinerary, loadItinerary, saveItinerary } from './offlineStorage'
import type { ItinerarySnapshot } from './offlineStorage'

const databaseName = 'ecologistica-offline-v1'
const ownerId = '123e4567-e89b-42d3-a456-426614174000'
const otherOwnerId = '223e4567-e89b-42d3-a456-426614174000'
const stopId = '323e4567-e89b-42d3-a456-426614174000'

function snapshot(overrides: Partial<ItinerarySnapshot> = {}): ItinerarySnapshot {
  const savedAt = Date.now()
  return {
    ownerId,
    savedAt,
    expiresAt: savedAt + 60_000,
    stops: [{ stopId, position: 1, status: 'PENDIENTE' }],
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

describe('offline itinerary storage', () => {
  it('saves and loads only the snapshot for the requested owner', async () => {
    const itinerary = snapshot()
    await saveItinerary(itinerary)
    expect(await loadItinerary(ownerId)).toEqual(itinerary)
    expect(await loadItinerary(otherOwnerId)).toBeNull()
  })

  it('clears only the requested owner itinerary', async () => {
    await saveItinerary(snapshot())
    await saveItinerary(snapshot({ ownerId: otherOwnerId }))

    await clearItinerary(ownerId)

    expect(await loadItinerary(ownerId)).toBeNull()
    expect(await loadItinerary(otherOwnerId)).not.toBeNull()
  })

  it('rejects malformed UUIDs, stops, and duplicate itinerary positions', async () => {
    await expect(saveItinerary(snapshot({ ownerId: 'not-a-uuid' }))).rejects.toThrow('Itinerario local inválido')
    await expect(saveItinerary(snapshot({
      stops: [{ stopId: 'fake-stop', position: 1, status: 'PENDIENTE' }],
    }))).rejects.toThrow('Itinerario local inválido')
    await expect(saveItinerary(snapshot({
      stops: [
        { stopId, position: 1, status: 'PENDIENTE' },
        { stopId: '423e4567-e89b-42d3-a456-426614174000', position: 1, status: 'EN_RUTA' },
      ],
    }))).rejects.toThrow('Itinerario local inválido')
  })

  it('upgrades version 1 without losing the itinerary store', async () => {
    const stored = snapshot()
    const legacyDb = await new Promise<IDBDatabase>((resolve, reject) => {
      const request = indexedDB.open(databaseName, 1)
      request.onupgradeneeded = () => request.result.createObjectStore('itineraries')
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(new Error('No se pudo crear la base legada'))
    })

    await new Promise<void>((resolve, reject) => {
      const transaction = legacyDb.transaction('itineraries', 'readwrite')
      transaction.objectStore('itineraries').put(stored, ownerId)
      transaction.oncomplete = () => resolve()
      transaction.onerror = () => reject(new Error('No se pudo guardar itinerario legado'))
    })
    legacyDb.close()

    expect(await loadItinerary(ownerId)).toEqual(stored)
    const upgradedDb = await new Promise<IDBDatabase>((resolve, reject) => {
      const request = indexedDB.open(databaseName, 2)
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(new Error('No se pudo abrir la base actualizada'))
    })
    expect(upgradedDb.objectStoreNames.contains('itineraries')).toBe(true)
    expect(upgradedDb.objectStoreNames.contains('pendingReports')).toBe(true)
    upgradedDb.close()
  })
})
