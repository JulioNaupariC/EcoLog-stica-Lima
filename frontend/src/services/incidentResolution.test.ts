import { pendingIncident as incident } from '../test/incidentFixtures'
import { IncidentResolutionError, resolveIncident } from './incidentResolution'

const resolved = {
  incidencia_id: incident.incidencia_id, estado: 'VALIDADA',
  resuelta_por: incident.conductor.conductor_id, resuelta_en: incident.registrada_en,
}
beforeEach(() => {
  vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000')
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(resolved))))
})
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs() })

it('envía solo acción y motivo con cookie y acepta el contrato de resolución', async () => {
  expect(await resolveIncident(incident.incidencia_id, 'VALIDAR', '😀'.repeat(300))).toEqual(resolved)
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining(`/incidencias/${incident.incidencia_id}`), expect.objectContaining({
    method: 'PATCH', credentials: 'include', cache: 'no-store', body: JSON.stringify({ accion: 'VALIDAR', motivo: '😀'.repeat(300) }),
  }))
})
it('acepta descarte con motivo vacío', async () => {
  vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ ...resolved, estado: 'DESCARTADA' })))
  expect((await resolveIncident(incident.incidencia_id, 'DESCARTAR', '')).estado).toBe('DESCARTADA')
})
it.each([[401, 'unauthorized'], [403, 'forbidden'], [409, 'conflict'], [422, 'invalid'], [404, 'unavailable'], [503, 'unavailable']])(
  'HTTP %s produce error seguro %s', async (status, kind) => {
    vi.mocked(fetch).mockResolvedValue(new Response('PRIVATE', { status: Number(status) }))
    await expect(resolveIncident(incident.incidencia_id, 'VALIDAR', '')).rejects.toMatchObject({ kind })
  },
)
it('rechaza motivo excedido e identificador inválido sin enviar', async () => {
  await expect(resolveIncident(incident.incidencia_id, 'VALIDAR', 'x'.repeat(301))).rejects.toMatchObject({ kind: 'invalid' })
  await expect(resolveIncident('private', 'VALIDAR', '')).rejects.toBeInstanceOf(IncidentResolutionError)
  expect(fetch).not.toHaveBeenCalled()
})
it.each([null, {}, { ...resolved, incidencia_id: 'other' }, { ...resolved, estado: 'DESCARTADA' },
  { ...resolved, resuelta_por: 'private' }, { ...resolved, resuelta_en: '2026-01-01' }, { ...resolved, resuelta_en: 'invalidZ' }])(
  'rechaza un contrato de éxito inválido', async body => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify(body)))
    await expect(resolveIncident(incident.incidencia_id, 'VALIDAR', '')).rejects.toMatchObject({ kind: 'unavailable' })
  },
)
it('sanea fallos de red y JSON', async () => {
  vi.mocked(fetch).mockRejectedValueOnce(new Error('PRIVATE'))
  await expect(resolveIncident(incident.incidencia_id, 'VALIDAR', '')).rejects.toMatchObject({ kind: 'unavailable' })
  vi.mocked(fetch).mockResolvedValueOnce(new Response('PRIVATE'))
  await expect(resolveIncident(incident.incidencia_id, 'VALIDAR', '')).rejects.toMatchObject({ kind: 'unavailable' })
})
