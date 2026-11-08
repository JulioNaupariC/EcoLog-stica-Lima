import { useState } from 'react'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { AuthServiceError, extendSession } from '../services/auth'
import type { AuthRole, LoginResponse } from '../services/auth'
import { SessionExpiryNotice } from './SessionExpiryNotice'

vi.mock('../services/auth', async original => ({
  ...await original<typeof import('../services/auth')>(), extendSession: vi.fn(),
}))
const extend = vi.mocked(extendSession)
const now = new Date('2026-11-07T12:00:00Z')
const identity: LoginResponse = { usuario_id: '123e4567-e89b-42d3-a456-426614174005', rol: 'OPERADOR',
  expires_at: '2026-11-07T13:00:00Z', max_expires_at: '2026-11-08T00:00:00Z' }

beforeEach(() => { vi.useFakeTimers(); vi.setSystemTime(now); extend.mockReset() })
afterEach(() => { vi.useRealTimers() })

function setup(role: AuthRole = 'OPERADOR') {
  const expired = vi.fn(), loggedOut = vi.fn(), saved = vi.fn(), renewed = vi.fn()
  function Harness() {
    const [value, setValue] = useState({ ...identity, rol: role })
    return <div id="root"><main><form><label>Placa<input defaultValue="DEMO-001" /></label></form></main>
      <SessionExpiryNotice identity={value} onExpired={expired} onLogout={loggedOut} onSaveAndExit={saved}
        onExtended={extension => { renewed(extension); setValue({ ...value, ...extension }) }} />
    </div>
  }
  const view = render(<Harness />)
  return { ...view, expired, loggedOut, saved, renewed }
}

it.each<AuthRole>(['ADMINISTRADOR', 'OPERADOR', 'CONDUCTOR', 'ANALISTA', 'AUDITOR'])(
  'avisa dos minutos antes para %s, con foco y teclado sin perder el formulario', async role => {
    const { expired, renewed } = setup(role)
    act(() => { vi.advanceTimersByTime(3_479_999) })
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(1) })
    expect(screen.getByRole('alertdialog', { name: 'Tu sesión está por vencer' })).toHaveAttribute('aria-modal', 'true')
    expect(screen.getByRole('button', { name: 'Seguir conectado' })).toHaveFocus()
    expect(document.getElementById('root')).toHaveAttribute('inert')
    const extension = { expires_at: new Date(Date.now() + 3_600_000).toISOString(), max_expires_at: identity.max_expires_at! }
    extend.mockResolvedValue(extension)
    const first = screen.getByRole('button', { name: 'Seguir conectado' })
    const last = screen.getByRole('button', { name: 'Volver al formulario' })
    last.focus()
    fireEvent.keyDown(document, { key: 'Tab' })
    expect(first).toHaveFocus()
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true })
    expect(last).toHaveFocus()
    await act(async () => { fireEvent.click(first); await Promise.resolve() })
    expect(renewed).toHaveBeenCalledWith(extension)
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Placa')).toHaveValue('DEMO-001')
    act(() => { vi.advanceTimersByTime(120_000) })
    expect(expired).not.toHaveBeenCalled()
    act(() => { vi.advanceTimersByTime(3_360_000) })
    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
  },
)

it('permite Escape, volver al aviso y cerrar sesión; vence si no hay respuesta', () => {
  const { expired, loggedOut } = setup()
  act(() => { vi.advanceTimersByTime(3_480_000) })
  fireEvent.keyDown(document, { key: 'Escape' })
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Revisar vencimiento' }))
  fireEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }))
  expect(loggedOut).toHaveBeenCalledOnce()
  act(() => { vi.advanceTimersByTime(120_000) })
  expect(expired).toHaveBeenCalledOnce()
})

it('409 ofrece guardar el formulario y volver a entrar', async () => {
  const { saved } = setup()
  act(() => { vi.advanceTimersByTime(3_480_000) })
  extend.mockRejectedValue(new AuthServiceError('unexpected', 'limit', { status: 409 }))
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Seguir conectado' })); await Promise.resolve() })
  expect(screen.getByRole('alert')).toHaveTextContent('La sesión alcanzó su duración máxima')
  fireEvent.click(screen.getByRole('button', { name: 'Guardar borrador y volver a entrar' }))
  expect(saved).toHaveBeenCalledOnce()
})

it('fallo de red no renueva localmente; permite reintentar y respeta el vencimiento', async () => {
  const { renewed, expired } = setup()
  act(() => { vi.advanceTimersByTime(3_480_000) })
  extend.mockRejectedValue(new Error('network'))
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Seguir conectado' })); await Promise.resolve() })
  expect(screen.getByRole('alert')).toHaveTextContent('Comprueba tu conexión')
  expect(renewed).not.toHaveBeenCalled()
  act(() => { vi.advanceTimersByTime(120_000) })
  expect(expired).toHaveBeenCalledOnce()
})

it('401 cierra la sesión y un 200 con plazo ya vencido tampoco la reactiva', async () => {
  const { expired } = setup()
  act(() => { vi.advanceTimersByTime(3_480_000) })
  extend.mockRejectedValueOnce(new AuthServiceError('unauthorized', 'expired', { status: 401 }))
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Seguir conectado' })); await Promise.resolve() })
  expect(expired).toHaveBeenCalledOnce()
  extend.mockResolvedValue({ expires_at: now.toISOString(), max_expires_at: identity.max_expires_at! })
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Seguir conectado' })); await Promise.resolve() })
  expect(expired).toHaveBeenCalledTimes(2)
})

it('invalida respuestas tardías al desmontar y no permite doble envío', async () => {
  const { unmount, renewed } = setup()
  act(() => { vi.advanceTimersByTime(3_480_000) })
  let resolve!: (value: { expires_at: string; max_expires_at: string }) => void
  extend.mockReturnValue(new Promise(accept => { resolve = accept }))
  fireEvent.click(screen.getByRole('button', { name: 'Seguir conectado' }))
  expect(screen.getByRole('button', { name: 'Renovando sesión…' })).toBeDisabled()
  expect(extend).toHaveBeenCalledOnce()
  unmount()
  await act(async () => { resolve({ expires_at: '2026-11-07T14:00:00Z', max_expires_at: identity.max_expires_at! }); await Promise.resolve() })
  expect(renewed).not.toHaveBeenCalled()
})

it('recomprueba la expiración al regresar de una pestaña suspendida', () => {
  const { expired } = setup()
  vi.setSystemTime(new Date('2026-11-07T14:00:00Z'))
  fireEvent.focus(window)
  expect(expired).toHaveBeenCalledOnce()
})

it('no inventa un plazo cuando no hay metadatos de una sesión anterior', () => {
  render(<SessionExpiryNotice identity={{ usuario_id: identity.usuario_id, rol: 'CONDUCTOR' }}
    onExtended={vi.fn()} onExpired={vi.fn()} onLogout={vi.fn()} onSaveAndExit={vi.fn()} />)
  act(() => { vi.advanceTimersByTime(3_600_000) })
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
})
