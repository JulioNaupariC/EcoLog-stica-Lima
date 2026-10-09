import { changedDriverFields, EMPTY_DRIVER, limaInput, validateDriver, valuesFromDriver } from './driverForm'
import type { DriverDetail } from '../services/drivers'

const values = { ...EMPTY_DRIVER, nombre: ' Rosa Prueba ', dni: '01234567', licencia_numero: ' lic-01 ',
  licencia_vigente_hasta: '2099-12-31', experiencia_anios: '0', telefono: '+51987654321',
  punto_partida: ' Base Lima ', disponible_desde: '2099-10-09T08:15', disponible_hasta: '2099-10-09T17:15',
  email: ' rosa@example.test ', password: 'synthetic-password' }
const driver: DriverDetail = { ...validateDriver(values, false, false).profile!,
  conductor_id: '123e4567-e89b-12d3-a456-426614174000', usuario_id: '223e4567-e89b-12d3-a456-426614174000',
  nombre: 'Rosa Prueba', licencia_numero: 'LIC-01', punto_partida: 'Base Lima', estado: 'ACTIVO', habilitado_asignacion: true }

it('normaliza campos y convierte hora de Lima a UTC sin depender del navegador', () => {
  const result = validateDriver(values, false, false)
  expect(result.errors).toEqual({})
  expect(result.create).toMatchObject({ dni: '01234567', nombre: 'Rosa Prueba', email: 'rosa@example.test',
    licencia_numero: 'LIC-01', experiencia_anios: 0, disponible_desde: '2099-10-09T13:15:00.000Z' })
  expect(limaInput('2099-10-09T13:15:00.123456Z')).toBe('2099-10-09T08:15:00.123')
  expect(limaInput(null)).toBe('')
})

it.each([
  ['nombre', ''], ['nombre', 'x'.repeat(161)], ['dni', '1234567'], ['dni', 'abcdefgh'],
  ['licencia_numero', ' '], ['licencia_numero', 'x'.repeat(21)],
  ['licencia_vigente_hasta', '2026-02-30'], ['licencia_vigente_hasta', 'invalid'],
  ['licencia_vigente_hasta', '0000-01-01'], ['experiencia_anios', '-1'], ['experiencia_anios', '1.5'],
  ['experiencia_anios', '2147483648'], ['telefono', '987654321'], ['punto_partida', ''],
  ['punto_partida', 'x'.repeat(256)], ['disponible_desde', ''], ['disponible_hasta', '2099-10-09T07:00'],
  ['disponible_desde', '2099-02-30T08:00'], ['email', 'invalid'], ['password', ''],
  ['password', 'x'.repeat(1025)],
] as const)('valida %s y rechaza valores inválidos', (field, value) => {
  const result = validateDriver({ ...values, [field]: value }, false, false)
  expect(result.errors[field]).toBeTruthy()
  expect(result.profile).toBeUndefined()
})

it('permite licencia vencida y retirar disponibilidad sólo en edición', () => {
  expect(validateDriver({ ...values, licencia_vigente_hasta: '2000-01-01' }, false, false).create).toBeDefined()
  const result = validateDriver({ ...values, email: '', password: '', disponible_desde: '', disponible_hasta: '' }, true, true)
  expect(result.profile).toMatchObject({ disponible_desde: null, disponible_hasta: null })
  expect(result.create).toBeUndefined()
})

it('envía sólo cambios y preserva precisión temporal al editar otros campos', () => {
  const original = { ...driver, disponible_desde: '2099-10-09T13:15:00.123456Z' }
  const initial = valuesFromDriver(original)
  const form = { ...initial, telefono: '+51987654322' }
  expect(changedDriverFields(original, form, validateDriver(form, true, false).profile!)).toEqual({ telefono: '+51987654322' })
  expect(changedDriverFields(driver, valuesFromDriver(driver), driver)).toEqual({})
  const removed = validateDriver(initial, true, true).profile!
  expect(changedDriverFields(original, initial, removed)).toEqual({ disponible_desde: null, disponible_hasta: null })
  const changed = { ...initial, disponible_hasta: '2099-10-10T10:00' }
  expect(changedDriverFields(original, changed, validateDriver(changed, true, false).profile!)).toHaveProperty('disponible_desde')
})

it('no inventa fechas para un perfil sin disponibilidad', () => {
  const original = { ...driver, disponible_desde: null, disponible_hasta: null }
  const form = valuesFromDriver(original)
  expect(form.disponible_desde).toBe('')
  expect(changedDriverFields(original, form, validateDriver(form, true, true).profile!)).toEqual({})
})
