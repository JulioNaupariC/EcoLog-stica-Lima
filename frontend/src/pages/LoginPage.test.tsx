import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AuthServiceError, login } from '../services/auth'
import type { LoginResponse } from '../services/auth'
import { LoginPage } from './LoginPage'

vi.mock('../services/auth', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/auth')>()
  return { ...actual, login: vi.fn() }
})

const loginMock = vi.mocked(login)
const identity: LoginResponse = {
  usuario_id: '123e4567-e89b-12d3-a456-426614174000',
  rol: 'OPERADOR',
}

function renderPage() {
  const onLoginSuccess = vi.fn()
  render(<LoginPage onLoginSuccess={onLoginSuccess} />)
  return onLoginSuccess
}

function fill(email = 'User@example.test', password = 'private-password') {
  fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: email } })
  fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: password } })
}

function submit() {
  fireEvent.submit(screen.getByRole('button', { name: 'Iniciar sesión' }).closest('form')!)
}

describe('LoginPage', () => {
  beforeEach(() => {
    loginMock.mockReset()
    loginMock.mockResolvedValue(identity)
  })

  it('renderiza campos asociados, atributos requeridos y contraseña enmascarada', () => {
    renderPage()
    const email = screen.getByLabelText('Correo electrónico')
    const password = screen.getByLabelText('Contraseña')
    expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
    expect(email).toHaveAttribute('id', 'login-email')
    expect(email).toHaveAttribute('required')
    expect(email).toHaveAttribute('maxLength', '255')
    expect(email).toHaveAttribute('autocomplete', 'username')
    expect(email).toHaveAttribute('inputmode', 'email')
    expect(password).toHaveAttribute('type', 'password')
    expect(password).toHaveAttribute('required')
    expect(password).toHaveAttribute('autocomplete', 'current-password')
    expect(screen.getByRole('button', { name: 'Iniciar sesión' })).toBeEnabled()
  })

  it('valida campos vacíos y enfoca el primero', () => {
    renderPage()
    submit()
    expect(loginMock).not.toHaveBeenCalled()
    expect(screen.getByLabelText('Correo electrónico')).toHaveFocus()
    expect(screen.getByLabelText('Correo electrónico')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Contraseña')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Contraseña')).toHaveAttribute('aria-describedby', 'login-password-error')
    expect(screen.getByRole('alert')).toHaveTextContent('Revisa los datos ingresados.')
    expect(screen.getByText('El correo electrónico es obligatorio.')).toBeInTheDocument()
    expect(screen.getByText('La contraseña es obligatoria.')).toBeInTheDocument()
  })

  it('enfoca la contraseña si es el único campo inválido', () => {
    renderPage()
    fill('User@example.test', '')
    submit()
    expect(screen.getByLabelText('Contraseña')).toHaveFocus()
    expect(loginMock).not.toHaveBeenCalled()
  })

  it('rechaza más de 255 caracteres en correo sin enviarlo', () => {
    renderPage()
    fill('x'.repeat(256), 'private-password')
    submit()
    expect(loginMock).not.toHaveBeenCalled()
    expect(screen.getByLabelText('Correo electrónico')).toHaveFocus()
    expect(screen.getByText('El correo electrónico no puede superar 255 caracteres.')).toBeInTheDocument()
  })

  it('envía ambos valores sin transformarlos y comunica la identidad exacta', async () => {
    const onLoginSuccess = renderPage()
    fill(' User@example.test ', ' private-password ')
    submit()
    await waitFor(() => expect(onLoginSuccess).toHaveBeenCalledWith(identity))
    expect(loginMock).toHaveBeenCalledWith({
      email: ' User@example.test ',
      password: ' private-password ',
    })
    expect(screen.getByLabelText('Correo electrónico')).toHaveValue(' User@example.test ')
    expect(screen.getByLabelText('Contraseña')).toHaveValue('')
    expect(screen.queryByText(' private-password ')).not.toBeInTheDocument()
  })

  it('anuncia loading, deshabilita el botón e impide doble submit inmediatamente', async () => {
    let resolveLogin!: (value: LoginResponse) => void
    loginMock.mockImplementation(() => new Promise((resolve) => { resolveLogin = resolve }))
    const onLoginSuccess = renderPage()
    fill()
    const form = screen.getByRole('button', { name: 'Iniciar sesión' }).closest('form')!
    fireEvent.submit(form)
    fireEvent.submit(form)
    expect(loginMock).toHaveBeenCalledTimes(1)
    expect(form).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByRole('status')).toHaveTextContent('Iniciando sesión…')
    expect(screen.getByRole('button', { name: 'Iniciando sesión…' })).toBeDisabled()
    act(() => { resolveLogin(identity) })
    await waitFor(() => expect(onLoginSuccess).toHaveBeenCalledWith(identity))
    expect(form).toHaveAttribute('aria-busy', 'false')
  })

  it.each([
    ['unauthorized', 'Credenciales inválidas.'],
    ['unavailable', 'El servicio no está disponible en este momento.'],
    ['network', 'No se pudo conectar con el servicio.'],
    ['unexpected', 'No se pudo iniciar sesión.'],
  ] as const)('muestra un error %s seguro, conserva correo y limpia contraseña', async (kind, message) => {
    loginMock.mockRejectedValue(new AuthServiceError(kind, message))
    const onLoginSuccess = renderPage()
    fill()
    submit()
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(message)
    await waitFor(() => { expect(alert).toHaveFocus() })
    expect(alert).not.toHaveTextContent('private-password')
    expect(screen.getByLabelText('Correo electrónico')).toHaveValue('User@example.test')
    expect(screen.getByLabelText('Contraseña')).toHaveValue('')
    expect(screen.getByRole('button', { name: 'Iniciar sesión' })).toBeEnabled()
    expect(onLoginSuccess).not.toHaveBeenCalled()
  })

  it('muestra errores 422 solo en campos reconocidos y enfoca el primero', async () => {
    loginMock.mockRejectedValue(new AuthServiceError('validation', 'Revisa los datos ingresados.', {
      status: 422,
      issues: [
        { field: 'email', message: 'Revisa el correo electrónico.' },
        { field: 'password', message: 'Revisa la contraseña.' },
      ],
    }))
    renderPage()
    fill()
    submit()
    expect(await screen.findByText('Revisa el correo electrónico.')).toBeInTheDocument()
    expect(screen.getByText('Revisa la contraseña.')).toBeInTheDocument()
    expect(screen.getByLabelText('Correo electrónico')).toHaveFocus()
    expect(screen.getByLabelText('Correo electrónico')).toHaveAttribute('aria-describedby', 'login-email-error')
    expect(screen.getByLabelText('Contraseña')).toHaveValue('')
    expect(screen.getByRole('alert')).not.toHaveTextContent('private-password')
  })

  it('enfoca la contraseña si es el único error 422 de campo', async () => {
    loginMock.mockRejectedValue(new AuthServiceError('validation', 'Revisa los datos ingresados.', {
      issues: [{ field: 'password', message: 'Revisa la contraseña.' }],
    }))
    renderPage()
    fill()
    submit()
    expect(await screen.findByText('Revisa la contraseña.')).toBeInTheDocument()
    expect(screen.getByLabelText('Contraseña')).toHaveFocus()
  })

  it('limpia errores al editar y permite un nuevo intento', async () => {
    const user = userEvent.setup()
    renderPage()
    submit()
    await user.type(screen.getByLabelText('Correo electrónico'), 'User@example.test')
    expect(screen.getByLabelText('Correo electrónico')).toHaveAttribute('aria-invalid', 'false')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    await user.type(screen.getByLabelText('Contraseña'), 'private-password')
    expect(screen.getByLabelText('Contraseña')).toHaveAttribute('aria-invalid', 'false')
    submit()
    await waitFor(() => expect(loginMock).toHaveBeenCalledTimes(1))
  })

  it('presenta un mensaje seguro si ocurre un rechazo no tipado', async () => {
    loginMock.mockRejectedValue(new Error('private-password'))
    renderPage()
    fill()
    submit()
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo iniciar sesión.')
    expect(screen.getByRole('alert')).not.toHaveTextContent('private-password')
    expect(screen.getByLabelText('Contraseña')).toHaveValue('')
  })
})
