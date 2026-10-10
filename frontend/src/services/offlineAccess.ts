import type { LoginResponse } from './auth'
import { validUuid } from '../types/driverReport'

const KEY = 'ecologistica-driver-tab'

/** Local UI hint for the same tab, never a credential or server authorization. */
export function rememberDriver(identity: LoginResponse): void {
  forgetDriver()
  if (identity.rol !== 'CONDUCTOR' || !identity.expires_at ||
      !validUuid(identity.usuario_id) || !Number.isFinite(Date.parse(identity.expires_at)) ||
      Date.parse(identity.expires_at) <= Date.now() || Date.parse(identity.expires_at) > Date.now() + 86_400_000) return
  try { sessionStorage.setItem(KEY, JSON.stringify(identity)) } catch { /* storage may be disabled */ }
}

export function recallDriver(): LoginResponse | null {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(KEY) || 'null')
    if (typeof value !== 'object' || value === null) return null
    const hint = value as Record<string, unknown>
    if (hint.rol !== 'CONDUCTOR' || typeof hint.usuario_id !== 'string' ||
        !validUuid(hint.usuario_id) || typeof hint.expires_at !== 'string' ||
        !Number.isFinite(Date.parse(hint.expires_at)) || Date.parse(hint.expires_at) <= Date.now() ||
        Date.parse(hint.expires_at) > Date.now() + 86_400_000) {
      forgetDriver(); return null
    }
    return { usuario_id: hint.usuario_id, rol: 'CONDUCTOR', expires_at: hint.expires_at }
  } catch { return null }
}

export function forgetDriver(): void {
  try { sessionStorage.removeItem(KEY) } catch { /* no persistent hint exists */ }
}
