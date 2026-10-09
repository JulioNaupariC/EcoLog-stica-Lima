import { PREFERENCE_LIMITS, preferencesPatch, valuesFromPreferences } from './deliveryPreferencesForm'
import { PREFERENCE_FIELDS } from '../services/deliveryPreferences'

const saved = { horario_preferido: 'Mañana', referencia: ' Puerta norte ', restriccion_acceso: null }
it('representa null con limpieza explícita y no envía campos sin cambios', () => {
  const values = valuesFromPreferences(saved)
  expect(values.restriccion_acceso).toEqual({ value: '', cleared: true })
  expect(preferencesPatch(saved, values)).toEqual({ errors: {}, patch: {} })
})
it('preserva espacios y solo envía el cambio; permite limpiar explícitamente', () => {
  const values = valuesFromPreferences(saved)
  values.horario_preferido.value = ' Tarde '
  values.referencia.cleared = true
  expect(preferencesPatch(saved, values)).toEqual({ errors: {}, patch: { horario_preferido: ' Tarde ', referencia: null } })
})
it.each(PREFERENCE_FIELDS)('acepta el límite y rechaza un carácter extra en %s', field => {
  const values = valuesFromPreferences(saved)
  values[field] = { value: 'A'.repeat(PREFERENCE_LIMITS[field]), cleared: false }
  expect(preferencesPatch(saved, values).errors[field]).toBeUndefined()
  values[field].value += 'A'
  expect(preferencesPatch(saved, values).errors[field]).toContain(String(PREFERENCE_LIMITS[field]))
})
it.each(['', '   ', '\n', '\0bad'])('rechaza texto vacío, espacios o NUL: %j', value => {
  const values = valuesFromPreferences(saved)
  values.referencia = { value, cleared: false }
  expect(preferencesPatch(saved, values).errors.referencia).toBeDefined()
})
it('cuenta caracteres Unicode como el backend y permite deshacer limpieza', () => {
  const values = valuesFromPreferences(saved)
  values.horario_preferido = { value: '🚚'.repeat(120), cleared: false }
  expect(preferencesPatch(saved, values).errors).toEqual({})
  values.referencia.cleared = true
  values.referencia.cleared = false
  expect(preferencesPatch(saved, values).patch).not.toHaveProperty('referencia')
})
