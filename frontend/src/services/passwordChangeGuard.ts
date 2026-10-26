import { parseApiBaseUrl } from './api'
import { isPasswordChangeRequired } from './users'

/** VITE_API_BASE_URL as a path prefix: "https://host/v1" matches "/v1/…", never "/v10". */
function apiPrefix(): string | null {
  try {
    const base = parseApiBaseUrl(import.meta.env.VITE_API_BASE_URL)
    return base.href.endsWith('/') ? base.href : `${base.href}/`
  } catch {
    return null
  }
}

/**
 * ECL-77: every service calls fetch on its own, so one observer detects the
 * API's 403 "Cambio de contraseña requerido" without touching each service.
 * Only 403 responses whose URL starts with VITE_API_BASE_URL are cloned and
 * read; the original response is always returned untouched. The returned
 * function restores the previous fetch (App calls it when the session ends).
 */
export function installPasswordChangeGuard(onRequired: () => void): () => void {
  const original = globalThis.fetch
  const prefix = apiPrefix()

  const guarded: typeof fetch = async (input, init) => {
    const response = await original(input, init)
    if (response.status !== 403 || prefix === null) return response
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
    if (!url.startsWith(prefix)) return response
    try {
      if (isPasswordChangeRequired(403, await response.clone().json())) onRequired()
    } catch { /* A non-JSON 403 is an ordinary denial. */ }
    return response
  }
  globalThis.fetch = guarded
  return () => {
    if (globalThis.fetch === guarded) globalThis.fetch = original
  }
}
