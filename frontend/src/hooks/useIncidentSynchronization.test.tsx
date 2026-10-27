import { act, renderHook, waitFor } from '@testing-library/react'
import { useIncidentSynchronization } from './useIncidentSynchronization'
import { listIncidents, updateIncident } from '../services/incidentStorage'
import { INCIDENTS_CHANGED, synchronizeIncidents } from '../services/incidentSync'
import type { StoredIncident } from '../domain/incident'

vi.mock('../services/incidentStorage', () => ({ listIncidents: vi.fn(), updateIncident: vi.fn() }))
vi.mock('../services/incidentSync', () => ({ INCIDENTS_CHANGED: 'incidents-test', synchronizeIncidents: vi.fn() }))
beforeEach(() => {
  vi.mocked(listIncidents).mockReset().mockResolvedValue([])
  vi.mocked(updateIncident).mockReset().mockResolvedValue()
  vi.mocked(synchronizeIncidents).mockReset().mockResolvedValue()
})
afterEach(() => { vi.useRealTimers() })

it('ruta de borde: reautenticación del mismo propietario reanuda 401, no 403/409/422', async () => {
  const entries = [401, 403, 409, 422].map(errorStatus => ({ errorStatus })) as StoredIncident[]
  vi.mocked(listIncidents).mockResolvedValue(entries)
  renderHook(() => useIncidentSynchronization('owner-A'))
  await waitFor(() => expect(synchronizeIncidents).toHaveBeenCalledTimes(1))
  expect(updateIncident).toHaveBeenCalledExactlyOnceWith({ errorStatus: undefined })
})
it('ruta de borde: navegación sin propietario no sincroniza; cambiar cuenta cancela la anterior', async () => {
  const view = renderHook(({ owner }) => useIncidentSynchronization(owner), { initialProps: { owner: undefined as string | undefined } })
  expect(listIncidents).not.toHaveBeenCalled()
  view.rerender({ owner: 'owner-A' })
  await waitFor(() => expect(synchronizeIncidents).toHaveBeenCalledTimes(1))
  const previous = vi.mocked(synchronizeIncidents).mock.calls[0][1]
  view.rerender({ owner: 'owner-B' })
  expect(previous.aborted).toBe(true)
  await waitFor(() => expect(synchronizeIncidents).toHaveBeenCalledTimes(2))
  const current = vi.mocked(synchronizeIncidents).mock.calls[1][1]
  view.unmount(); expect(current.aborted).toBe(true)
})
it('ruta de borde: reconexión, aviso local y sondeo reintentan sin solaparse', async () => {
  const view = renderHook(() => useIncidentSynchronization('owner-A'))
  await waitFor(() => expect(synchronizeIncidents).toHaveBeenCalledTimes(1))
  await act(async () => { window.dispatchEvent(new Event('online')); await Promise.resolve() })
  await act(async () => { window.dispatchEvent(new Event(INCIDENTS_CHANGED)); await Promise.resolve() })
  expect(synchronizeIncidents).toHaveBeenCalledTimes(3)
  view.unmount()
  await act(async () => { window.dispatchEvent(new Event('online')); await Promise.resolve() })
  expect(synchronizeIncidents).toHaveBeenCalledTimes(3)
})
it('ruta infeliz: error de persistencia al recuperar sesión no produce envío', async () => {
  vi.mocked(listIncidents).mockRejectedValue(new Error('almacenamiento bloqueado'))
  renderHook(() => useIncidentSynchronization('owner-A'))
  await act(async () => { await Promise.resolve() })
  expect(synchronizeIncidents).not.toHaveBeenCalled()
})
