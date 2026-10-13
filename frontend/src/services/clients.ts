import { buildApiUrl } from './api'

export interface ClientOption {
  cliente_id: string
  nombre: string
}

export interface ClientPage {
  items: ClientOption[]
  page: number
  page_size: number
  total: number
}

export type ClientsErrorKind = 'unauthorized' | 'forbidden' | 'validation' | 'network' | 'unavailable' | 'unexpected'

const MESSAGES: Record<ClientsErrorKind, string> = {
  unauthorized: 'Tu sesión ha vencido. Vuelve a iniciar sesión.',
  forbidden: 'No tienes permisos para consultar clientes.',
  validation: 'Revisa el texto de búsqueda.',
  network: 'No se pudo comunicar con el servicio. Revisa tu conexión.',
  unavailable: 'El servicio no está disponible. Intenta nuevamente más tarde.',
  unexpected: 'No se pudo completar la búsqueda. Intenta nuevamente.',
}

export const CLIENT_SEARCH_MAX_LENGTH = 160
export const CLIENT_SEARCH_PAGE_SIZE = 8

/** Short, non-sensitive prefix to tell apart clients with the same name. */
export function shortClientId(id: string): string {
  return id.slice(0, 8)
}

export class ClientsServiceError extends Error {
  constructor(readonly kind: ClientsErrorKind) {
    super(MESSAGES[kind])
    this.name = 'ClientsServiceError'
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isClientOption(value: unknown): value is ClientOption {
  return isRecord(value) && typeof value.cliente_id === 'string' && typeof value.nombre === 'string'
}

function kindFor(status: number): ClientsErrorKind {
  if (status === 401) return 'unauthorized'
  if (status === 403) return 'forbidden'
  if (status === 422) return 'validation'
  if (status >= 500) return 'unavailable'
  return 'unexpected'
}

export async function searchClients(
  term: string,
  { page = 1, pageSize = CLIENT_SEARCH_PAGE_SIZE, signal }: { page?: number, pageSize?: number, signal?: AbortSignal } = {},
): Promise<ClientPage> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  const cleaned = term.trim().slice(0, CLIENT_SEARCH_MAX_LENGTH)
  if (cleaned) params.set('buscar', cleaned)
  let url: string
  try { url = buildApiUrl(`clientes?${params.toString()}`) } catch { throw new ClientsServiceError('unexpected') }
  let response: Response
  try {
    response = await fetch(url, { credentials: 'include', cache: 'no-store', signal })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ClientsServiceError('network')
  }
  if (!response.ok) throw new ClientsServiceError(kindFor(response.status))
  let body: unknown
  try { body = await response.json() } catch { throw new ClientsServiceError('unexpected') }
  if (!isRecord(body) || !Array.isArray(body.items) || !body.items.every(isClientOption) ||
    typeof body.total !== 'number' || typeof body.page !== 'number' || typeof body.page_size !== 'number') {
    throw new ClientsServiceError('unexpected')
  }
  return {
    items: body.items.map(item => ({ cliente_id: item.cliente_id, nombre: item.nombre })),
    page: body.page,
    page_size: body.page_size,
    total: body.total,
  }
}
