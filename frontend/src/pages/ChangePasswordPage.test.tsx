import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChangePasswordPage } from './ChangePasswordPage'
import { changePassword, UserServiceError } from '../services/users'
import { validatePasswordField } from '../domain/passwordForm'

vi.mock('../services/users', async original => {
  const actual = await original<typeof import('../services/users')>()
  return { ...actual, changePassword: vi.fn() }
})
const changeMock = vi.mocked(changePassword)

function setup(required = true) {
  const props = { onChanged: vi.fn(), onSessionExpired: vi.fn(), onLogout: vi.fn() }
  render(<ChangePasswordPage required={required} onChanged={props.onChanged}
    onSessionExpired={props.onSessionExpired} onLogout={required ? props.onLogout : undefined} />)
  return { user: userEvent.setup(), ...props }
}
const current = () => screen.getByLabelText(/^Contraseña (temporal|actual)$/u)
const next = () => screen.getByLabelText('Nueva contraseña (mínimo 12 caracteres)')
const confirm = () => screen.getByLabelText('Confirmar nueva contraseña')

beforeEach(() => { changeMock.mockReset().mockResolvedValue() })

it('muestra etiquetas visibles y el modo obligatorio con salida', async () => {
  const { user, onLogout } = setup()
  expect(current()).toHaveAccessibleName('Contraseña temporal')
  expect(next()).toHaveAttribute('type', 'password')
  expect(confirm()).toHaveAttribute('autocomplete', 'new-password')
  await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }))
  expect(onLogout).toHaveBeenCalled()
})

it('el cambio voluntario pide la contraseña actual', () => {
  setup(false)
  expect(current()).toHaveAccessibleName('Contraseña actual')
  expect(screen.queryByRole('button', { name: 'Cerrar sesión' })).not.toBeInTheDocument()
})

it('valida 12 caracteres al salir del campo y limpia el error al corregir', async () => {
  const { user } = setup()
  await user.type(next(), 'corta-11ch')
  expect(screen.queryByText('Usa al menos 12 caracteres.')).not.toBeInTheDocument()
  await user.tab()
  expect(screen.getByText('Usa al menos 12 caracteres.')).toBeInTheDocument()
  expect(next()).toHaveAttribute('aria-invalid', 'true')
  expect(next()).toHaveAccessibleDescription(/Usa al menos 12 caracteres/u)
  await user.type(next(), 'xx')
  expect(screen.queryByText('Usa al menos 12 caracteres.')).not.toBeInTheDocument()
})

it('valida la coincidencia y que la nueva sea distinta de la actual', async () => {
  const { user } = setup()
  await user.type(current(), 'temporal-16-char')
  await user.type(next(), 'temporal-16-char')
  await user.tab()
  expect(screen.getByText('Elige una contraseña distinta de la actual.')).toBeInTheDocument()
  await user.clear(next())
  await user.type(next(), 'definitiva-larga')
  await user.type(confirm(), 'definitiva-larg')
  await user.tab()
  expect(screen.getByText('Las contraseñas no coinciden. Escríbela de nuevo.')).toBeInTheDocument()
  await user.type(confirm(), 'a')
  expect(screen.queryByText('Las contraseñas no coinciden. Escríbela de nuevo.')).not.toBeInTheDocument()
})

it('guarda y avisa al terminar; no envía si hay errores', async () => {
  const { user, onChanged } = setup()
  await user.click(screen.getByRole('button', { name: 'Guardar contraseña' }))
  expect(changeMock).not.toHaveBeenCalled()
  expect(current()).toHaveFocus()
  await user.type(current(), 'temporal-16-char')
  await user.type(next(), 'definitiva-larga')
  await user.type(confirm(), 'definitiva-larga')
  await user.click(screen.getByRole('button', { name: 'Guardar contraseña' }))
  expect(changeMock).toHaveBeenCalledWith('temporal-16-char', 'definitiva-larga')
  await waitFor(() => expect(onChanged).toHaveBeenCalled())
})

it('si la actual no coincide, la limpia y explica el bloqueo sin culpar', async () => {
  const { user } = setup()
  changeMock.mockRejectedValueOnce(new UserServiceError('current_invalid'))
  await user.type(current(), 'temporal-16-char')
  await user.type(next(), 'definitiva-larga')
  await user.type(confirm(), 'definitiva-larga')
  await user.click(screen.getByRole('button', { name: 'Guardar contraseña' }))
  expect(await screen.findByText(/no coincide\. Revísala e intenta de nuevo/u)).toBeInTheDocument()
  expect(current()).toHaveValue('')
  expect(current()).toHaveFocus()
})

it('errores de red con salida y sesión vencida al login', async () => {
  const { user, onSessionExpired } = setup()
  changeMock.mockRejectedValueOnce(new UserServiceError('network'))
  await user.type(current(), 'temporal-16-char')
  await user.type(next(), 'definitiva-larga')
  await user.type(confirm(), 'definitiva-larga')
  await user.click(screen.getByRole('button', { name: 'Guardar contraseña' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Revisa tu conexión e intenta de nuevo')
  changeMock.mockRejectedValueOnce(new UserServiceError('unauthorized'))
  await user.click(screen.getByRole('button', { name: 'Guardar contraseña' }))
  await waitFor(() => expect(onSessionExpired).toHaveBeenCalled())
  changeMock.mockRejectedValueOnce(new Error('raro'))
  await user.click(screen.getByRole('button', { name: 'Guardar contraseña' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo guardar la contraseña')
})

it('reglas puras de los campos', () => {
  const values = { current: 'a', next: 'b'.repeat(12), confirm: 'b'.repeat(12) }
  expect(validatePasswordField('current', { ...values, current: '' })).toBe('Escribe tu contraseña actual.')
  expect(validatePasswordField('next', values)).toBeUndefined()
  expect(validatePasswordField('confirm', values)).toBeUndefined()
})
