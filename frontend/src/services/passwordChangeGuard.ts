import { parseApiBaseUrl } from './api'
import { isPasswordChangeRequired } from './users'

/**
 * ECL-77: every service calls fetch on its own, so one observer detects the
 * API's 403 "Cambio de contraseña requerido" without touching each service.
 * It only reads a clone of API responses and never alters them.
 */
export function installPasswordChangeGuard(onRequired: () => void): () => void {
  const original = globalThis.fetch
  let apiOrigin: string | null = null
  try { apiOrigin = parseApiBaseUrl(import.meta.env.VITE_API_BASE_URL).origin } catch { /* no API configured */ }

  const guarded: typeof fetch = async (input, init) => {
    const response = await original(input, init)
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
    if (response.status === 403 && apiOrigin !== null && url.startsWith(apiOrigin)) {
      try {
        if (isPasswordChangeRequired(403, await response.clone().json())) onRequired()
      } catch { /* A non-JSON 403 is an ordinary denial. */ }
    }
    return response
  }
  globalThis.fetch = guarded
  return () => {
    if (globalThis.fetch === guarded) globalThis.fetch = original
  }
}
