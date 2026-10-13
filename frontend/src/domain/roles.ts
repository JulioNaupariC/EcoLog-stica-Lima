import type { AuthRole } from '../services/auth'

/** Readable role names for the interface (the API keeps the uppercase codes). */
export const ROLE_LABEL: Record<AuthRole, string> = {
  ADMINISTRADOR: 'Administrador',
  OPERADOR: 'Operador',
  CONDUCTOR: 'Conductor',
  ANALISTA: 'Analista',
  AUDITOR: 'Auditor',
}

export function canManageOperations(role: AuthRole | undefined): boolean {
  return role === 'ADMINISTRADOR' || role === 'OPERADOR'
}

export function canListVehicles(role: AuthRole | undefined): boolean {
  return canManageOperations(role) || role === 'AUDITOR'
}
