import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LoginPage } from './LoginPage'

it('«¿Olvidaste tu contraseña?» abre un aviso en línea sin pedir el correo', async () => {
  render(<LoginPage onLoginSuccess={vi.fn()} />)
  const user = userEvent.setup()
  const link = screen.getByRole('button', { name: '¿Olvidaste tu contraseña?' })
  expect(link).toHaveAttribute('aria-expanded', 'false')
  expect(screen.queryByText(/Pide al Administrador/u)).not.toBeVisible()
  const inputsBefore = document.querySelectorAll('input').length

  await user.click(link)
  expect(link).toHaveAttribute('aria-expanded', 'true')
  expect(screen.getByRole('note')).toHaveTextContent(
    'Pide al Administrador que restablezca tu contraseña. Por seguridad, no enviamos contraseñas por correo.')
  expect(document.querySelectorAll('input')).toHaveLength(inputsBefore)

  await user.click(link)
  expect(link).toHaveAttribute('aria-expanded', 'false')
})
