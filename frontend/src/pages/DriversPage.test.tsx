import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DriversPage } from './DriversPage'
import { createDriver, DriverServiceError, getDriver, listDrivers, updateDriver } from '../services/drivers'
import type { DriverDetail, DriverPage } from '../services/drivers'

vi.mock('../services/drivers', async (original) => {
  const actual = await original<typeof import('../services/drivers')>()
  return { ...actual, createDriver: vi.fn(), getDriver: vi.fn(), listDrivers: vi.fn(), updateDriver: vi.fn() }
})
const listMock = vi.mocked(listDrivers)
const createMock = vi.mocked(createDriver)
const getMock = vi.mocked(getDriver)
const updateMock = vi.mocked(updateDriver)
const driver: DriverDetail = {
  conductor_id: '123e4567-e89b-12d3-a456-426614174000', usuario_id: '223e4567-e89b-12d3-a456-426614174000',
  nombre: 'Rosa Prueba', dni: '01234567', licencia_numero: 'LIC-01', licencia_vigente_hasta: '2099-12-31',
  experiencia_anios: 2, telefono: '+51987654321', punto_partida: 'Base Lima',
  disponible_desde: '2099-10-09T13:15:00.123456Z', disponible_hasta: '2099-10-09T22:15:00Z',
  estado: 'ACTIVO', habilitado_asignacion: true,
}
const result: DriverPage = { items: [driver], page: 1, page_size: 10, total: 1 }
const fields = {
  nombre: 'Rosa Prueba', dni: '01234567', licencia_numero: 'LIC-01', licencia_vigente_hasta: '2099-12-31',
  experiencia_anios: '2', telefono: '+51987654321', punto_partida: 'Base Lima',
  disponible_desde: '2099-10-09T08:15', disponible_hasta: '2099-10-09T17:15',
  email: 'rosa@example.test', password: 'synthetic-password',
}
function fill() {
  for (const [field, value] of Object.entries(fields)) fireEvent.change(document.getElementById('driver-' + field)!, { target: { value } })
}
function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: Error) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
async function ready() {
  const expired = vi.fn()
  const view = render(<DriversPage onSessionExpired={expired} />)
  await screen.findByRole('heading', { name: 'Rosa Prueba' })
  return { ...view, expired, user: userEvent.setup() }
}
beforeEach(() => {
  listMock.mockReset().mockResolvedValue(result)
  getMock.mockReset().mockResolvedValue(driver)
  createMock.mockReset().mockResolvedValue(driver)
  updateMock.mockReset().mockResolvedValue(driver)
})

it('muestra carga, vacío y no presenta datos ficticios', async () => {
  const pending = deferred<DriverPage>()
  listMock.mockReturnValue(pending.promise)
  render(<DriversPage onSessionExpired={vi.fn()} />)
  expect(screen.getByRole('status')).toHaveTextContent('Cargando conductores')
  expect(screen.getByRole('region', { name: 'Conductores registrados' })).toHaveAttribute('aria-busy', 'true')
  await act(async () => { pending.resolve({ ...result, items: [], total: 0 }); await pending.promise })
  expect(screen.getByRole('status')).toHaveTextContent('Aún no hay conductores registrados')
})
it('lista sin DNI ni teléfono, carga perfil con foco y permite cancelar', async () => {
  const { user } = await ready()
  expect(screen.queryByText(driver.dni)).not.toBeInTheDocument()
  expect(screen.queryByText(driver.telefono)).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Ver y editar Rosa Prueba' }))
  expect(await screen.findByRole('heading', { name: 'Perfil de Rosa Prueba' })).toHaveFocus()
  expect(screen.getByLabelText('DNI')).toHaveValue('01234567')
  expect(screen.queryByLabelText('Contraseña inicial')).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Cancelar' }))
  expect(screen.getByRole('heading', { name: 'Conductores registrados' })).toHaveFocus()
})
it('valida antes de enviar y registra contra el servicio una sola vez', async () => {
  const { user } = await ready()
  await user.click(screen.getByRole('button', { name: 'Nuevo conductor' }))
  fireEvent.submit(screen.getByRole('form', { name: 'Registrar conductor' }))
  expect(await screen.findByRole('alert')).toHaveFocus()
  expect(createMock).not.toHaveBeenCalled()
  fill()
  const pending = deferred<DriverDetail>()
  createMock.mockReturnValue(pending.promise)
  fireEvent.submit(screen.getByRole('form', { name: 'Registrar conductor' }))
  fireEvent.submit(screen.getByRole('form', { name: 'Registrar conductor' }))
  expect(createMock).toHaveBeenCalledTimes(1)
  expect(createMock.mock.calls[0][0]).toMatchObject({ dni: '01234567', disponible_desde: '2099-10-09T13:15:00.000Z' })
  expect(screen.getByRole('button', { name: 'Guardando…' })).toBeDisabled()
  await act(async () => { pending.resolve(driver); await pending.promise })
  expect(await screen.findByText('Conductor registrado correctamente.')).toBeInTheDocument()
  expect(screen.queryByLabelText('Contraseña inicial')).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Consultar perfil guardado' }))
  expect(await screen.findByRole('heading', { name: 'Perfil de Rosa Prueba' })).toBeInTheDocument()
})
it('edita sólo datos modificados, preserva fechas y retira disponibilidad', async () => {
  const { user } = await ready()
  await user.click(screen.getByRole('button', { name: 'Ver y editar Rosa Prueba' }))
  await screen.findByRole('heading', { name: 'Perfil de Rosa Prueba' })
  fireEvent.submit(screen.getByRole('form', { name: 'Editar conductor' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('No hay cambios para guardar')
  expect(updateMock).not.toHaveBeenCalled()
  fireEvent.change(screen.getByLabelText('Teléfono'), { target: { value: '+51987654322' } })
  fireEvent.submit(screen.getByRole('form', { name: 'Editar conductor' }))
  await screen.findByText('Conductor actualizado correctamente.')
  expect(updateMock).toHaveBeenLastCalledWith(driver.conductor_id, { telefono: '+51987654322' })
  await user.click(screen.getByRole('button', { name: 'Ver y editar Rosa Prueba' }))
  await screen.findByRole('heading', { name: 'Perfil de Rosa Prueba' })
  await user.click(screen.getByRole('checkbox'))
  expect(screen.getByLabelText('Disponible desde (hora de Lima)')).toBeDisabled()
  fireEvent.submit(screen.getByRole('form', { name: 'Editar conductor' }))
  await waitFor(() => expect(updateMock).toHaveBeenLastCalledWith(driver.conductor_id, { disponible_desde: null, disponible_hasta: null }))
})
it.each(['conflict', 'network', 'validation'] as const)('mantiene campos y limpia contraseña ante error %s', async kind => {
  const { user } = await ready()
  createMock.mockRejectedValue(new DriverServiceError(kind, kind === 'validation' ? ['dni'] : []))
  await user.click(screen.getByRole('button', { name: 'Nuevo conductor' }))
  fill()
  fireEvent.submit(screen.getByRole('form', { name: 'Registrar conductor' }))
  expect(await screen.findByRole('alert')).toBeInTheDocument()
  await waitFor(() => expect(screen.getByLabelText('Contraseña inicial')).toHaveValue(''))
  expect(screen.getByLabelText('DNI')).toHaveValue('01234567')
  if (kind === 'validation') expect(screen.getByLabelText('DNI')).toHaveAttribute('aria-invalid', 'true')
})
it('informa error de carga y permite reintentar', async () => {
  listMock.mockRejectedValueOnce(new DriverServiceError('unavailable'))
  render(<DriversPage onSessionExpired={vi.fn()} />)
  expect(await screen.findByRole('alert')).toHaveTextContent('El servicio no está disponible')
  await userEvent.click(screen.getByRole('button', { name: 'Reintentar carga' }))
  expect(await screen.findByRole('heading', { name: 'Rosa Prueba' })).toBeInTheDocument()
})
it('pagina y actualiza desde el backend', async () => {
  listMock.mockResolvedValue({ ...result, total: 11 })
  const { user } = await ready()
  listMock.mockResolvedValueOnce({ ...result, page: 2, total: 11 })
  await user.click(screen.getByRole('button', { name: 'Siguiente' }))
  expect(await screen.findByText('Página 2 de 2')).toBeInTheDocument()
  expect(listMock).toHaveBeenLastCalledWith(2)
  await user.click(screen.getByRole('button', { name: 'Anterior' }))
  expect(await screen.findByText('Página 1 de 2')).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Actualizar listado' }))
  await waitFor(() => expect(listMock).toHaveBeenCalledTimes(4))
})
it('expira sesión, bloquea acceso denegado y oculta datos previamente cargados', async () => {
  const { user, expired } = await ready()
  listMock.mockRejectedValueOnce(new DriverServiceError('unauthorized'))
  await user.click(screen.getByRole('button', { name: 'Actualizar listado' }))
  await waitFor(() => expect(expired).toHaveBeenCalledOnce())
  listMock.mockRejectedValueOnce(new DriverServiceError('forbidden'))
  await user.click(screen.getByRole('button', { name: 'Reintentar carga' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Nuevo conductor' })).toBeDisabled())
  expect(screen.queryByRole('heading', { name: 'Rosa Prueba' })).not.toBeInTheDocument()
})
it('informa perfil inexistente y bloquea error de permiso al guardar', async () => {
  const { user } = await ready()
  getMock.mockRejectedValueOnce(new DriverServiceError('not_found'))
  await user.click(screen.getByRole('button', { name: 'Ver y editar Rosa Prueba' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('El conductor ya no está disponible')
  await user.click(screen.getByRole('button', { name: 'Nuevo conductor' }))
  fill()
  createMock.mockRejectedValueOnce(new DriverServiceError('forbidden'))
  fireEvent.submit(screen.getByRole('form', { name: 'Registrar conductor' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Nuevo conductor' })).toBeDisabled())
})
it('ignora respuestas tardías después de salir de la página', async () => {
  const pending = deferred<DriverPage>()
  listMock.mockReturnValueOnce(pending.promise)
  const expired = vi.fn()
  const view = render(<DriversPage onSessionExpired={expired} />)
  view.unmount()
  await act(async () => { pending.reject(new DriverServiceError('unauthorized')); try { await pending.promise } catch { /* intentional rejection */ } })
  expect(expired).not.toHaveBeenCalled()
})

it('maneja errores inesperados sin mostrar detalles privados', async () => {
  listMock.mockRejectedValueOnce(new Error('private SQL'))
  const expired = vi.fn()
  render(<DriversPage onSessionExpired={expired} />)
  expect(await screen.findByRole('alert')).not.toHaveTextContent('private SQL')
  await userEvent.click(screen.getByRole('button', { name: 'Reintentar carga' }))
  await screen.findByRole('heading', { name: 'Rosa Prueba' })
  getMock.mockRejectedValueOnce(new Error('private SQL'))
  await userEvent.click(screen.getByRole('button', { name: 'Ver y editar Rosa Prueba' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo consultar el perfil.')
  await userEvent.click(screen.getByRole('button', { name: 'Ver y editar Rosa Prueba' }))
  await screen.findByRole('heading', { name: 'Perfil de Rosa Prueba' })
  updateMock.mockRejectedValueOnce(new Error('private SQL'))
  fireEvent.change(screen.getByLabelText('Nombre completo'), { target: { value: 'Otro nombre' } })
  fireEvent.submit(screen.getByRole('form', { name: 'Editar conductor' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo guardar el conductor.')
})
it('representa un perfil inactivo sin franja y páginas sin registros', async () => {
  const inactive = { ...driver, estado: 'INACTIVO' as const, habilitado_asignacion: false,
    disponible_desde: null, disponible_hasta: null }
  listMock.mockResolvedValueOnce({ ...result, total: 11, items: [inactive] })
  const { user } = await ready()
  expect(screen.getByText('Inactivo')).toBeInTheDocument()
  expect(screen.getByText('Sin disponibilidad')).toBeInTheDocument()
  getMock.mockResolvedValueOnce(inactive)
  await user.click(screen.getByRole('button', { name: 'Ver y editar Rosa Prueba' }))
  await screen.findByRole('heading', { name: 'Perfil de Rosa Prueba' })
  expect(screen.getByRole('checkbox')).toBeChecked()
  await user.click(screen.getByRole('checkbox'))
  fireEvent.submit(screen.getByRole('form', { name: 'Editar conductor' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Revisa los campos indicados')
  await user.click(screen.getByRole('button', { name: 'Cancelar' }))
  listMock.mockResolvedValueOnce({ ...result, page: 2, total: 11, items: [] })
  await user.click(screen.getByRole('button', { name: 'Siguiente' }))
  expect(await screen.findByText('No hay conductores en esta página.')).toBeInTheDocument()
})
