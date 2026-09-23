const ALLOWED_PROTOCOLS = new Set(['http:', 'https:'])

export function parseApiBaseUrl(value: string | undefined): URL {
  if (!value?.trim()) {
    throw new Error('VITE_API_BASE_URL es obligatoria.')
  }

  let url: URL
  try {
    url = new URL(value)
  } catch {
    throw new Error('VITE_API_BASE_URL debe ser una URL válida.')
  }

  if (!ALLOWED_PROTOCOLS.has(url.protocol)) {
    throw new Error('VITE_API_BASE_URL debe usar el protocolo http o https.')
  }

  if (url.username || url.password) {
    throw new Error('VITE_API_BASE_URL no debe incluir credenciales.')
  }

  if (url.search) {
    throw new Error('VITE_API_BASE_URL no debe incluir parámetros de consulta.')
  }

  if (url.hash) {
    throw new Error('VITE_API_BASE_URL no debe incluir fragmentos.')
  }

  return url
}

export function buildApiUrl(path: string): string {
  const baseUrl = parseApiBaseUrl(import.meta.env.VITE_API_BASE_URL)
  const trimmedPath = path.trim()

  if (
    trimmedPath.startsWith('//') ||
    /^[a-z][a-z\d+.-]*:/iu.test(trimmedPath)
  ) {
    throw new Error('El path del API debe ser relativo a VITE_API_BASE_URL.')
  }

  const relativePath = trimmedPath.replace(/^\/+/, '')
  const basePath = baseUrl.pathname.endsWith('/')
    ? baseUrl.pathname
    : `${baseUrl.pathname}/`
  const normalizedBase = new URL(baseUrl.href)
  normalizedBase.pathname = basePath
  const result = new URL(relativePath, normalizedBase)

  if (result.origin !== baseUrl.origin || !result.pathname.startsWith(basePath)) {
    throw new Error(
      'El path del API no puede cambiar el origen ni escapar de la ruta base.',
    )
  }

  return result.href
}
