import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { DriverShell, PublicShell, StaffShell } from './AppShell'

function mockViewport(desktop: boolean) {
  const listeners: (() => void)[] = []
  vi.stubGlobal('matchMedia', vi.fn().mockImplementation(() => ({
    matches: desktop,
    addEventListener: (_: string, listener: () => void) => listeners.push(listener),
    removeEventListener: vi.fn(),
  })))
}

function staff(role: 'ADMINISTRADOR' | 'OPERADOR' | 'ANALISTA' | 'AUDITOR' = 'OPERADOR', onLogout = vi.fn()) {
  render(<MemoryRouter initialEntries={['/vehiculos']}>
    <StaffShell role={role} accountName="operador@example.test" loggingOut={false} onLogout={onLogout}>
      <p>Contenido</p>
    </StaffShell>
  </MemoryRouter>)
  return onLogout
}

afterEach(() => {
  vi.unstubAllGlobals()
  try { localStorage.clear() } catch { /* jsdom storage */ }
  delete document.documentElement.dataset.theme
})

describe('StaffShell', () => {
  it('ruta dorada: sidebar por rol, página actual y «Próximamente» sin enlaces', () => {
    staff('OPERADOR')
    const nav = screen.getByRole('navigation', { name: 'Navegación principal' })
    expect(within(nav).getByRole('link', { name: 'Vehículos' })).toHaveAttribute('aria-current', 'page')
    expect(within(nav).getByRole('link', { name: 'Registrar pedido' })).toBeInTheDocument()
    expect(screen.getByText('Rutas optimizadas')).not.toHaveAttribute('href')
    // Section label plus one badge per planned feature; no sprint names in the UI.
    expect(screen.getAllByText('Próximamente')).toHaveLength(3)
    expect(screen.queryByText(/Sprint/u)).not.toBeInTheDocument()
  })

  it('ruta feliz: el menú de cuenta muestra rol legible, cambia el tema y cierra sesión', async () => {
    const user = userEvent.setup()
    const onLogout = staff('ADMINISTRADOR')
    const account = screen.getByRole('button', { name: 'Cuenta: operador@example.test, Administrador' })
    await user.click(account)
    expect(account).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Rol: Administrador')).toBeInTheDocument()
    await user.click(screen.getByRole('radio', { name: 'Oscuro' }))
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem('ecologistica-theme')).toBe('dark')
    await user.click(screen.getByRole('radio', { name: 'Sistema' }))
    expect(document.documentElement.dataset.theme).toBeUndefined()
    await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }))
    expect(onLogout).toHaveBeenCalledOnce()
  })

  it('ruta infeliz: Escape y clic fuera cierran el menú de cuenta y devuelven el foco', async () => {
    const user = userEvent.setup()
    staff()
    const account = screen.getByRole('button', { name: /^Cuenta:/u })
    await user.click(account)
    await user.keyboard('{Escape}')
    expect(account).toHaveAttribute('aria-expanded', 'false')
    expect(account).toHaveFocus()
    await user.click(account)
    await user.click(screen.getByText('Contenido'))
    expect(account).toHaveAttribute('aria-expanded', 'false')
  })

  it('ruta de borde: en móvil el menú lateral es inerte hasta abrirlo y se cierra con Escape', async () => {
    mockViewport(false)
    const user = userEvent.setup()
    staff()
    const sidebar = screen.getByRole('complementary', { name: 'Menú lateral' })
    expect(sidebar).toHaveAttribute('inert')
    const open = screen.getByRole('button', { name: 'Abrir menú' })
    await user.click(open)
    expect(sidebar).not.toHaveAttribute('inert')
    expect(open).toHaveAttribute('aria-expanded', 'true')
    await user.keyboard('{Escape}')
    expect(sidebar).toHaveAttribute('inert')
    expect(open).toHaveFocus()
  })

  it('ruta de borde: en escritorio el menú se contrae y recuerda la preferencia', async () => {
    mockViewport(true)
    const user = userEvent.setup()
    staff('AUDITOR')
    await user.click(screen.getByRole('button', { name: 'Contraer menú lateral' }))
    expect(localStorage.getItem('ecologistica-sidebar')).toBe('collapsed')
    expect(document.querySelector('.app--staff')).toHaveAttribute('data-sidebar', 'collapsed')
    expect(screen.queryByRole('link', { name: 'Registrar pedido' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Expandir menú lateral' }))
    expect(localStorage.getItem('ecologistica-sidebar')).toBe('expanded')
  })
})

describe('DriverShell y PublicShell', () => {
  it('el conductor navega con la barra inferior y el sitio público solo muestra el contenido', () => {
    const { unmount } = render(<MemoryRouter initialEntries={['/conductor/itinerario']}>
      <DriverShell role="CONDUCTOR" accountName="Conductor" loggingOut onLogout={vi.fn()}><p>Itinerario</p></DriverShell>
    </MemoryRouter>)
    const nav = screen.getByRole('navigation', { name: 'Navegación principal' })
    expect(within(nav).getByRole('link', { name: 'Mi itinerario' })).toHaveAttribute('aria-current', 'page')
    expect(within(nav).getAllByRole('link')).toHaveLength(2)
    unmount()
    render(<MemoryRouter><PublicShell><p>Login</p></PublicShell></MemoryRouter>)
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Saltar al contenido principal' })).toHaveAttribute('href', '#contenido-principal')
  })
})
