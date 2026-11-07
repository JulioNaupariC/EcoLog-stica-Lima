import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { App } from './App'
import { login, logout } from '../services/auth'
import type { LoginResponse } from '../services/auth'

vi.mock('../services/auth', async original => ({ ...await original<typeof import('../services/auth')>(), login: vi.fn(), logout: vi.fn().mockResolvedValue(undefined) }))
vi.mock('../hooks/useIncidentSynchronization', () => ({ useIncidentSynchronization: vi.fn() }))
vi.mock('../pages/HomePage', () => ({ HomePage: () => <section><h1>Inicio</h1><form>
  <label htmlFor="plate">Placa</label><input id="plate" defaultValue="DEMO-001" />
  <label htmlFor="password">Contraseña</label><input id="password" type="password" defaultValue="synthetic-private" />
  </form></section> }))
vi.mock('../components/SessionExpiryNotice', () => ({ SessionExpiryNotice: ({ onExpired, onExtended, onSaveAndExit }: {
  onExpired: () => void; onExtended: (value: { expires_at: string; max_expires_at: string }) => void; onSaveAndExit: () => void
}) => <>
  <button onClick={onExpired}>Simular vencimiento</button>
  <button onClick={() => onExtended({ expires_at: new Date(Date.now() + 3_600_000).toISOString(),
    max_expires_at: new Date(Date.now() + 43_200_000).toISOString() })}>Simular renovación</button>
  <button onClick={onSaveAndExit}>Guardar y salir</button>
  </> }))

const identity: LoginResponse = { usuario_id: '123e4567-e89b-42d3-a456-426614174005', rol: 'OPERADOR',
  expires_at: new Date(Date.now() + 3_600_000).toISOString() }
const downloadUrl = vi.fn().mockReturnValue('blob:synthetic')

beforeEach(() => {
  vi.mocked(login).mockReset().mockResolvedValue(identity)
  vi.mocked(logout).mockClear()
  sessionStorage.clear()
  downloadUrl.mockClear()
  vi.stubGlobal('URL', class extends URL {
    static createObjectURL = downloadUrl
    static revokeObjectURL = vi.fn()
  })
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
})
afterEach(async () => {
  await new Promise(resolve => setTimeout(resolve, 0))
  vi.restoreAllMocks(); vi.unstubAllGlobals()
})

async function signIn() {
  fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: 'demo@example.test' } })
  fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'synthetic' } })
  fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
  await screen.findByRole('heading', { name: 'Inicio', level: 1 })
}

it('conserva el borrador tras vencer y lo ofrece solo al recuperar la misma cuenta', async () => {
  render(<MemoryRouter initialEntries={['/login']}><App /></MemoryRouter>)
  await signIn()
  fireEvent.click(screen.getByRole('button', { name: 'Simular vencimiento' }))
  await screen.findByRole('heading', { name: 'Iniciar sesión' })
  expect(screen.queryByRole('button', { name: 'Descargar borrador' })).not.toBeInTheDocument()
  await signIn()
  expect(screen.getByRole('button', { name: 'Descargar borrador' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Descargar borrador' }))
  expect(downloadUrl).toHaveBeenCalledOnce()
  expect(localStorage.length).toBe(0)
})

it('renovar conserva el formulario y permite guardarlo antes de salir al llegar al tope', async () => {
  render(<MemoryRouter initialEntries={['/login']}><App /></MemoryRouter>)
  await signIn()
  fireEvent.click(screen.getByRole('button', { name: 'Simular renovación' }))
  expect(screen.getByLabelText('Placa')).toHaveValue('DEMO-001')
  expect(screen.getByText('Sesión renovada. Puedes continuar con tu trabajo.')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Guardar y salir' }))
  await screen.findByRole('heading', { name: 'Iniciar sesión' })
  expect(downloadUrl).toHaveBeenCalledOnce()
  expect(logout).toHaveBeenCalledOnce()
})

it('otra cuenta no recibe el borrador del usuario anterior', async () => {
  render(<MemoryRouter initialEntries={['/login']}><App /></MemoryRouter>)
  await signIn()
  fireEvent.click(screen.getByRole('button', { name: 'Simular vencimiento' }))
  await screen.findByRole('heading', { name: 'Iniciar sesión' })
  vi.mocked(login).mockResolvedValue({ ...identity, usuario_id: '223e4567-e89b-42d3-a456-426614174005' })
  await signIn()
  expect(screen.queryByRole('button', { name: 'Descargar borrador' })).not.toBeInTheDocument()
})

it('renovar no habilita un conductor con cambio de contraseña obligatorio para acceso offline', async () => {
  vi.mocked(login).mockResolvedValue({ ...identity, rol: 'CONDUCTOR', debe_cambiar_contrasena: true })
  render(<MemoryRouter initialEntries={['/login']}><App /></MemoryRouter>)
  fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: 'demo@example.test' } })
  fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'synthetic' } })
  fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
  await screen.findByLabelText('Contraseña temporal')
  fireEvent.click(screen.getByRole('button', { name: 'Simular renovación' }))
  expect(sessionStorage.getItem('ecologistica-driver-tab')).toBeNull()
  expect(screen.getByLabelText('Contraseña temporal')).toBeInTheDocument()
})
