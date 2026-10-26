import { buildApiUrl } from './api'
import type { AuthRole } from './auth'

/** Exact 403 detail of the API (ECL-77); the backend pins it with a test. */
export const PASSWORD_CHANGE_REQUIRED_DETAIL = 'Cambio de contraseña requerido'
export const MIN_PASSWORD_LENGTH = 12

export interface UserListItem {
  usuario_id: string
  email: string
  rol: AuthRole
  estado: 'ACTIVO' | 'BLOQUEADO' | 'INACTIVO'
  debe_cambiar_contrasena: boolean
}
export interface UserPage { items: UserListItem[]; page: number; page_size: number; total: number }
export interface TemporaryPassword { contrasena_temporal: string; expira_en: string }

type ErrorKind =
  | 'unauthorized' | 'forbidden' | 'password_change_required' | 'not_found' | 'conflict'
  | 'validation' | 'current_invalid' | 'network' | 'unavailable' | 'unexpected'

const MESSAGES: Record<ErrorKind, string> = {
  unauthorized: 'Tu sesión ha vencido. Vuelve a iniciar sesión.',
  forbidden: 'Esta función está disponible solo para el Administrador.',
  password_change_required: 'Antes de continuar, guarda una contraseña nueva.',
  not_found: 'La cuenta ya no está disponible. Actualiza el listado.',
  conflict: 'Esta cuenta no admite el restablecimiento. Actualiza el listado o usa «Cambiar contraseña» para tu propia cuenta.',
  validation: 'La nueva contraseña necesita al menos 12 caracteres y debe ser distinta de la actual.',
  current_invalid: 'La contraseña actual no coincide. Revísala e intenta de nuevo; tras 3 intentos la cuenta se bloquea 15 minutos.',
  network: 'No se pudo conectar con el servicio. Revisa tu conexión e intenta de nuevo.',
  unavailable: 'El servicio no está disponible en este momento. Intenta de nuevo en unos minutos.',
  unexpected: 'No se pudo completar la operación. Intenta de nuevo.',
}

export class UserServiceError extends Error {
  readonly kind: ErrorKind
  constructor(kind: ErrorKind) {
    super(MESSAGES[kind])
    this.name = 'UserServiceError'
    this.kind = kind
  }
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/iu
const ROLES: readonly AuthRole[] = ['ADMINISTRADOR', 'OPERADOR', 'CONDUCTOR', 'ANALISTA', 'AUDITOR']
const STATES: readonly UserListItem['estado'][] = ['ACTIVO', 'BLOQUEADO', 'INACTIVO']

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function isPasswordChangeRequired(status: number, body: unknown): boolean {
  return status === 403 && record(body) && body.detail === PASSWORD_CHANGE_REQUIRED_DETAIL
}

function errorFor(status: number, body: unknown): UserServiceError {
  if (isPasswordChangeRequired(status, body)) return new UserServiceError('password_change_required')
  const kind: ErrorKind = status === 401 ? 'unauthorized' : status === 403 ? 'forbidden'
    : status === 404 ? 'not_found' : status === 409 ? 'conflict' : status === 422 ? 'validation'
      : status === 400 ? 'current_invalid' : status >= 500 ? 'unavailable' : 'unexpected'
  return new UserServiceError(kind)
}

async function request(path: string, init: RequestInit, expected: number): Promise<unknown> {
  let url: string
  try { url = buildApiUrl(path) } catch { throw new UserServiceError('unexpected') }
  let response: Response
  try {
    response = await fetch(url, { credentials: 'include', cache: 'no-store', ...init })
  } catch { throw new UserServiceError('network') }
  let body: unknown = null
  if (response.status !== 204) {
    try { body = await response.json() } catch { /* The status alone selects the message. */ }
  }
  if (!response.ok) throw errorFor(response.status, body)
  if (response.status !== expected) throw new UserServiceError('unexpected')
  return body
}

function listItem(value: unknown): UserListItem {
  if (!record(value) || typeof value.usuario_id !== 'string' || !UUID.test(value.usuario_id) ||
    typeof value.email !== 'string' || !ROLES.some(role => role === value.rol) ||
    !STATES.some(state => state === value.estado) || typeof value.debe_cambiar_contrasena !== 'boolean') {
    throw new UserServiceError('unexpected')
  }
  return {
    usuario_id: value.usuario_id, email: value.email, rol: value.rol as AuthRole,
    estado: value.estado as UserListItem['estado'], debe_cambiar_contrasena: value.debe_cambiar_contrasena,
  }
}

export async function listUsers(page = 1, pageSize = 20): Promise<UserPage> {
  if (!Number.isInteger(page) || page < 1 || !Number.isInteger(pageSize) || pageSize < 1 || pageSize > 100) {
    throw new UserServiceError('unexpected')
  }
  const body = await request(`usuarios?page=${page}&page_size=${pageSize}`, { method: 'GET' }, 200)
  if (!record(body) || body.page !== page || body.page_size !== pageSize || typeof body.total !== 'number' ||
    !Number.isInteger(body.total) || body.total < 0 || !Array.isArray(body.items) || body.items.length > pageSize) {
    throw new UserServiceError('unexpected')
  }
  return { items: body.items.map(listItem), page, page_size: pageSize, total: body.total }
}

export async function resetPassword(userId: string): Promise<TemporaryPassword> {
  if (!UUID.test(userId)) throw new UserServiceError('unexpected')
  const body = await request(`usuarios/${userId}/restablecer-contrasena`, { method: 'POST' }, 200)
  if (!record(body) || typeof body.contrasena_temporal !== 'string' || body.contrasena_temporal.length < 12 ||
    typeof body.expira_en !== 'string' || !Number.isFinite(Date.parse(body.expira_en))) {
    throw new UserServiceError('unexpected')
  }
  return { contrasena_temporal: body.contrasena_temporal, expira_en: body.expira_en }
}

export async function changePassword(current: string, next: string): Promise<void> {
  await request('cambiar-contrasena', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ contrasena_actual: current, contrasena_nueva: next }),
  }, 204)
}
