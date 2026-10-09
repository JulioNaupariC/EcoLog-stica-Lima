import { buildApiUrl } from './api'

const AUTH_ROLES = [
  'ADMINISTRADOR',
  'OPERADOR',
  'CONDUCTOR',
  'ANALISTA',
  'AUDITOR',
] as const

export type AuthRole = (typeof AUTH_ROLES)[number]

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  usuario_id: string
  rol: AuthRole
}

export type AuthServiceErrorKind =
  | 'unauthorized'
  | 'validation'
  | 'unavailable'
  | 'network'
  | 'unexpected'

export interface AuthValidationIssue {
  field: keyof LoginRequest
  message: string
}

export class AuthServiceError extends Error {
  readonly kind: AuthServiceErrorKind
  readonly status?: number
  readonly issues: AuthValidationIssue[]

  constructor(
    kind: AuthServiceErrorKind,
    message: string,
    options: { status?: number; issues?: AuthValidationIssue[] } = {},
  ) {
    super(message)
    this.name = 'AuthServiceError'
    this.kind = kind
    this.status = options.status
    this.issues = options.issues ?? []
  }
}

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/iu

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isAuthRole(value: unknown): value is AuthRole {
  return AUTH_ROLES.some((role) => role === value)
}

function validationIssues(body: unknown): AuthValidationIssue[] {
  if (!isRecord(body) || !Array.isArray(body.detail)) {
    return []
  }

  return body.detail.flatMap((detail): AuthValidationIssue[] => {
    if (!isRecord(detail) || !Array.isArray(detail.loc) || typeof detail.msg !== 'string') {
      return []
    }

    const location: unknown[] = detail.loc
    if (location[0] !== 'body') {
      return []
    }

    const field = location.at(-1)
    if (field === 'email') {
      return [{ field, message: 'Revisa el correo electrónico.' }]
    }
    if (field === 'password') {
      return [{ field, message: 'Revisa la contraseña.' }]
    }
    return []
  })
}

async function responseBody(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}

function httpError(status: number, body: unknown): AuthServiceError {
  if (status === 401) {
    return new AuthServiceError('unauthorized', 'Credenciales inválidas.', { status })
  }
  if (status === 422) {
    return new AuthServiceError('validation', 'Revisa los datos ingresados.', {
      status,
      issues: validationIssues(body),
    })
  }
  if (status === 503) {
    return new AuthServiceError(
      'unavailable',
      'El servicio no está disponible en este momento.',
      { status },
    )
  }
  return new AuthServiceError('unexpected', 'No se pudo iniciar sesión.', { status })
}

export async function login(payload: LoginRequest): Promise<LoginResponse> {
  let url: string
  try {
    url = buildApiUrl('login')
  } catch {
    throw new AuthServiceError('unexpected', 'No se pudo iniciar sesión.')
  }

  let response: Response
  try {
    response = await fetch(url, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: payload.email, password: payload.password }),
    })
  } catch {
    throw new AuthServiceError('network', 'No se pudo conectar con el servicio.')
  }

  const body = await responseBody(response)
  if (!response.ok) {
    throw httpError(response.status, body)
  }
  if (
    response.status !== 200 ||
    !isRecord(body) ||
    typeof body.usuario_id !== 'string' ||
    !UUID_PATTERN.test(body.usuario_id) ||
    !isAuthRole(body.rol)
  ) {
    throw new AuthServiceError('unexpected', 'El servicio devolvió una respuesta inválida.', {
      status: response.status,
    })
  }
  return { usuario_id: body.usuario_id, rol: body.rol }
}

export async function logout(): Promise<void> {
  let url: string
  try {
    url = buildApiUrl('logout')
  } catch {
    throw new AuthServiceError('unexpected', 'No se pudo cerrar la sesión.')
  }

  let response: Response
  try {
    response = await fetch(url, { method: 'POST', credentials: 'include' })
  } catch {
    throw new AuthServiceError('network', 'No se pudo conectar para cerrar la sesión.')
  }

  if (response.status !== 204) {
    throw new AuthServiceError(
      response.status === 503 ? 'unavailable' : 'unexpected',
      response.status === 503
        ? 'El servicio no está disponible para cerrar la sesión.'
        : 'No se pudo cerrar la sesión.',
      { status: response.status },
    )
  }
}
