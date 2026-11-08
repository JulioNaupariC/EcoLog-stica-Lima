import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { OperationRoutesPage } from './OperationRoutesPage'
import { operationFixture, operationPage } from '../test/operationRoutesFixtures'
import { RouteOutcomeError } from '../services/routeOutcomes'
import { OperationRoutesError } from '../services/operationRoutes'
import type { RouteSource } from '../services/operationRoutes'
import type { RouteOutcomeSource } from '../services/routeOutcomes'
import type { AuthRole } from '../services/auth'
import type { UpdatedStop } from '../domain/routeOutcomes'

vi.mock('../domain/operationRoutes', async original => ({ ...await original<typeof import('../domain/operationRoutes')>(), operationDateInLima: () => '2026-11-20' }))
vi.mock('../components/OperationRouteMap', () => ({ OperationRouteMap: () => <div>Mapa de prueba</div> }))
let source: RouteSource, outcomes: RouteOutcomeSource, plan: ReturnType<typeof operationFixture>
const NOW = Date.parse('2026-11-20T18:00:00Z')
beforeEach(() => {
  vi.spyOn(Date, 'now').mockReturnValue(NOW)
  plan = operationFixture(); plan.simulado = false
  plan.rutas[0].estado = 'PLANIFICADA'; plan.rutas[0].paradas = plan.rutas[0].paradas.slice(0, 2).map(s => ({ ...s, estado: 'PENDIENTE' }))
  source = { list: vi.fn().mockResolvedValue({ ...operationPage(), simulado: false }), detail: vi.fn().mockImplementation(() => Promise.resolve(structuredClone(plan))) }
  outcomes = {
    record: vi.fn().mockImplementation((ruta_id: string, parada_id: string, payload: { estado: 'ATENDIDA' | 'NO_ATENDIDA'; atendida_en?: string }) => Promise.resolve({ ruta_id, parada_id, ...payload, atendida_en: payload.atendida_en ?? null, ruta_estado: 'EN_CURSO' })),
    close: vi.fn().mockImplementation((ruta_id: string) => Promise.resolve({ ruta_id, estado: 'CERRADA', cerrada_en: '2026-11-20T13:00:00-05:00', paradas_atendidas: 1, paradas_no_atendidas: 1 })),
  }
})
afterEach(() => { vi.restoreAllMocks() })
function show(role: AuthRole = 'OPERADOR') {
  const expired = vi.fn()
  return { ...render(<OperationRoutesPage role={role} source={source} outcomes={outcomes} onSessionExpired={expired} />), expired }
}
const ready = () => screen.findByRole('heading', { name: 'Ruta ECO-101' })
const open = (n: number) => fireEvent.click(screen.getByRole('button', { name: `Registrar resultado de parada ${n}` }))
const save = (n: number) => fireEvent.click(screen.getByRole('button', { name: `Guardar resultado de parada ${n}` }))
async function record(n: number, attended = true) {
  open(n)
  if (!attended) fireEvent.change(screen.getByLabelText(`Resultado de parada ${n}`), { target: { value: 'NO_ATENDIDA' } })
  save(n)
  await waitFor(() => expect(screen.queryByRole('button', { name: `Guardar resultado de parada ${n}` })).not.toBeInTheDocument())
}

it('éxito: registra atención real y no atención, bloquea finales y cierra con confirmación por teclado', async () => {
  const user = userEvent.setup(), confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
  show(); await ready()
  expect(screen.getByRole('button', { name: 'Cerrar ruta' })).toBeDisabled()
  open(1)
  expect(screen.getByLabelText('Hora real de parada 1 (Lima)')).toHaveValue('2026-11-20T13:00')
  expect(screen.getByLabelText('Hora real de parada 1 (Lima)')).toHaveFocus()
  expect(screen.getByText('Hora de Lima (24 h): 2026-11-20 13:00:00.')).toBeInTheDocument()
  save(1)
  await waitFor(() => expect(screen.queryByRole('button', { name: 'Registrar resultado de parada 1' })).not.toBeInTheDocument())
  expect(outcomes.record).toHaveBeenCalledWith(plan.rutas[0].ruta_id, plan.rutas[0].paradas[0].parada_id,
    { estado: 'ATENDIDA', atendida_en: '2026-11-20T13:00:00-05:00' }, expect.any(AbortSignal))
  expect(screen.getByText(/Estado: en curso/)).toBeInTheDocument()
  await waitFor(() => expect(screen.getByText(/Resultado de parada 1 registrado: atendida/).closest('[role="status"]')).toHaveFocus())
  await record(2, false)
  expect(screen.getAllByText('Resultado final registrado; no se puede editar.')).toHaveLength(2)
  const close = screen.getByRole('button', { name: 'Cerrar ruta' })
  expect(close).toBeEnabled(); close.focus(); await user.keyboard('{Enter}')
  expect(screen.getByRole('button', { name: 'Cancelar cierre' })).toHaveFocus()
  expect(outcomes.close).not.toHaveBeenCalled()
  await user.keyboard('{Enter}'); expect(close).toHaveFocus()
  fireEvent.click(close); await user.keyboard('{Tab}'); await user.keyboard(' ')
  await screen.findByText(/Ruta cerrada el/)
  expect(outcomes.close).toHaveBeenCalledOnce(); expect(confirm).not.toHaveBeenCalled()
  expect(screen.getByText(/Estado: cerrada/)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Ver dashboard de sostenibilidad' })).toHaveAttribute('href', '/indicadores/sostenibilidad')
  expect(screen.queryByRole('button', { name: 'Cerrar ruta' })).not.toBeInTheDocument()
})
it('valida hora antes de enviar y conserva el borrador con foco en el campo', async () => {
  show(); await ready(); open(1)
  const input = screen.getByLabelText('Hora real de parada 1 (Lima)')
  fireEvent.change(input, { target: { value: '2026-11-20T13:01' } }); save(1)
  expect(screen.getByRole('alert')).toHaveTextContent('no puede ser futura')
  expect(input).toHaveFocus(); expect(input).toHaveAttribute('aria-invalid', 'true')
  fireEvent.change(input, { target: { value: '2026-11-19T23:59' } }); save(1)
  expect(screen.getByRole('alert')).toHaveTextContent('anterior a la jornada')
  expect(input).toHaveValue('2026-11-19T23:59'); expect(outcomes.record).not.toHaveBeenCalled()
  fireEvent.change(input, { target: { value: '' } }); save(1)
  expect(screen.getByText('Hora de Lima (24 h): sin hora seleccionada.')).toBeInTheDocument()
  expect(outcomes.record).not.toHaveBeenCalled()
})
it('cancelar registro devuelve el foco y no hace cambios', async () => {
  show(); await ready(); open(1)
  fireEvent.click(screen.getByRole('button', { name: 'Cancelar registro de parada 1' }))
  expect(screen.getByRole('button', { name: 'Registrar resultado de parada 1' })).toHaveFocus()
  expect(outcomes.record).not.toHaveBeenCalled()
})
it('422 del servidor se muestra junto a la hora y no modifica estados', async () => {
  vi.mocked(outcomes.record).mockRejectedValueOnce(new RouteOutcomeError('invalid', 'La hora de atención no puede ser futura', 'atendida_en'))
  show(); await ready(); open(1); save(1)
  expect(await screen.findByRole('alert')).toHaveTextContent('no puede ser futura')
  await waitFor(() => expect(screen.getByLabelText('Hora real de parada 1 (Lima)')).toHaveFocus())
  expect(screen.getByRole('button', { name: 'Cerrar ruta' })).toBeDisabled()
  expect(screen.getByText(/Estado: planificada/)).toBeInTheDocument()
})
it.each(['conflict', 'not_found', 'unavailable'] as const)('%s obliga a refrescar sin perder borrador ni fingir éxito', async kind => {
  vi.mocked(outcomes.record).mockRejectedValueOnce(new RouteOutcomeError(kind))
  show(); await ready(); open(1); save(1)
  const error = await screen.findByRole('alert')
  await waitFor(() => expect(error).toHaveFocus())
  expect(screen.queryByText(/registrado: atendida/)).not.toBeInTheDocument()
  const input = screen.getByLabelText('Hora real de parada 1 (Lima)')
  expect(input).toBeDisabled(); expect(input).toHaveValue('2026-11-20T13:00')
  fireEvent.click(screen.getByRole('button', { name: 'Actualizar estado de la ruta' }))
  await waitFor(() => expect(input).toBeEnabled())
  expect(source.detail).toHaveBeenCalledTimes(2)
  save(1); await waitFor(() => expect(screen.queryByRole('button', { name: 'Guardar resultado de parada 1' })).not.toBeInTheDocument())
})
it('503 seguido de fallo de lectura mantiene escrituras bloqueadas hasta una lectura válida', async () => {
  vi.mocked(outcomes.record).mockRejectedValueOnce(new RouteOutcomeError('unavailable'))
  show(); await ready(); open(1); save(1); await screen.findByRole('alert')
  vi.mocked(source.detail).mockRejectedValueOnce(new OperationRoutesError('unavailable'))
  fireEvent.click(screen.getByRole('button', { name: 'Actualizar estado de la ruta' }))
  await screen.findByText(/Se conserva la última versión del plan/)
  expect(screen.getByRole('button', { name: 'Guardar resultado de parada 1' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Reintentar plan' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Guardar resultado de parada 1' })).toBeEnabled())
})
it('409 de cierre muestra el motivo y la lectura posterior detecta paradas pendientes', async () => {
  plan.rutas[0].estado = 'EN_CURSO'; plan.rutas[0].paradas.forEach(s => { s.estado = 'NO_ATENDIDA' })
  vi.mocked(outcomes.close).mockRejectedValueOnce(new RouteOutcomeError('conflict', 'Faltan 1 paradas por registrar'))
  show(); await ready(); fireEvent.click(screen.getByRole('button', { name: 'Cerrar ruta' }))
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar cierre' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Faltan 1 paradas por registrar')
  plan.rutas[0].paradas[0].estado = 'PENDIENTE'
  fireEvent.click(screen.getByRole('button', { name: 'Actualizar estado de la ruta' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Cerrar ruta' })).toBeDisabled())
  expect(screen.getByRole('button', { name: 'Registrar resultado de parada 1' })).toBeEnabled()
})
it('401 termina la sesión y 403 impide nuevos intentos de escritura', async () => {
  vi.mocked(outcomes.record).mockRejectedValueOnce(new RouteOutcomeError('unauthorized'))
  const { expired } = show(); await ready(); open(1); save(1)
  await waitFor(() => expect(expired).toHaveBeenCalledOnce())
  vi.mocked(outcomes.record).mockRejectedValueOnce(new RouteOutcomeError('forbidden')); save(1)
  expect(await screen.findByRole('alert')).toHaveTextContent('Solo el Operador')
  expect(screen.queryByRole('button', { name: 'Cerrar ruta' })).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Registrar resultado de parada 2' })).not.toBeInTheDocument()
})
it.each(['ADMINISTRADOR', 'ANALISTA', 'AUDITOR', 'CONDUCTOR'] as const)('%s nunca recibe acciones en el componente de detalle', async role => {
  show(role); await ready()
  expect(screen.getByText(/Estado: planificada/)).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Cerrar ruta' })).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Registrar resultado/ })).not.toBeInTheDocument()
  expect(outcomes.record).not.toHaveBeenCalled(); expect(outcomes.close).not.toHaveBeenCalled()
})
it('nunca escribe sobre un detalle simulado ni sobre una ruta cerrada', async () => {
  plan.simulado = true
  const first = show(); await ready()
  expect(screen.queryByRole('button', { name: /Registrar resultado/ })).not.toBeInTheDocument()
  first.unmount(); plan.simulado = false; plan.rutas[0].estado = 'CERRADA'
  show(); await ready()
  expect(screen.getByText('Ruta cerrada. Sus resultados ya no se pueden editar.')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Cerrar ruta' })).not.toBeInTheDocument()
})
it('no hace cambios optimistas, evita doble envío y descarta respuestas al cambiar de ruta', async () => {
  let resolve!: (value: UpdatedStop) => void
  vi.mocked(outcomes.record).mockImplementationOnce(() => new Promise(done => { resolve = done }))
  show(); await ready(); open(1); save(1); save(1)
  expect(outcomes.record).toHaveBeenCalledOnce()
  expect(screen.getByText(/Estado: planificada/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Registrar resultado de parada 2' })).toBeDisabled()
  const args = vi.mocked(outcomes.record).mock.calls[0]
  fireEvent.click(screen.getByRole('button', { name: /Ruta ECO-102/ }))
  await screen.findByRole('heading', { name: 'Ruta ECO-102' }); expect(args[3].aborted).toBe(true)
  await act(async () => { resolve({ ruta_id: args[0], parada_id: args[1], estado: 'ATENDIDA', atendida_en: '2026-11-20T13:00:00-05:00', ruta_estado: 'EN_CURSO' }); await Promise.resolve() })
  expect(screen.queryByText(/registrado: atendida/)).not.toBeInTheDocument()
  expect(within(screen.getByRole('heading', { name: 'Ruta ECO-102' }).parentElement!).queryByText(/Ruta cerrada el/)).not.toBeInTheDocument()
})
it('un acuse de cierre con conteos incoherentes no confirma el cierre', async () => {
  plan.rutas[0].estado = 'EN_CURSO'; plan.rutas[0].paradas.forEach(s => { s.estado = 'NO_ATENDIDA' })
  vi.mocked(outcomes.close).mockResolvedValueOnce({ ruta_id: plan.rutas[0].ruta_id, estado: 'CERRADA', cerrada_en: '2026-11-20T13:00:00-05:00', paradas_atendidas: 99, paradas_no_atendidas: 0 })
  show(); await ready(); fireEvent.click(screen.getByRole('button', { name: 'Cerrar ruta' }))
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar cierre' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo confirmar')
  expect(screen.getByText(/Estado: en curso/)).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Ver dashboard de sostenibilidad' })).not.toBeInTheDocument()
})
