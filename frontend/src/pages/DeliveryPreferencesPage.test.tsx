import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DeliveryPreferencesPage } from './DeliveryPreferencesPage'
import { getDeliveryPreferences, PreferencesServiceError, updateDeliveryPreferences } from '../services/deliveryPreferences'
import type { DeliveryPreferences } from '../services/deliveryPreferences'
import { searchClients } from '../services/clients'

vi.mock('../services/deliveryPreferences', async original => ({
  ...await original<typeof import('../services/deliveryPreferences')>(), getDeliveryPreferences: vi.fn(), updateDeliveryPreferences: vi.fn(),
}))
vi.mock('../services/clients', async original => ({
  ...await original<typeof import('../services/clients')>(), searchClients: vi.fn(),
}))
const CLIENT = { cliente_id: '123e4567-e89b-12d3-a456-426614174000', nombre: 'Bodega Ficticia Norte' }
const get = vi.mocked(getDeliveryPreferences)
const patch = vi.mocked(updateDeliveryPreferences)
const saved: DeliveryPreferences = {
  cliente_id: '123e4567-e89b-12d3-a456-426614174000', horario_preferido: 'Mañana',
  referencia: 'Puerta norte', restriccion_acceso: 'Avisar a recepción',
}
function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: Error) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { resolve, reject, promise }
}
function show() {
  const expired = vi.fn()
  const view = render(<DeliveryPreferencesPage onSessionExpired={expired} />)
  return { ...view, expired, user: userEvent.setup() }
}
function clientInput() { return screen.getByRole('combobox', { name: 'Cliente' }) }
async function selectClient() {
  if (screen.queryByText(/Cliente seleccionado:/u)) return
  fireEvent.change(clientInput(), { target: { value: 'Bodega' } })
  fireEvent.click(await screen.findByRole('option', { name: /Bodega Ficticia Norte/u }))
}
async function consult() {
  await selectClient()
  fireEvent.submit(screen.getByRole('form', { name: 'Consultar cliente' }))
}
async function ready() {
  const view = show()
  await consult()
  await screen.findByRole('heading', { name: 'Preferencias del cliente' })
  return view
}
function submit() { fireEvent.submit(screen.getByRole('form', { name: 'Editar preferencias de entrega' })) }
beforeEach(() => {
  get.mockReset().mockResolvedValue(saved); patch.mockReset().mockResolvedValue(saved)
  vi.mocked(searchClients).mockReset().mockResolvedValue({ items: [CLIENT], page: 1, page_size: 8, total: 1 })
})

it('ruta infeliz: exige seleccionar un cliente de la lista sin hacer solicitudes', async () => {
  show()
  expect(get).not.toHaveBeenCalled()
  fireEvent.change(clientInput(), { target: { value: 'texto sin seleccionar' } })
  fireEvent.submit(screen.getByRole('form', { name: 'Consultar cliente' }))
  expect(await screen.findByRole('alert')).toHaveFocus()
  expect(screen.getByText('Selecciona un cliente de la lista.')).toBeInTheDocument()
  expect(clientInput()).toHaveAttribute('aria-invalid', 'true')
  expect(get).not.toHaveBeenCalled()
  await selectClient()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})
it('ruta dorada: busca por nombre, selecciona y consulta las preferencias del cliente', async () => {
  show()
  await consult()
  expect(await screen.findByRole('heading', { name: 'Preferencias del cliente' })).toBeInTheDocument()
  const [term, options] = vi.mocked(searchClients).mock.calls[0]
  expect(term).toBe('Bodega')
  expect(options?.signal).toBeInstanceOf(AbortSignal)
  expect(get).toHaveBeenCalledWith(CLIENT.cliente_id)
})
it('anuncia carga, impide doble consulta y recupera valores con foco', async () => {
  const pending = deferred<DeliveryPreferences>()
  get.mockReturnValueOnce(pending.promise)
  show()
  await consult()
  fireEvent.submit(screen.getByRole('form', { name: 'Consultar cliente' }))
  expect(get).toHaveBeenCalledTimes(1)
  expect(screen.getByRole('status')).toHaveTextContent('Cargando preferencias')
  expect(clientInput()).toBeDisabled()
  await act(async () => { pending.resolve(saved); await pending.promise })
  expect(await screen.findByRole('heading', { name: 'Preferencias del cliente' })).toHaveFocus()
  expect(screen.getByLabelText('Horario preferido')).toHaveValue('Mañana')
  expect(screen.getByLabelText('Referencia de ubicación')).toHaveValue('Puerta norte')
})
it('representa preferencias vacías y permite inicializarlas', async () => {
  get.mockResolvedValueOnce({ ...saved, horario_preferido: null, referencia: null, restriccion_acceso: null })
  const { user } = await ready()
  expect(screen.getByLabelText('Horario preferido')).toBeDisabled()
  await user.click(screen.getByLabelText('Sin horario preferido'))
  await user.type(screen.getByLabelText('Horario preferido'), 'Tarde')
  submit()
  await waitFor(() => expect(patch).toHaveBeenCalledWith(saved.cliente_id, { horario_preferido: 'Tarde' }))
})
it('rechaza sin cambios, blancos y exceso de longitud; asocia errores a campos', async () => {
  await ready()
  submit()
  expect(await screen.findByRole('alert')).toHaveTextContent('No hay cambios')
  fireEvent.change(screen.getByLabelText('Horario preferido'), { target: { value: ' ' } })
  submit()
  expect(await screen.findByRole('alert')).toHaveTextContent('Revisa los campos')
  expect(screen.getByLabelText('Horario preferido')).toHaveAttribute('aria-invalid', 'true')
  expect(screen.getByLabelText('Horario preferido')).toHaveAccessibleDescription(/Escribe una preferencia/u)
  fireEvent.change(screen.getByLabelText('Horario preferido'), { target: { value: 'A'.repeat(121) } })
  submit()
  expect(await screen.findByText('Usa como máximo 120 caracteres.')).toBeInTheDocument()
  expect(patch).not.toHaveBeenCalled()
})
it('envía solo cambios una vez y actualiza la base local después del ACK', async () => {
  await ready()
  const pending = deferred<DeliveryPreferences>()
  patch.mockReturnValueOnce(pending.promise)
  fireEvent.change(screen.getByLabelText('Referencia de ubicación'), { target: { value: ' Nueva puerta ' } })
  submit(); submit()
  expect(patch).toHaveBeenCalledTimes(1)
  expect(patch).toHaveBeenCalledWith(saved.cliente_id, { referencia: ' Nueva puerta ' })
  expect(screen.getByRole('button', { name: 'Guardando…' })).toBeDisabled()
  await act(async () => { pending.resolve({ ...saved, referencia: ' Nueva puerta ' }); await pending.promise })
  expect(await screen.findByRole('status')).toHaveTextContent('Preferencias guardadas correctamente')
  expect(screen.getByLabelText('Referencia de ubicación')).toHaveValue(' Nueva puerta ')
  submit()
  expect(await screen.findByRole('alert')).toHaveTextContent('No hay cambios')
})
it('limpia explícitamente con null sin alterar las demás preferencias', async () => {
  const { user } = await ready()
  patch.mockResolvedValueOnce({ ...saved, restriccion_acceso: null })
  await user.click(screen.getByLabelText('Sin restricciones de acceso definidas'))
  submit()
  await screen.findByRole('status')
  expect(patch).toHaveBeenCalledWith(saved.cliente_id, { restriccion_acceso: null })
  expect(screen.getByLabelText('Restricciones de acceso')).toBeDisabled()
  expect(screen.getByLabelText('Horario preferido')).toHaveValue('Mañana')
})
it('retira una confirmación anterior al editar y no la muestra ante un nuevo fallo', async () => {
  await ready()
  fireEvent.change(screen.getByLabelText('Referencia de ubicación'), { target: { value: 'Guardado' } })
  patch.mockResolvedValueOnce({ ...saved, referencia: 'Guardado' })
  submit()
  await screen.findByText('Preferencias guardadas correctamente.')
  fireEvent.change(screen.getByLabelText('Referencia de ubicación'), { target: { value: 'Sin confirmar' } })
  expect(screen.queryByText('Preferencias guardadas correctamente.')).not.toBeInTheDocument()
  patch.mockRejectedValueOnce(new PreferencesServiceError('unavailable'))
  submit()
  await screen.findByRole('alert')
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
  expect(screen.getByLabelText('Referencia de ubicación')).toHaveValue('Sin confirmar')
})
it('cancela cambios y puede consultar de nuevo el cliente guardado', async () => {
  const { user } = await ready()
  fireEvent.change(screen.getByLabelText('Horario preferido'), { target: { value: 'No guardar' } })
  await user.click(screen.getByRole('button', { name: 'Cancelar cambios' }))
  expect(screen.getByLabelText('Horario preferido')).toHaveValue('Mañana')
  expect(patch).not.toHaveBeenCalled()
  await user.click(screen.getByRole('button', { name: 'Consultar de nuevo u otro cliente' }))
  expect(screen.queryByLabelText('Horario preferido')).not.toBeInTheDocument()
  await consult()
  expect(await screen.findByLabelText('Horario preferido')).toHaveValue('Mañana')
  expect(get).toHaveBeenCalledTimes(2)
})
it.each(['network', 'validation', 'unavailable', 'unexpected'] as const)('conserva cambios al fallar guardado: %s', async kind => {
  await ready()
  patch.mockRejectedValueOnce(new PreferencesServiceError(kind, kind === 'validation' ? ['referencia'] : []))
  fireEvent.change(screen.getByLabelText('Referencia de ubicación'), { target: { value: 'Conservar' } })
  submit()
  expect(await screen.findByRole('alert')).toBeInTheDocument()
  expect(screen.getByLabelText('Referencia de ubicación')).toHaveValue('Conservar')
  expect(screen.queryByText('Preferencias guardadas correctamente.')).not.toBeInTheDocument()
  if (kind === 'network') expect(screen.getByRole('alert')).toHaveTextContent('No se pudo confirmar')
  if (kind === 'validation') expect(screen.getByLabelText('Referencia de ubicación')).toHaveAttribute('aria-invalid', 'true')
})
it.each(['not_found', 'network', 'unavailable', 'unexpected'] as const)('muestra error de consulta y permite reintentar: %s', async kind => {
  get.mockRejectedValueOnce(new PreferencesServiceError(kind))
  show(); await consult()
  expect(await screen.findByRole('alert')).toBeInTheDocument()
  expect(screen.queryByLabelText('Horario preferido')).not.toBeInTheDocument()
  await consult()
  expect(await screen.findByLabelText('Horario preferido')).toHaveValue('Mañana')
})
it.each(['unauthorized', 'forbidden'] as const)('maneja acceso denegado al consultar: %s', async kind => {
  get.mockRejectedValueOnce(new PreferencesServiceError(kind))
  const { expired } = show(); await consult()
  await screen.findByRole('alert')
  if (kind === 'unauthorized') expect(expired).toHaveBeenCalledOnce()
  else expect(screen.getByRole('button', { name: 'Consultar preferencias' })).toBeDisabled()
})
it.each(['unauthorized', 'forbidden', 'not_found'] as const)('bloquea escritura al perder acceso o cliente: %s', async kind => {
  const { expired } = await ready()
  patch.mockRejectedValueOnce(new PreferencesServiceError(kind))
  fireEvent.change(screen.getByLabelText('Referencia de ubicación'), { target: { value: 'Cambio' } })
  submit()
  await screen.findByRole('alert')
  if (kind === 'unauthorized') expect(expired).toHaveBeenCalledOnce()
  if (kind === 'forbidden') expect(screen.queryByLabelText('Horario preferido')).not.toBeInTheDocument()
})
it('no muestra excepciones privadas en carga ni guardado', async () => {
  get.mockRejectedValueOnce(new Error('private SQL'))
  show(); await consult()
  expect(await screen.findByRole('alert')).not.toHaveTextContent('private')
  await consult()
  await screen.findByLabelText('Horario preferido')
  patch.mockRejectedValueOnce(new Error('private SQL'))
  fireEvent.change(screen.getByLabelText('Referencia de ubicación'), { target: { value: 'Cambio' } })
  submit()
  expect(await screen.findByRole('alert')).not.toHaveTextContent('private')
})
it.each(['load', 'save'] as const)('ignora respuestas y errores tardíos después de salir: %s', async operation => {
  const pending = deferred<DeliveryPreferences>()
  const view = operation === 'load' ? show() : await ready()
  if (operation === 'load') { get.mockReturnValueOnce(pending.promise); await consult() }
  else {
    patch.mockReturnValueOnce(pending.promise)
    fireEvent.change(screen.getByLabelText('Referencia de ubicación'), { target: { value: 'Cambio' } }); submit()
  }
  view.unmount()
  await act(async () => { pending.reject(new PreferencesServiceError('unauthorized')); try { await pending.promise } catch { /* Expected rejection. */ } })
  expect(view.expired).not.toHaveBeenCalled()
})
