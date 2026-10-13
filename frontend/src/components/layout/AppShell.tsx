import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import {
  BarChart3, Building2, ClipboardList, Home, Leaf, Map, Menu, PanelLeftClose, PanelLeftOpen,
  Route as RouteIcon, Truck, UserRound, X,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { AuthRole } from '../../services/auth'
import { canListVehicles, canManageOperations } from '../../domain/roles'
import { Badge } from '../ui'
import { AccountMenu } from './AccountMenu'

interface NavEntry { to: string, label: string, icon: LucideIcon, end?: boolean }

const SIDEBAR_KEY = 'ecologistica-sidebar'

function staffNavigation(role: AuthRole): { label: string, items: NavEntry[] }[] {
  const operations: NavEntry[] = canManageOperations(role) ? [
    { to: '/pedidos/nuevo', label: 'Registrar pedido', icon: ClipboardList },
    { to: '/clientes/preferencias', label: 'Preferencias de entrega', icon: Building2 },
  ] : []
  const resources: NavEntry[] = [
    ...(canListVehicles(role) ? [{ to: '/vehiculos', label: 'Vehículos', icon: Truck }] : []),
    ...(canManageOperations(role) ? [{ to: '/conductores', label: 'Conductores', icon: UserRound }] : []),
  ]
  return [
    { label: 'General', items: [{ to: '/', label: 'Inicio', icon: Home, end: true }] },
    ...(operations.length ? [{ label: 'Operación', items: operations }] : []),
    ...(resources.length ? [{ label: 'Recursos', items: resources }] : []),
  ]
}

const COMING_SOON: { label: string, icon: LucideIcon }[] = [
  { label: 'Rutas optimizadas', icon: RouteIcon },
  { label: 'Indicadores de sostenibilidad', icon: BarChart3 },
]

function useDesktop(): boolean {
  const query = '(min-width: 64rem)'
  const [desktop, setDesktop] = useState(() => typeof window.matchMedia !== 'function' || window.matchMedia(query).matches)
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return undefined
    const media = window.matchMedia(query)
    const update = () => setDesktop(media.matches)
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])
  return desktop
}

function readCollapsed(): boolean {
  try { return localStorage.getItem(SIDEBAR_KEY) === 'collapsed' } catch { return false }
}

function Brand() {
  return <Link className="brand" to="/">
    <span className="brand-mark" aria-hidden="true"><Leaf size={18} /></span>
    <span className="brand-text">EcoLogística Lima</span>
  </Link>
}

interface ShellProps {
  role: AuthRole
  accountName: string
  loggingOut: boolean
  onLogout: () => void
  banner?: ReactNode
  children: ReactNode
}

/** Administración, operación, análisis y auditoría: sidebar colapsable + barra superior. */
export function StaffShell({ role, accountName, loggingOut, onLogout, banner, children }: ShellProps) {
  const desktop = useDesktop()
  const [open, setOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(readCollapsed)
  const location = useLocation()
  const menuButton = useRef<HTMLButtonElement>(null)
  const sidebar = useRef<HTMLElement>(null)
  const sections = staffNavigation(role)
  const [lastPath, setLastPath] = useState(location.pathname)

  // Close the mobile drawer after navigating.
  if (location.pathname !== lastPath) {
    setLastPath(location.pathname)
    if (open) setOpen(false)
  }

  useEffect(() => {
    if (!open) return undefined
    sidebar.current?.querySelector<HTMLElement>('a, button')?.focus()
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') { setOpen(false); menuButton.current?.focus() }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  function toggleCollapsed() {
    setCollapsed(value => {
      try { localStorage.setItem(SIDEBAR_KEY, value ? 'expanded' : 'collapsed') } catch { /* optional */ }
      return !value
    })
  }

  const hidden = !desktop && !open
  return <div className="app app--staff" data-sidebar={desktop && collapsed ? 'collapsed' : 'expanded'}>
    <a className="skip-link" href="#contenido-principal">Saltar al contenido principal</a>
    <aside ref={sidebar} id="menu-lateral" className="sidebar" data-open={open} inert={hidden}
      aria-label="Menú lateral">
      <div className="sidebar-head">
        <span className="sidebar-title">Menú</span>
        <button type="button" className="icon-button sidebar-collapse" onClick={toggleCollapsed}
          aria-label={collapsed ? 'Expandir menú lateral' : 'Contraer menú lateral'} aria-expanded={!collapsed}>
          {collapsed ? <PanelLeftOpen aria-hidden="true" size={20} /> : <PanelLeftClose aria-hidden="true" size={20} />}
        </button>
        <button type="button" className="icon-button sidebar-close" onClick={() => { setOpen(false); menuButton.current?.focus() }}
          aria-label="Cerrar menú">
          <X aria-hidden="true" size={20} />
        </button>
      </div>
      <nav aria-label="Navegación principal">
        {sections.map(section => <div className="nav-section" key={section.label}>
          <p className="nav-section-label">{section.label}</p>
          <ul className="nav-list">
            {section.items.map(item => <li key={item.to}>
              <NavLink to={item.to} end={item.end} className="nav-item" title={collapsed ? item.label : undefined}>
                <item.icon aria-hidden="true" size={20} />
                <span className="nav-label">{item.label}</span>
              </NavLink>
            </li>)}
          </ul>
        </div>)}
      </nav>
      <div className="nav-section nav-section--soon">
        <p className="nav-section-label">Próximamente</p>
        <ul className="nav-list">
          {COMING_SOON.map(item => <li key={item.label}>
            <span className="nav-item nav-item--soon" title={collapsed ? `${item.label} (próximamente)` : undefined}>
              <item.icon aria-hidden="true" size={20} />
              <span className="nav-label">{item.label}</span>
              <Badge tone="neutral" icon={null}>Próximamente</Badge>
            </span>
          </li>)}
        </ul>
      </div>
    </aside>
    {open && !desktop ? <button type="button" className="sidebar-backdrop" tabIndex={-1} aria-label="Cerrar menú"
      onClick={() => setOpen(false)} /> : null}
    <div className="app-body">
      <header className="topbar">
        <button ref={menuButton} type="button" className="icon-button topbar-menu-button" aria-label="Abrir menú"
          aria-expanded={open} aria-controls="menu-lateral" onClick={() => setOpen(true)}>
          <Menu aria-hidden="true" size={22} />
        </button>
        <Brand />
        <span className="topbar-spacer" />
        <AccountMenu name={accountName} role={role} loggingOut={loggingOut} onLogout={onLogout} />
      </header>
      {banner}
      <main id="contenido-principal" tabIndex={-1} className="page">{children}</main>
    </div>
  </div>
}

/** Conductor: móvil primero, con navegación inferior de dos destinos. */
export function DriverShell({ role, accountName, loggingOut, onLogout, banner, children }: ShellProps) {
  const items: NavEntry[] = [
    { to: '/', label: 'Inicio', icon: Home, end: true },
    { to: '/conductor/itinerario', label: 'Mi itinerario', icon: Map },
  ]
  return <div className="app app--driver">
    <a className="skip-link" href="#contenido-principal">Saltar al contenido principal</a>
    <div className="app-body">
      <header className="topbar">
        <Brand />
        <span className="topbar-spacer" />
        <AccountMenu name={accountName} role={role} loggingOut={loggingOut} onLogout={onLogout} />
      </header>
      {banner}
      <main id="contenido-principal" tabIndex={-1} className="page">{children}</main>
    </div>
    <nav className="bottom-nav" aria-label="Navegación principal" style={{ '--bottom-nav-items': items.length } as React.CSSProperties}>
      <ul className="nav-list">
        {items.map(item => <li key={item.to}>
          <NavLink to={item.to} end={item.end} className="nav-item">
            <item.icon aria-hidden="true" size={22} />
            <span className="nav-label">{item.label}</span>
          </NavLink>
        </li>)}
      </ul>
    </nav>
  </div>
}

/** Sin sesión: páginas públicas (login y 404) sin navegación. */
export function PublicShell({ children }: { children: ReactNode }) {
  return <div className="app app--public">
    <a className="skip-link" href="#contenido-principal">Saltar al contenido principal</a>
    <main id="contenido-principal" tabIndex={-1}>{children}</main>
  </div>
}
