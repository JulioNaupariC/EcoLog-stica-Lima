import { attendanceTime, isAwareInstant, limaDateTimeInput } from '../domain/routeOutcomes'
import { routeOutcomesApi } from './routeOutcomes'

const routeId = '123e4567-e89b-42d3-a456-426614174001', stopId = '123e4567-e89b-42d3-a456-426614174002'
const now = Date.parse('2026-11-16T15:30:00Z'), time = '2026-11-16T10:30:00-05:00'
const attended = { estado: 'ATENDIDA', atendida_en: time } as const
const updated = { ruta_id: routeId, parada_id: stopId, estado: 'ATENDIDA', atendida_en: time, ruta_estado: 'EN_CURSO' }
const closed = { ruta_id: routeId, estado: 'CERRADA', cerrada_en: time, paradas_atendidas: 1, paradas_no_atendidas: 1 }
const signal = () => new AbortController().signal
const reply = (body: unknown, status = 200) => vi.mocked(fetch).mockImplementation(() => Promise.resolve(new Response(JSON.stringify(body), { status })))
beforeEach(() => { vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000'); vi.stubGlobal('fetch', vi.fn()) })
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs() })

it('convierte explícitamente Lima, acepta medianoche y ahora, sin depender de la zona del equipo', () => {
  expect(limaDateTimeInput(now)).toBe('2026-11-16T10:30:00')
  expect(attendanceTime('2026-11-16T10:30', '2026-11-16', now)).toBe(time)
  expect(attendanceTime('2026-11-16T00:00:00', '2026-11-16', now)).toBe('2026-11-16T00:00:00-05:00')
  expect(attendanceTime('2026-11-16T10:30:00', '2026-11-15', now)).toBe(time)
})
it.each(['', '2026-02-30T10:00', '2026-11-16T24:00', '2026-11-16T10:60', '2026-11-16T10:30:60', '2026-11-16T10:31', '2026-11-15T23:59:59'])('rechaza hora inválida, futura o anterior a jornada: %s', value => {
  expect(() => attendanceTime(value, '2026-11-16', now)).toThrow()
})
it('requiere instante con zona y fecha de operación válida', () => {
  expect(isAwareInstant('2026-11-16T10:30:00')).toBe(false)
  expect(isAwareInstant('2026-02-30T10:30:00Z')).toBe(false)
  expect(() => attendanceTime('2026-11-16T10:30', 'bad-date', now)).toThrow()
})
it('PATCH envía hora real con cookie, no-store y abort; valida el acuse', async () => {
  reply(updated)
  expect(await routeOutcomesApi.record(routeId, stopId, attended, signal())).toEqual(updated)
  expect(fetch).toHaveBeenCalledWith(`http://127.0.0.1:8000/rutas/${routeId}/paradas/${stopId}`, expect.objectContaining({
    method: 'PATCH', credentials: 'include', cache: 'no-store', body: JSON.stringify(attended), headers: { 'Content-Type': 'application/json' }, signal: expect.any(AbortSignal) as AbortSignal,
  }))
})
it('NO_ATENDIDA no envía una hora residual del formulario', async () => {
  reply({ ...updated, estado: 'NO_ATENDIDA', atendida_en: null })
  await routeOutcomesApi.record(routeId, stopId, { estado: 'NO_ATENDIDA', atendida_en: time } as { estado: 'NO_ATENDIDA' }, signal())
  expect(vi.mocked(fetch).mock.calls[0][1]?.body).toBe('{"estado":"NO_ATENDIDA"}')
})
it('POST cierre sin payload arbitrario preserva conteos, hora e idempotencia del API', async () => {
  reply(closed)
  expect(await routeOutcomesApi.close(routeId, signal())).toEqual(closed)
  expect(await routeOutcomesApi.close(routeId, signal())).toEqual(closed)
  expect(fetch).toHaveBeenCalledWith(`http://127.0.0.1:8000/rutas/${routeId}/cierre`, expect.objectContaining({ method: 'POST', credentials: 'include', cache: 'no-store' }))
  expect(vi.mocked(fetch).mock.calls[0][1]?.body).toBeUndefined()
})
it.each([[401, 'unauthorized'], [403, 'forbidden'], [404, 'not_found'], [409, 'conflict'], [422, 'invalid'], [503, 'unavailable']])('clasifica HTTP %s sin mostrar detalle arbitrario', async (status, kind) => {
  reply({ detail: 'PRIVATE_DETAIL' }, Number(status))
  await expect(routeOutcomesApi.record(routeId, stopId, attended, signal())).rejects.toMatchObject({ kind })
  await expect(routeOutcomesApi.close(routeId, signal())).rejects.not.toThrow('PRIVATE_DETAIL')
})
it.each(['La ruta ya está cerrada', 'La parada ya tiene un resultado final', 'Faltan 3 paradas por registrar', 'La ruta no tiene referencia secuencial; vuelve a optimizar la jornada'])('409 conserva un motivo seguro: %s', detail => {
  reply({ detail }, 409)
  return expect(routeOutcomesApi.close(routeId, signal())).rejects.toThrow(detail)
})
it.each(['La hora de atención no puede ser futura', 'La hora de atención es anterior a la jornada de la ruta'])('422 de hora identifica campo sin eco de valores: %s', motivo => {
  reply({ detail: { campo: 'atendida_en', motivo } }, 422)
  return expect(routeOutcomesApi.record(routeId, stopId, attended, signal())).rejects.toMatchObject({ kind: 'invalid', field: 'atendida_en', message: motivo })
})
it('422 no refleja mensajes o campos arbitrarios', async () => {
  reply({ detail: { campo: 'atendida_en', motivo: 'PRIVATE_DETAIL' } }, 422)
  await expect(routeOutcomesApi.record(routeId, stopId, attended, signal())).rejects.not.toThrow('PRIVATE_DETAIL')
})
it.each([
  null, [], { ...updated, ruta_id: stopId }, { ...updated, parada_id: routeId }, { ...updated, estado: 'PENDIENTE' },
  { ...updated, ruta_estado: 'PLANIFICADA' }, { ...updated, atendida_en: null }, { ...updated, atendida_en: '2026-11-16T10:31:00-05:00' },
])('rechaza acuse de otra ruta, parcial o incoherente: %#', body => {
  reply(body)
  return expect(routeOutcomesApi.record(routeId, stopId, attended, signal())).rejects.toMatchObject({ kind: 'unavailable' })
})
it('no admite una hora para NO_ATENDIDA en el acuse', () => {
  reply({ ...updated, estado: 'NO_ATENDIDA' })
  return expect(routeOutcomesApi.record(routeId, stopId, { estado: 'NO_ATENDIDA' }, signal())).rejects.toMatchObject({ kind: 'unavailable' })
})
it.each([{ ...closed, ruta_id: stopId }, { ...closed, estado: 'EN_CURSO' }, { ...closed, cerrada_en: null }, { ...closed, paradas_atendidas: -1 }, { ...closed, paradas_no_atendidas: 1.5 }])('rechaza un cierre incoherente: %#', body => {
  reply(body)
  return expect(routeOutcomesApi.close(routeId, signal())).rejects.toMatchObject({ kind: 'unavailable' })
})
it('no envía IDs ni instantes inválidos', async () => {
  await expect(routeOutcomesApi.record('bad', stopId, attended, signal())).rejects.toMatchObject({ kind: 'invalid' })
  await expect(routeOutcomesApi.record(routeId, 'bad', attended, signal())).rejects.toMatchObject({ kind: 'invalid' })
  await expect(routeOutcomesApi.record(routeId, stopId, { ...attended, atendida_en: 'bad' }, signal())).rejects.toMatchObject({ kind: 'invalid' })
  await expect(routeOutcomesApi.close('bad', signal())).rejects.toMatchObject({ kind: 'invalid' })
  expect(fetch).not.toHaveBeenCalled()
})
it('red, cuerpo ilegible y aborto se distinguen sin fingir éxito', async () => {
  vi.mocked(fetch).mockRejectedValueOnce(new Error('PRIVATE'))
  await expect(routeOutcomesApi.close(routeId, signal())).rejects.toMatchObject({ kind: 'unavailable' })
  vi.mocked(fetch).mockResolvedValueOnce(new Response('not-json'))
  await expect(routeOutcomesApi.close(routeId, signal())).rejects.toMatchObject({ kind: 'unavailable' })
  vi.mocked(fetch).mockResolvedValueOnce(new Response('', { status: 401 }))
  await expect(routeOutcomesApi.close(routeId, signal())).rejects.toMatchObject({ kind: 'unauthorized' })
  const controller = new AbortController(); controller.abort()
  const aborted = new DOMException('Aborted', 'AbortError'); vi.mocked(fetch).mockRejectedValueOnce(aborted)
  await expect(routeOutcomesApi.close(routeId, controller.signal)).rejects.toBe(aborted)
})
