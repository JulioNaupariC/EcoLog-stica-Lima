import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, useNavigate } from 'react-router-dom'
import { App } from './App'
import { login } from '../services/auth'
import type { AuthRole } from '../services/auth'
import { getDeliveryPreferences, PreferencesServiceError } from '../services/deliveryPreferences'

vi.mock('../services/auth', async original => ({ ...await original<typeof import('../services/auth')>(), login: vi.fn() }))
vi.mock('../services/deliveryPreferences', async original => ({ ...await original<typeof import('../services/deliveryPreferences')>(), getDeliveryPreferences: vi.fn() }))
function Controls() {
  const navigate = useNavigate()
  return <button onClick={() => { void navigate('/clientes/preferencias') }}>Abrir preferencias</button>
}
function show(path = '/login') { render(<MemoryRouter initialEntries={[path]}><Controls /><App /></MemoryRouter>) }
async function signIn(role: AuthRole) {
  vi.mocked(login).mockResolvedValue({ usuario_id: '123e4567-e89b-12d3-a456-426614174000', rol: role })
  fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: 'test@example.test' } })
  fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'synthetic-password' } })
  fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
  await screen.findByRole('heading', { name: 'Rutas sostenibles para Lima' })
}
beforeEach(() => { vi.mocked(getDeliveryPreferences).mockReset() })
it('solicita login al abrir preferencias sin identidad', async () => {
  show('/clientes/preferencias')
  expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
  expect(getDeliveryPreferences).not.toHaveBeenCalled()
})
it.each(['ADMINISTRADOR', 'OPERADOR'] as const)('permite gestionar preferencias a %s', async role => {
  show(); await signIn(role)
  fireEvent.click(screen.getByRole('link', { name: 'Preferencias de entrega' }))
  expect(await screen.findByRole('heading', { name: 'Preferencias de entrega' })).toBeInTheDocument()
  expect(screen.getByLabelText('ID del cliente')).toBeEnabled()
})
it.each(['CONDUCTOR', 'AUDITOR', 'ANALISTA'] as const)('deniega ruta directa a %s sin consultar API', async role => {
  show(); await signIn(role)
  expect(screen.queryByRole('link', { name: 'Preferencias de entrega' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Abrir preferencias' }))
  expect(await screen.findByRole('heading', { name: 'Acceso denegado' })).toBeInTheDocument()
  expect(getDeliveryPreferences).not.toHaveBeenCalled()
})
it('elimina identidad ante 401 y vuelve al login', async () => {
  show(); await signIn('OPERADOR')
  fireEvent.click(screen.getByRole('link', { name: 'Preferencias de entrega' }))
  vi.mocked(getDeliveryPreferences).mockRejectedValueOnce(new PreferencesServiceError('unauthorized'))
  fireEvent.change(screen.getByLabelText('ID del cliente'), { target: { value: '123e4567-e89b-12d3-a456-426614174000' } })
  fireEvent.submit(screen.getByRole('form', { name: 'Consultar cliente' }))
  expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
  expect(screen.queryByText('Rol: OPERADOR')).not.toBeInTheDocument()
})
