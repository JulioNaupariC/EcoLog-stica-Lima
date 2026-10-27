import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { OperationIncidentsPage } from './OperationIncidentsPage'
import { IncidentListError, listPendingIncidents } from '../services/incidentList'
import { pendingIncident as incident, pendingIncidentPage as page } from '../test/incidentFixtures'

vi.mock('../services/incidentList', async original => {
  const actual = await original<typeof import('../services/incidentList')>()
  return { ...actual, listPendingIncidents: vi.fn() }
})
const listMock = vi.mocked(listPendingIncidents)
beforeEach(() => { listMock.mockReset().mockResolvedValue(page) })
afterEach(() => { vi.useRealTimers() })

function renderPage(onSessionExpired = vi.fn()) {
  return { ...render(<OperationIncidentsPage onSessionExpired={onSessionExpired} />), onSessionExpired }
}

it('I02: presenta hora de Lima, catálogo, severidad textual con icono y solo el nombre del conductor', async () => {
  renderPage()
  const table = await screen.findByRole('table')
  expect(within(table).getByText('26/10 09:15')).toHaveAttribute('datetime', incident.ocurrida_en)
  expect(within(table).getByText('Avería')).toBeInTheDocument()
  expect(within(table).getByText('Alta').querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
  expect(within(table).getByText(incident.conductor.nombre)).toBeInTheDocument()
  expect(within(table).getByText('-12.04641, -77.04281')).toBeInTheDocument()
  const map = within(table).getByRole('link', { name: 'Ver en mapa (nueva pestaña)' })
  expect(map).toHaveAttribute('href', expect.stringContaining('https://www.openstreetmap.org/'))
  expect(map).toHaveAttribute('target', '_blank')
  expect(map).toHaveAttribute('rel', 'noopener noreferrer')
  expect(document.body).not.toHaveTextContent(incident.conductor.conductor_id)
  expect(screen.getByText('Página 1 de 1')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Anterior' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled()
})

it('conserva el orden de ocurrencia entregado por el servicio y muestra las tres severidades con texto', async () => {
  listMock.mockResolvedValue({ ...page, total: 3, items: [
    { ...incident, ocurrida_en: '2026-10-26T11:00:00-05:00' },
    { ...incident, incidencia_id: '323e4567-e89b-42d3-a456-426614174000', severidad: 'MEDIA', ocurrida_en: '2026-10-26T10:00:00-05:00' },
    { ...incident, incidencia_id: '423e4567-e89b-42d3-a456-426614174000', severidad: 'BAJA' },
  ] })
  renderPage()
  const table = await screen.findByRole('table')
  const rows = within(table).getAllByRole('row').slice(1)
  expect(rows.map(row => row.querySelector('time')?.textContent)).toEqual(['26/10 11:00', '26/10 10:00', '26/10 09:15'])
  for (const label of ['Alta', 'Media', 'Baja']) expect(within(table).getByText(label).querySelector('svg')).not.toBeNull()
})

it('trunca observaciones largas con la completa en un detalle nativo accesible y sin interpretar HTML', async () => {
  const text = '<script>alert("synthetic")</script> ' + 'Texto de ejemplo. '.repeat(12)
  listMock.mockResolvedValue({ ...page, items: [{ ...incident, observacion: text }] })
  renderPage()
  await screen.findByRole('table')
  const summary = screen.getByText('Ver observación completa')
  expect(summary.closest('details')).not.toHaveAttribute('open')
  await userEvent.click(summary)
  expect(summary.closest('details')).toHaveAttribute('open')
  expect(within(summary.closest('details')!).getByText(text.trim())).toBeVisible()
  expect(document.querySelector('script')).toBeNull()
})

it('admite observación vacía', async () => {
  listMock.mockResolvedValue({ ...page, items: [{ ...incident, observacion: '' }] })
  renderPage()
  expect(await screen.findByText('Sin observación')).toBeInTheDocument()
})

it('muestra vacío sin inventar datos y permite actualizar', async () => {
  listMock.mockResolvedValueOnce({ ...page, items: [], total: 0 })
  renderPage()
  expect(await screen.findByRole('heading', { name: 'No hay incidencias pendientes de validación' })).toBeInTheDocument()
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Actualizar listado' }))
  expect(await screen.findByRole('table')).toBeInTheDocument()
  expect(listMock).toHaveBeenCalledTimes(2)
})

it('anuncia carga y muestra esqueleto solo al alcanzar un segundo; lo retira al terminar', async () => {
  vi.useFakeTimers()
  let finish!: (value: typeof page) => void
  listMock.mockReturnValue(new Promise(resolve => { finish = resolve }))
  const { container } = renderPage()
  await act(async () => { await Promise.resolve() })
  expect(screen.getByText('Cargando incidencias pendientes…')).toHaveAttribute('role', 'status')
  expect(container.querySelector('.skeleton')).toBeNull()
  expect(screen.getByRole('button', { name: 'Actualizar listado' })).toBeDisabled()
  await act(async () => { await vi.advanceTimersByTimeAsync(999) })
  expect(container.querySelector('.skeleton')).toBeNull()
  await act(async () => { await vi.advanceTimersByTimeAsync(1) })
  expect(container.querySelector('.skeleton')).toHaveAttribute('aria-hidden', 'true')
  await act(async () => { finish(page); await Promise.resolve() })
  expect(container.querySelector('.skeleton')).toBeNull()
  expect(screen.getByRole('table')).toBeInTheDocument()
})

it('muestra error de red con reintento y un mensaje específico para 403', async () => {
  listMock.mockRejectedValueOnce(new IncidentListError('network'))
  listMock.mockRejectedValueOnce(new IncidentListError('forbidden'))
  renderPage()
  expect(await screen.findByRole('alert')).toHaveTextContent('Revisa tu conexión')
  await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Solo Administrador y Operador')
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
  expect(await screen.findByRole('table')).toBeInTheDocument()
})

it('un error inesperado muestra un mensaje seguro y 401 devuelve el control a la sesión', async () => {
  listMock.mockRejectedValueOnce(new Error('PRIVATE_DETAIL'))
  listMock.mockRejectedValueOnce(new IncidentListError('unauthorized'))
  const { onSessionExpired } = renderPage()
  expect(await screen.findByRole('alert')).not.toHaveTextContent('PRIVATE_DETAIL')
  await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
  await waitFor(() => expect(onSessionExpired).toHaveBeenCalledOnce())
})

it('I15: pagina con teclado, actualiza la página actual y vuelve a la anterior', async () => {
  listMock.mockResolvedValueOnce({ ...page, total: 21 })
  listMock.mockResolvedValueOnce({ ...page, page: 2, total: 21 })
  listMock.mockResolvedValueOnce({ ...page, page: 2, total: 21 })
  listMock.mockResolvedValueOnce({ ...page, total: 21 })
  renderPage()
  await screen.findByRole('table')
  const user = userEvent.setup()
  screen.getByRole('button', { name: 'Siguiente' }).focus()
  await user.keyboard('{Enter}')
  expect(await screen.findByText('Página 2 de 2')).toBeInTheDocument()
  expect(listMock).toHaveBeenLastCalledWith(2, 20, expect.any(AbortSignal))
  expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled()
  await user.click(screen.getByRole('button', { name: 'Actualizar listado' }))
  await screen.findByRole('table')
  expect(listMock).toHaveBeenLastCalledWith(2, 20, expect.any(AbortSignal))
  await user.click(screen.getByRole('button', { name: 'Anterior' }))
  expect(await screen.findByText('Página 1 de 2')).toBeInTheDocument()
})

it('si desaparece la última página, consulta de nuevo una página válida', async () => {
  listMock.mockResolvedValueOnce({ ...page, total: 21 })
  listMock.mockResolvedValueOnce({ ...page, page: 2, items: [], total: 20 })
  listMock.mockResolvedValueOnce({ ...page, total: 20 })
  renderPage()
  await screen.findByRole('table')
  await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
  expect(await screen.findByText('Página 1 de 1')).toBeInTheDocument()
  expect(listMock).toHaveBeenLastCalledWith(1, 20, expect.any(AbortSignal))
})

it('cancela al desmontar y no procesa una respuesta o error de una página abandonada', async () => {
  let fail!: (error: Error) => void
  listMock.mockReturnValue(new Promise((_resolve, reject) => { fail = reject }))
  const { unmount, onSessionExpired } = renderPage()
  await waitFor(() => expect(listMock).toHaveBeenCalledOnce())
  const signal = listMock.mock.calls[0][2]!
  unmount()
  expect(signal.aborted).toBe(true)
  await act(async () => { fail(new IncidentListError('unauthorized')); await Promise.resolve() })
  expect(onSessionExpired).not.toHaveBeenCalled()
})
