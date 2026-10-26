import { MIN_PASSWORD_LENGTH } from '../services/users'

export type PasswordField = 'current' | 'next' | 'confirm'
export type PasswordValues = Record<PasswordField, string>
export type PasswordErrors = Partial<Record<PasswordField, string>>
export const PASSWORD_FIELDS: PasswordField[] = ['current', 'next', 'confirm']

/** ECL-77 field rules, also used to clear a shown error as soon as it is fixed. */
export function validatePasswordField(field: PasswordField, values: PasswordValues): string | undefined {
  if (field === 'current' && !values.current) return 'Escribe tu contraseña actual.'
  if (field === 'next') {
    if (values.next.length < MIN_PASSWORD_LENGTH) return `Usa al menos ${MIN_PASSWORD_LENGTH} caracteres.`
    if (values.current && values.next === values.current) return 'Elige una contraseña distinta de la actual.'
  }
  if (field === 'confirm' && values.confirm !== values.next) return 'Las contraseñas no coinciden. Escríbela de nuevo.'
  return undefined
}
