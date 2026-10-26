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

/** ECL-77: user list and password reset require usuarios.actualizar (Administrator only). */
export function canManageUsers(role: AuthRole | undefined): boolean {
  return role === 'ADMINISTRADOR'
}

export function canListVehicles(role: AuthRole | undefined): boolean {
  return canManageOperations(role) || role === 'AUDITOR'
}

/** indicadores.consultar with general scope (RBAC): every role except the driver, whose scope is its own. */
export function canViewOperationIndicators(role: AuthRole | undefined): boolean {
  return role !== undefined && role !== 'CONDUCTOR'
}
