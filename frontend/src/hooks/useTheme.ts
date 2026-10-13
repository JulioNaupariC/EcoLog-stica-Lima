import { useCallback, useState } from 'react'

export type ThemePreference = 'system' | 'light' | 'dark'

const KEY = 'ecologistica-theme'

function readPreference(): ThemePreference {
  try {
    const stored = localStorage.getItem(KEY)
    return stored === 'light' || stored === 'dark' ? stored : 'system'
  } catch {
    return 'system'
  }
}

export function applyTheme(preference: ThemePreference): void {
  const root = document.documentElement
  if (preference === 'system') delete root.dataset.theme
  else root.dataset.theme = preference
}

/** Restores the stored preference before the first render (avoids a flash). */
export function initTheme(): void {
  applyTheme(readPreference())
}

/** Per-device convenience only: storage failures fall back to the system theme. */
export function useTheme(): [ThemePreference, (preference: ThemePreference) => void] {
  const [preference, setPreference] = useState<ThemePreference>(readPreference)
  const update = useCallback((next: ThemePreference) => {
    setPreference(next)
    applyTheme(next)
    try {
      if (next === 'system') localStorage.removeItem(KEY)
      else localStorage.setItem(KEY, next)
    } catch { /* Storage may be unavailable; the choice still applies to this tab. */ }
  }, [])
  return [preference, update]
}
