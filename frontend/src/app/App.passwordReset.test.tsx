import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import { App } from './App'
import { login, logout } from '../services/auth'
import type { AuthRole, LoginResponse } from '../services/auth'
import { changePassword, listUsers } from '../services/users'

vi.mock('../services/auth', async original => {
  const actual = await original<typeof import('../services/auth')>()
  return { ...actual, login: vi.fn(), logout: vi.fn() }
})
vi.mock('../services/users', async original => {
  const actual = await original<typeof import('../services/users')>()
  return { ...actual, changePassword: vi.fn(), listUsers: vi.fn() }
})
const loginMock = vi.mocked(login)
const logoutMock = vi.mocked(logout)
const changeMock = vi.mocked(changePassword)
const listUsersMock = vi.mocked(listUsers)
const usuario_id = '123e4567-e89b-12d3-a456-426614174000'
const fetchMock = vi.fn<typeof fetch>()

function Controls() {
  const navigate = useNavigate()
  const location = useLocation()
  return <aside aria-label="Controles de prueba">
    <span data-testid="path">{location.pathname}</span>
    {['/vehiculos', '/usuarios', '/'].map(path =>
      <button key={path} type="button" onClick={() => { void navigate(path) }}>Ir a {path}</button>)}
  </aside>
}

async function signIn(identity: LoginResponse) {
  render(<MemoryRouter initialEntries={['/login']}><Controls /><App /></MemoryRouter>)
  const user = userEvent.setup()
  loginMock.mockResolvedValue(identity)
  await user.click(screen.getByLabelText('Correo electrónico'))
  await user.paste('persona@example.test')
  await user.click(screen.getByLabelText('Contraseña'))
  await user.paste('synthetic-password')
  await user.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
  return user
}

async function fillChange(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByLabelText('Contraseña temporal'))
  await user.paste('temporal-16-char')
  await user.click(screen.getByLabelText('Nueva contraseña (mínimo 12 caracteres)'))
  await user.paste('definitiva-larga')
  await user.click(screen.getByLabelText('Confirmar nueva contraseña'))
  await user.paste('definitiva-larga')
  await user.click(screen.getByRole('button', { name: 'Guardar contraseña' }))
}

beforeEach(() => {
  vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test')
  fetchMock.mockReset().mockResolvedValue(new Response(JSON.stringify({ detail: 'Acceso denegado' }), { status: 403 }))
  vi.stubGlobal('fetch', fetchMock)
  loginMock.mockReset()
  logoutMock.mockReset().mockResolvedValue()
  changeMock.mockReset().mockResolvedValue()
  listUsersMock.mockReset().mockResolvedValue({ items: [], page: 1, page_size: 20, total: 0 })
  sessionStorage.clear()
})
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals() })

it('login con temporal redirige al cambio obligatorio y bloquea las demás rutas', async () => {
  const user = await signIn({ usuario_id, rol: 'OPERADOR', debe_cambiar_contrasena: true })
  expect(await screen.findByRole('heading', { name: 'Cambiar contraseña' })).toBeInTheDocument()
  expect(screen.getByTestId('path')).toHaveTextContent('/cambiar-contrasena')
  expect(screen.queryByRole('navigation', { name: 'Navegación principal' })).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Ir a /vehiculos' }))
  expect(screen.getByTestId('path')).toHaveTextContent('/cambiar-contrasena')

  await fillChange(user)
  expect(changeMock).toHaveBeenCalledWith('temporal-16-char', 'definitiva-larga')
  expect(await screen.findByRole('heading', { name: 'Inicio' })).toBeInTheDocument()
  expect(screen.getByTestId('path')).toHaveTextContent(/^\/$/u)
  expect(await screen.findByText('Contraseña actualizada.')).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Ir a /vehiculos' }))
  expect(screen.getByTestId('path')).toHaveTextContent('/vehiculos')
}, 15_000)

it('cualquier 403 «Cambio de contraseña requerido» del API fuerza el cambio', async () => {
  await signIn({ usuario_id, rol: 'ADMINISTRADOR' })
  expect(await screen.findByRole('heading', { name: 'Inicio' })).toBeInTheDocument()
  await act(async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'Cambio de contraseña requerido' }), { status: 403 }))
    await fetch('https://api.example.test/vehiculos')
  })
  await waitFor(() => expect(screen.getByTestId('path')).toHaveTextContent('/cambiar-contrasena'))
  expect(screen.getByRole('heading', { name: 'Cambiar contraseña' })).toBeInTheDocument()
})

it('desde el cambio obligatorio se puede cerrar sesión', async () => {
  const user = await signIn({ usuario_id, rol: 'ANALISTA', debe_cambiar_contrasena: true })
  await user.click(await screen.findByRole('button', { name: 'Cerrar sesión' }))
  expect(logoutMock).toHaveBeenCalled()
  expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
})

it.each<AuthRole>(['OPERADOR', 'ANALISTA', 'AUDITOR'])('%s no ve ni puede abrir /usuarios', async role => {
  const user = await signIn({ usuario_id, rol: role })
  expect(await screen.findByRole('heading', { name: 'Inicio' })).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Usuarios' })).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Ir a /usuarios' }))
  expect(screen.getByRole('heading', { name: 'Acceso denegado' })).toBeInTheDocument()
  expect(listUsersMock).not.toHaveBeenCalled()
})

it('el conductor tampoco puede abrir /usuarios', async () => {
  const user = await signIn({ usuario_id, rol: 'CONDUCTOR', expires_at: new Date(Date.now() + 3_600_000).toISOString() })
  await screen.findByRole('heading', { name: 'Inicio' })
  await user.click(screen.getByRole('button', { name: 'Ir a /usuarios' }))
  expect(screen.getByRole('heading', { name: 'Acceso denegado' })).toBeInTheDocument()
})

it('el Administrador ve Usuarios en el menú y el cambio voluntario en su cuenta', async () => {
  const user = await signIn({ usuario_id, rol: 'ADMINISTRADOR' })
  await screen.findByRole('heading', { name: 'Inicio' })
  await user.click(screen.getByRole('link', { name: 'Usuarios' }))
  expect(await screen.findByRole('heading', { name: 'Usuarios', level: 1 })).toBeInTheDocument()
  expect(listUsersMock).toHaveBeenCalledWith(1, 20)

  await user.click(screen.getByRole('button', { name: /^Cuenta:/u }))
  await user.click(screen.getByRole('link', { name: 'Cambiar contraseña' }))
  expect(screen.getByLabelText('Contraseña actual')).toBeInTheDocument()
  expect(screen.getByRole('navigation', { name: 'Navegación principal' })).toBeInTheDocument()
})
