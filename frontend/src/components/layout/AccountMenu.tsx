import { useEffect, useId, useRef, useState } from 'react'
import { ChevronDown, LogOut, Monitor, Moon, Sun } from 'lucide-react'
import type { AuthRole } from '../../services/auth'
import { ROLE_LABEL } from '../../domain/roles'
import { useTheme } from '../../hooks/useTheme'
import type { ThemePreference } from '../../hooks/useTheme'

const THEMES: { value: ThemePreference, label: string, icon: typeof Sun }[] = [
  { value: 'system', label: 'Sistema', icon: Monitor },
  { value: 'light', label: 'Claro', icon: Sun },
  { value: 'dark', label: 'Oscuro', icon: Moon },
]

function initials(name: string): string {
  const letters = name.replace(/@.*/u, '').split(/[.\s_-]+/u).filter(Boolean).map(part => part[0])
  return (letters.slice(0, 2).join('') || name.slice(0, 1)).toUpperCase()
}

/** Disclosure (not an ARIA menu): a button that shows account details, theme and logout. */
export function AccountMenu({ name, role, loggingOut, onLogout }: {
  name: string
  role: AuthRole
  loggingOut: boolean
  onLogout: () => void
}) {
  const [open, setOpen] = useState(false)
  const [theme, setTheme] = useTheme()
  const panelId = useId()
  const container = useRef<HTMLDivElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const roleLabel = ROLE_LABEL[role]

  useEffect(() => {
    if (!open) return undefined
    function onPointer(event: PointerEvent) {
      if (!container.current?.contains(event.target as Node)) setOpen(false)
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') { setOpen(false); trigger.current?.focus() }
    }
    document.addEventListener('pointerdown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return <div className="account" ref={container}>
    <button ref={trigger} type="button" className="account-trigger" aria-expanded={open} aria-controls={panelId}
      aria-label={`Cuenta: ${name}, ${roleLabel}`} onClick={() => setOpen(value => !value)}>
      <span className="account-avatar" aria-hidden="true">{initials(name)}</span>
      <span className="account-meta" aria-hidden="true">
        <span className="account-name">{name}</span>
        <span className="account-role">{roleLabel}</span>
      </span>
      <ChevronDown aria-hidden="true" size={16} />
    </button>
    {open ? <div className="account-menu" id={panelId}>
      <div className="account-menu-header">
        <strong>{name}</strong>
        <span className="account-role">Rol: {roleLabel}</span>
      </div>
      <fieldset>
        <legend>Tema</legend>
        <div className="theme-options">
          {THEMES.map(({ value, label, icon: Icon }) => <label key={value} className="theme-option">
            <input type="radio" name="tema" value={value} checked={theme === value} onChange={() => setTheme(value)} />
            <span><Icon aria-hidden="true" size={18} />{label}</span>
          </label>)}
        </div>
      </fieldset>
      <button type="button" className="menu-item" disabled={loggingOut} onClick={onLogout}>
        <LogOut aria-hidden="true" size={18} />
        {loggingOut ? 'Cerrando sesión…' : 'Cerrar sesión'}
      </button>
    </div> : null}
  </div>
}
