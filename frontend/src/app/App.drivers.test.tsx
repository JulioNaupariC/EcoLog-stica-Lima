import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useNavigate } from 'react-router-dom'
import { App } from './App'
import { login, logout } from '../services/auth'
import type { AuthRole } from '../services/auth'
import { DriverServiceError, listDrivers } from '../services/drivers'

vi.mock('../services/auth', async original => ({ ...await original<typeof import('../services/auth')>(), login: vi.fn(), logout: vi.fn() }))
vi.mock('../services/drivers', async original => ({ ...await original<typeof import('../services/drivers')>(), listDrivers: vi.fn() }))
function Controls() {
  const navigate = useNavigate()
  return <button onClick={() => { void navigate('/conductores') }}>Abrir ruta conductores</button>
}
function show(path = '/login') {
  render(<MemoryRouter initialEntries={[path]}><Controls /><App /></MemoryRouter>)
}
async function signIn(role: AuthRole) {
  vi.mocked(login).mockResolvedValue({ usuario_id: '123e4567-e89b-12d3-a456-426614174000', rol: role })
  fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: 'test@example.test' } })
  fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'synthetic-password' } })
  fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
  await screen.findByRole('heading', { name: 'Rutas sostenibles para Lima' })
}
beforeEach(() => {
  vi.mocked(listDrivers).mockReset().mockResolvedValue({ items: [], page: 1, page_size: 10, total: 0 })
  vi.mocked(logout).mockResolvedValue()
})
it('redirige acceso anónimo al login', async () => {
  show('/conductores')
  expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
  expect(listDrivers).not.toHaveBeenCalled()
})
it.each(['ADMINISTRADOR', 'OPERADOR'] as const)('habilita navegación y gestión para %s', async role => {
  show()
  await signIn(role)
  fireEvent.click(screen.getByRole('link', { name: 'Conductores' }))
  expect(await screen.findByRole('heading', { name: 'Conductores' })).toBeInTheDocument()
  expect(await screen.findByRole('button', { name: 'Nuevo conductor' })).toBeEnabled()
})
it.each(['CONDUCTOR', 'AUDITOR', 'ANALISTA'] as const)('deniega ruta y oculta enlace a %s', async role => {
  show()
  await signIn(role)
  expect(screen.queryByRole('link', { name: 'Conductores' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Abrir ruta conductores' }))
  expect(await screen.findByRole('heading', { name: 'Acceso denegado' })).toBeInTheDocument()
  expect(listDrivers).not.toHaveBeenCalled()
})
it('401 de API limpia identidad y vuelve al login', async () => {
  show()
  await signIn('OPERADOR')
  vi.mocked(listDrivers).mockRejectedValueOnce(new DriverServiceError('unauthorized'))
  fireEvent.click(screen.getByRole('link', { name: 'Conductores' }))
  expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
  await waitFor(() => expect(screen.queryByText('Rol: OPERADOR')).not.toBeInTheDocument())
  expect(screen.getByRole('alert')).toHaveTextContent('Tu sesión ha vencido')
})
