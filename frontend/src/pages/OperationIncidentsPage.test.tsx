import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { OperationIncidentsPage } from './OperationIncidentsPage'
import { IncidentListError, listPendingIncidents } from '../services/incidentList'
import { IncidentResolutionError, resolveIncident } from '../services/incidentResolution'
import { pendingIncident as incident, pendingIncidentPage as page } from '../test/incidentFixtures'

vi.mock('../services/incidentList', async original => {
  const actual = await original<typeof import('../services/incidentList')>()
  return { ...actual, listPendingIncidents: vi.fn() }
})
const listMock = vi.mocked(listPendingIncidents)
vi.mock('../services/incidentResolution', async original => ({
  ...await original<typeof import('../services/incidentResolution')>(), resolveIncident: vi.fn(),
}))
const resolveMock = vi.mocked(resolveIncident)
beforeEach(() => { listMock.mockReset().mockResolvedValue(page) })
beforeEach(() => { resolveMock.mockReset().mockResolvedValue({
  incidencia_id: incident.incidencia_id, estado: 'VALIDADA',
  resuelta_por: incident.conductor.conductor_id, resuelta_en: incident.registrada_en,
}) })
afterEach(() => { vi.useRealTimers() })

function renderPage(onSessionExpired = vi.fn()) {
  return { ...render(<OperationIncidentsPage onSessionExpired={onSessionExpired} />), onSessionExpired }
}

it.each(['Validar', 'Descartar'])('ECL-98: confirma %s con teclado y retira la incidencia', async action => {
  const user = userEvent.setup()
  renderPage()
  const opener = await screen.findByRole('button', { name: `${action} incidencia ${incident.incidencia_id}` })
  opener.focus()
  await user.keyboard('{Enter}')
  const dialog = screen.getByRole('dialog', { name: `${action} incidencia` })
  expect(within(dialog).getByRole('textbox')).toHaveFocus()
  await user.type(within(dialog).getByRole('textbox'), 'Revisión operativa')
  listMock.mockResolvedValue({ ...page, items: [], total: 0 })
  within(dialog).getByRole('button', { name: 'Confirmar decisión' }).focus()
  await user.keyboard('{Enter}')
  expect(await screen.findByText(action === 'Validar' ? 'Incidencia validada.' : 'Incidencia descartada.')).toHaveFocus()
  expect(resolveMock).toHaveBeenCalledWith(incident.incidencia_id, action === 'Validar' ? 'VALIDAR' : 'DESCARTAR', 'Revisión operativa')
  expect(await screen.findByText('No hay incidencias pendientes de validación')).toBeInTheDocument()
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})

it('ECL-98: Escape y cancelar devuelven foco y no envían; motivo excedido bloquea confirmar', async () => {
  const user = userEvent.setup()
  renderPage()
  const opener = await screen.findByRole('button', { name: `Validar incidencia ${incident.incidencia_id}` })
  await user.click(opener)
  await user.keyboard('{Escape}')
  expect(opener).toHaveFocus()
  expect(resolveMock).not.toHaveBeenCalled()
  await user.click(opener)
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'x'.repeat(301) } })
  expect(screen.getByRole('button', { name: 'Confirmar decisión' })).toBeDisabled()
  await user.click(screen.getByRole('button', { name: 'Cancelar' }))
  expect(opener).toHaveFocus()
})

it('ECL-98: 409 anuncia la decisión concurrente y actualiza la lista', async () => {
  resolveMock.mockRejectedValue(new IncidentResolutionError('conflict'))
  renderPage()
  await userEvent.click(await screen.findByRole('button', { name: `Validar incidencia ${incident.incidencia_id}` }))
  listMock.mockResolvedValue({ ...page, items: [], total: 0 })
  await userEvent.click(screen.getByRole('button', { name: 'Confirmar decisión' }))
  expect(await screen.findByText(/Otra persona ya resolvió/)).toBeInTheDocument()
  expect(await screen.findByText('No hay incidencias pendientes de validación')).toBeInTheDocument()
})

it.each(['unauthorized', 'forbidden', 'unavailable'] as const)('ECL-98: maneja %s sin retirar el pendiente', async kind => {
  resolveMock.mockRejectedValue(new IncidentResolutionError(kind))
  const { onSessionExpired } = renderPage()
  await userEvent.click(await screen.findByRole('button', { name: `Descartar incidencia ${incident.incidencia_id}` }))
  await userEvent.click(screen.getByRole('button', { name: 'Confirmar decisión' }))
  if (kind === 'unauthorized') await waitFor(() => expect(onSessionExpired).toHaveBeenCalledOnce())
  else expect(await screen.findByRole('alert')).toHaveTextContent(new IncidentResolutionError(kind).message)
  expect(listMock).toHaveBeenCalledOnce()
})

it('ECL-98: mientras guarda bloquea decisiones duplicadas y Escape', async () => {
  let finish!: (value: Awaited<ReturnType<typeof resolveIncident>>) => void
  resolveMock.mockReturnValue(new Promise(resolve => { finish = resolve }))
  renderPage()
  await userEvent.click(await screen.findByRole('button', { name: `Validar incidencia ${incident.incidencia_id}` }))
  await userEvent.click(screen.getByRole('button', { name: 'Confirmar decisión' }))
  expect(screen.getByRole('button', { name: 'Guardando…' })).toBeDisabled()
  await userEvent.keyboard('{Escape}')
  expect(screen.getByRole('dialog')).toBeInTheDocument()
  expect(resolveMock).toHaveBeenCalledOnce()
  await act(async () => {
    finish({ incidencia_id: incident.incidencia_id, estado: 'VALIDADA', resuelta_por: incident.conductor.conductor_id, resuelta_en: incident.registrada_en })
    await Promise.resolve()
  })
})

it('I02: presenta hora de Lima, catálogo, severidad textual con icono y solo el nombre del conductor', async () => {
  renderPage()
  const table = await screen.findByRole('table')
  const time = within(table).getByText('26/10 09:15').closest('time')
  expect(time).toHaveAttribute('datetime', incident.ocurrida_en)
  expect(time).not.toHaveAttribute('aria-label')
  expect(time?.querySelector('.visually-hidden')).toHaveTextContent('2026')
  expect(time?.querySelector('.visually-hidden')).toHaveTextContent('hora de Lima')
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
  expect(rows.map(row => row.querySelector('time [aria-hidden="true"]')?.textContent)).toEqual(['26/10 11:00', '26/10 10:00', '26/10 09:15'])
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
  listMock.mockResolvedValueOnce({ ...page, total: 13 })
  listMock.mockResolvedValueOnce({ ...page, page: 2, total: 13 })
  listMock.mockResolvedValueOnce({ ...page, page: 2, total: 13 })
  listMock.mockResolvedValueOnce({ ...page, total: 13 })
  renderPage()
  await screen.findByRole('table')
  const user = userEvent.setup()
  screen.getByRole('button', { name: 'Siguiente' }).focus()
  await user.keyboard('{Enter}')
  expect(await screen.findByText('Página 2 de 2')).toBeInTheDocument()
  expect(listMock).toHaveBeenLastCalledWith(2, 12, expect.any(AbortSignal))
  expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled()
  await user.click(screen.getByRole('button', { name: 'Actualizar listado' }))
  await screen.findByRole('table')
  expect(listMock).toHaveBeenLastCalledWith(2, 12, expect.any(AbortSignal))
  await user.click(screen.getByRole('button', { name: 'Anterior' }))
  expect(await screen.findByText('Página 1 de 2')).toBeInTheDocument()
})

it('si desaparece la última página, consulta de nuevo una página válida', async () => {
  listMock.mockResolvedValueOnce({ ...page, total: 13 })
  listMock.mockResolvedValueOnce({ ...page, page: 2, items: [], total: 12 })
  listMock.mockResolvedValueOnce({ ...page, total: 12 })
  renderPage()
  await screen.findByRole('table')
  await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
  expect(await screen.findByText('Página 1 de 1')).toBeInTheDocument()
  expect(listMock).toHaveBeenLastCalledWith(1, 12, expect.any(AbortSignal))
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
