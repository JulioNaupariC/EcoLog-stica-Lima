import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useNavigate } from 'react-router-dom'
import { App } from './App'
import { login, logout } from '../services/auth'
import type { AuthRole } from '../services/auth'
import { operationRoutesApi } from '../services/operationRoutes'

vi.mock('../services/auth', async original => ({ ...await original<typeof import('../services/auth')>(), login: vi.fn(), logout: vi.fn() }))
vi.mock('../services/operationRoutes', async original => ({ ...await original<typeof import('../services/operationRoutes')>(),
  operationRoutesApi: { list: vi.fn(), detail: vi.fn() } }))
function Controls() { const navigate = useNavigate(); return <button onClick={() => { void navigate('/operacion/rutas') }}>Abrir mapa operativo</button> }
function show(path = '/login') { render(<MemoryRouter initialEntries={[path]}><Controls /><App /></MemoryRouter>) }
async function signIn(role: AuthRole) {
  vi.mocked(login).mockResolvedValue({ usuario_id: '123e4567-e89b-42d3-a456-426614174000', rol: role })
  fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: 'operator@example.test' } })
  fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'synthetic-password' } })
  fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
  await screen.findByRole('heading', { name: 'Inicio' })
}
beforeEach(() => {
  vi.mocked(operationRoutesApi.list).mockReset().mockResolvedValue({ items: [], page: 1, page_size: 12, total: 0, simulado: true })
  vi.mocked(operationRoutesApi.detail).mockReset()
  vi.mocked(logout).mockResolvedValue()
})
it('M04: sin sesión redirige al login sin consultar rutas', async () => {
  show('/operacion/rutas')
  expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
  expect(operationRoutesApi.list).not.toHaveBeenCalled()
})
it.each(['ADMINISTRADOR', 'OPERADOR'] as const)('M01: %s abre el mapa por menú', async role => {
  show(); await signIn(role)
  fireEvent.click(screen.getByRole('link', { name: 'Rutas y alertas' }))
  expect(await screen.findByRole('heading', { name: 'Rutas y alertas en mapa' })).toBeInTheDocument()
  await waitFor(() => expect(operationRoutesApi.list).toHaveBeenCalledOnce())
})
it.each(['CONDUCTOR', 'ANALISTA', 'AUDITOR'] as const)('M04: %s no ve el menú ni abre el detalle por URL', async role => {
  show(); await signIn(role)
  expect(screen.queryByRole('link', { name: 'Rutas y alertas' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Abrir mapa operativo' }))
  expect(await screen.findByRole('heading', { name: 'Acceso denegado' })).toBeInTheDocument()
  expect(operationRoutesApi.list).not.toHaveBeenCalled()
})
