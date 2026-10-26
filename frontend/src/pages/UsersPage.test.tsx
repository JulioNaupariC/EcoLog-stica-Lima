import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UsersPage } from './UsersPage'
import { listUsers, resetPassword, UserServiceError } from '../services/users'
import type { UserPage } from '../services/users'

vi.mock('../services/users', async original => {
  const actual = await original<typeof import('../services/users')>()
  return { ...actual, listUsers: vi.fn(), resetPassword: vi.fn() }
})
const listMock = vi.mocked(listUsers)
const resetMock = vi.mocked(resetPassword)
const ADMIN_ID = '000e4567-e89b-12d3-a456-426614174000'
const OPERATOR_ID = '123e4567-e89b-12d3-a456-426614174000'
const TEMPORARY = 'Synthetic16Chars'
const page: UserPage = {
  items: [
    { usuario_id: ADMIN_ID, email: 'admin.demo@example.test', rol: 'ADMINISTRADOR', estado: 'ACTIVO', debe_cambiar_contrasena: false },
    { usuario_id: OPERATOR_ID, email: 'operador.demo@example.test', rol: 'OPERADOR', estado: 'ACTIVO', debe_cambiar_contrasena: false },
    { usuario_id: '223e4567-e89b-12d3-a456-426614174000', email: 'auditor.demo@example.test', rol: 'AUDITOR', estado: 'INACTIVO', debe_cambiar_contrasena: true },
  ],
  page: 1, page_size: 20, total: 3,
}

async function ready() {
  const expired = vi.fn()
  render(<UsersPage ownId={ADMIN_ID} onSessionExpired={expired} />)
  await screen.findByRole('region', { name: 'Cuentas registradas' })
  return { user: userEvent.setup(), expired }
}
function resetButton(email: string) {
  return screen.getByRole('button', { name: `Restablecer contraseña de ${email}` })
}

beforeEach(() => {
  listMock.mockReset().mockResolvedValue(page)
  resetMock.mockReset().mockResolvedValue({ contrasena_temporal: TEMPORARY, expira_en: '2026-10-26T12:00:00Z' })
})

it('lista correo, rol, estado e insignia, sin restablecer la propia cuenta ni una inactiva', async () => {
  await ready()
  const table = screen.getByRole('table')
  expect(within(table).getByText('operador.demo@example.test')).toBeInTheDocument()
  expect(within(table).getByText('Operador')).toBeInTheDocument()
  expect(within(table).getByText('Debe cambiar contraseña')).toBeInTheDocument()
  expect(within(table).getByText('Inactivo')).toBeInTheDocument()
  expect(resetButton('admin.demo@example.test')).toBeDisabled()
  expect(resetButton('auditor.demo@example.test')).toBeDisabled()
  expect(resetButton('operador.demo@example.test')).toBeEnabled()
})

it('restablece → confirma → ve y copia → Listo borra la temporal y devuelve el foco', async () => {
  const { user } = await ready()
  const writeText = vi.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
  const origin = resetButton('operador.demo@example.test')
  await user.click(origin)

  const confirm = screen.getByRole('alertdialog', { name: 'Restablecer contraseña' })
  expect(confirm).toHaveTextContent('¿Restablecer la contraseña de operador.demo@example.test? Se cerrarán sus sesiones activas.')
  expect(within(confirm).getByRole('button', { name: 'Cancelar' })).toHaveFocus()
  await user.click(within(confirm).getByRole('button', { name: 'Restablecer' }))

  const shown = await screen.findByRole('dialog', { name: 'Contraseña temporal' })
  expect(resetMock).toHaveBeenCalledWith(OPERATOR_ID)
  expect(within(shown).getByTestId('temporary-password')).toHaveTextContent(TEMPORARY)
  expect(shown).toHaveTextContent('No se volverá a mostrar · vence en 24 h')
  await user.click(within(shown).getByRole('button', { name: 'Copiar' }))
  expect(writeText).toHaveBeenCalledWith(TEMPORARY)
  expect(within(shown).getByRole('status')).toHaveTextContent('Contraseña copiada.')

  await user.click(within(shown).getByRole('button', { name: 'Listo' }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(document.body).not.toHaveTextContent(TEMPORARY)
  expect(resetButton('operador.demo@example.test')).toHaveFocus()
  const row = resetButton('operador.demo@example.test').closest('tr')!
  expect(within(row).getByText('Debe cambiar contraseña')).toBeInTheDocument()
})

it('Escape cancela la confirmación sin restablecer y devuelve el foco', async () => {
  const { user } = await ready()
  await user.click(resetButton('operador.demo@example.test'))
  await user.keyboard('{Escape}')
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
  expect(resetMock).not.toHaveBeenCalled()
  expect(resetButton('operador.demo@example.test')).toHaveFocus()
})

it('Escape en el diálogo de la temporal también la borra', async () => {
  const { user } = await ready()
  await user.click(resetButton('operador.demo@example.test'))
  await user.click(screen.getByRole('button', { name: 'Restablecer' }))
  await screen.findByRole('dialog', { name: 'Contraseña temporal' })
  await user.keyboard('{Escape}')
  expect(document.body).not.toHaveTextContent(TEMPORARY)
})

it('el foco queda atrapado dentro del diálogo', async () => {
  const { user } = await ready()
  await user.click(resetButton('operador.demo@example.test'))
  const dialog = screen.getByRole('alertdialog')
  for (let index = 0; index < 4; index++) {
    await user.tab()
    expect(dialog).toContainElement(document.activeElement as HTMLElement)
  }
  await user.tab({ shift: true })
  expect(dialog).toContainElement(document.activeElement as HTMLElement)
})

it('si falla, informa sin culpar y deja reintentar', async () => {
  const { user } = await ready()
  resetMock.mockRejectedValueOnce(new UserServiceError('network'))
  await user.click(resetButton('operador.demo@example.test'))
  await user.click(screen.getByRole('button', { name: 'Restablecer' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo restablecer. Intenta de nuevo o revisa tu conexión.')
  await user.click(screen.getByRole('button', { name: 'Restablecer' }))
  expect(await screen.findByRole('dialog', { name: 'Contraseña temporal' })).toBeInTheDocument()
})

it('muestra conflictos con salida y avisa si no se puede copiar', async () => {
  const { user } = await ready()
  resetMock.mockRejectedValueOnce(new UserServiceError('conflict'))
  await user.click(resetButton('operador.demo@example.test'))
  await user.click(screen.getByRole('button', { name: 'Restablecer' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Actualiza el listado')
  Object.defineProperty(navigator, 'clipboard', { value: { writeText: vi.fn().mockRejectedValue(new Error('denied')) }, configurable: true })
  await user.click(screen.getByRole('button', { name: 'Restablecer' }))
  await user.click(await screen.findByRole('button', { name: 'Copiar' }))
  expect(await screen.findByRole('status')).toHaveTextContent('No se pudo copiar. Selecciona la contraseña y cópiala manualmente.')
})

it('una sesión vencida al restablecer o listar vuelve al login', async () => {
  const { user, expired } = await ready()
  resetMock.mockRejectedValueOnce(new UserServiceError('unauthorized'))
  await user.click(resetButton('operador.demo@example.test'))
  await user.click(screen.getByRole('button', { name: 'Restablecer' }))
  await waitFor(() => expect(expired).toHaveBeenCalledTimes(1))
  listMock.mockRejectedValueOnce(new UserServiceError('unauthorized'))
  await user.click(screen.getByRole('button', { name: 'Actualizar listado' }))
  await waitFor(() => expect(expired).toHaveBeenCalledTimes(2))
  expect(screen.getByRole('alert')).toHaveTextContent('Tu sesión ha vencido')
})

it('si el listado falla, ofrece reintentar; y pagina', async () => {
  listMock.mockRejectedValueOnce(new UserServiceError('unavailable'))
  render(<UsersPage ownId={ADMIN_ID} onSessionExpired={vi.fn()} />)
  const user = userEvent.setup()
  expect(await screen.findByRole('alert')).toHaveTextContent('Intenta de nuevo en unos minutos')
  listMock.mockResolvedValue({ ...page, total: 45 })
  await user.click(screen.getByRole('button', { name: 'Reintentar carga' }))
  expect(await screen.findByText('Página 1 de 3')).toBeInTheDocument()
  listMock.mockResolvedValue({ ...page, items: [], page: 2, total: 45 })
  await user.click(screen.getByRole('button', { name: 'Siguiente' }))
  expect(await screen.findByText('Sin cuentas en esta página')).toBeInTheDocument()
  expect(listMock).toHaveBeenLastCalledWith(2, 20)
})
