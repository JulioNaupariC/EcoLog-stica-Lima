import { PREFERENCE_FIELDS } from '../services/deliveryPreferences'
import type { PreferenceField, Preferences, PreferencesPatch } from '../services/deliveryPreferences'

export interface PreferenceInput { value: string; cleared: boolean }
export type PreferencesValues = Record<PreferenceField, PreferenceInput>
export type PreferencesErrors = Partial<Record<PreferenceField, string>>
export const PREFERENCE_LIMITS: Record<PreferenceField, number> = {
  horario_preferido: 120, referencia: 255, restriccion_acceso: 255,
}
export function valuesFromPreferences(saved: Preferences): PreferencesValues {
  return {
    horario_preferido: { value: saved.horario_preferido ?? '', cleared: saved.horario_preferido === null },
    referencia: { value: saved.referencia ?? '', cleared: saved.referencia === null },
    restriccion_acceso: { value: saved.restriccion_acceso ?? '', cleared: saved.restriccion_acceso === null },
  }
}
export function preferencesPatch(saved: Preferences, values: PreferencesValues): { errors: PreferencesErrors; patch: PreferencesPatch } {
  const errors: PreferencesErrors = {}
  const patch: PreferencesPatch = {}
  for (const field of PREFERENCE_FIELDS) {
    const input = values[field]
    const value = input.cleared ? null : input.value
    if (value !== null) {
      if (!value.trim()) errors[field] = 'Escribe una preferencia o marca la opción para dejarla sin definir.'
      else if (value.includes('\0')) errors[field] = 'El texto contiene un carácter no permitido.'
      else if (Array.from(value).length > PREFERENCE_LIMITS[field]) errors[field] = `Usa como máximo ${PREFERENCE_LIMITS[field]} caracteres.`
    }
    if (value !== saved[field]) patch[field] = value
  }
  return { errors, patch }
}
