import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useNavigate } from 'react-router-dom'
import { App } from './App'
import { login } from '../services/auth'
import type { AuthRole } from '../services/auth'
import { sustainabilityApi } from '../services/sustainability'
import { parseSustainability } from '../domain/sustainability'
import raw from '../test/fixtures/rutas/sostenibilidad-con-datos.json'

vi.mock('../services/auth', async original => ({ ...await original<typeof import('../services/auth')>(), login: vi.fn(), logout: vi.fn() }))
vi.mock('../services/sustainability', async original => ({ ...await original<typeof import('../services/sustainability')>(), sustainabilityApi: { load: vi.fn() } }))
function Controls() { const navigate = useNavigate(); return <button onClick={() => { void navigate('/indicadores/sostenibilidad') }}>Abrir agregado por URL</button> }
function show(path = '/login') { render(<MemoryRouter initialEntries={[path]}><Controls /><App /></MemoryRouter>) }
async function signIn(role: AuthRole, required = false) {
  vi.mocked(login).mockResolvedValue({ usuario_id: '123e4567-e89b-42d3-a456-426614174000', rol: role,
    ...(required ? { debe_cambiar_contrasena: true as const } : {}) })
  fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: 'synthetic@example.test' } })
  fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'synthetic-password' } })
  fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
  await screen.findByRole('heading', { name: required ? 'Cambiar contraseña' : 'Inicio' })
}
beforeEach(() => {
  vi.mocked(sustainabilityApi.load).mockReset().mockImplementation(p => Promise.resolve(parseSustainability({ ...raw, periodo: p }, p)))
})
it('D04 sin sesión redirige al login sin descargar el agregado', async () => {
  show('/indicadores/sostenibilidad')
  expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
  expect(sustainabilityApi.load).not.toHaveBeenCalled()
})
it.each(['ADMINISTRADOR', 'OPERADOR', 'ANALISTA', 'AUDITOR'] as const)('D01/D04 %s consulta por menú según la BDD ratificada', async role => {
  show(); await signIn(role)
  const links = screen.getAllByRole('link', { name: /Indicadores de sostenibilidad/ })
  fireEvent.click(links[0])
  expect(await screen.findByRole('heading', { name: 'Operación y sostenibilidad' })).toBeInTheDocument()
  await waitFor(() => expect(sustainabilityApi.load).toHaveBeenCalledOnce())
})
it('D04 conductor no ve el enlace ni consulta desde URL', async () => {
  show(); await signIn('CONDUCTOR')
  expect(screen.queryByRole('link', { name: /Indicadores de sostenibilidad/ })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Abrir agregado por URL' }))
  expect(await screen.findByRole('heading', { name: 'Acceso denegado' })).toBeInTheDocument()
  expect(sustainabilityApi.load).not.toHaveBeenCalled()
})
it('mantiene el bloqueo por cambio obligatorio de contraseña', async () => {
  show(); await signIn('OPERADOR', true)
  fireEvent.click(screen.getByRole('button', { name: 'Abrir agregado por URL' }))
  expect(await screen.findByRole('heading', { name: 'Cambiar contraseña' })).toBeInTheDocument()
  expect(sustainabilityApi.load).not.toHaveBeenCalled()
})
