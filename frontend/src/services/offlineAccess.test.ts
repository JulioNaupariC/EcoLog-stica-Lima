import { forgetDriver, recallDriver, rememberDriver } from './offlineAccess'
import type { LoginResponse } from './auth'

const driver: LoginResponse = { usuario_id: '123e4567-e89b-42d3-a456-426614174005', rol: 'CONDUCTOR', expires_at: new Date(Date.now() + 60_000).toISOString() }
afterEach(() => { vi.restoreAllMocks(); sessionStorage.clear() })

it('restores only the last verified driver hint in the same tab without credentials', () => {
  rememberDriver(driver)
  expect(recallDriver()).toEqual(driver)
  expect(sessionStorage.getItem('ecologistica-driver-tab')).not.toMatch(/password|token|cookie/i)
  forgetDriver()
  expect(recallDriver()).toBeNull()
})

it.each([
  { ...driver, rol: 'ADMINISTRADOR' as const },
  { ...driver, usuario_id: 'invalid' },
  { ...driver, expires_at: 'invalid' },
  { ...driver, expires_at: new Date(0).toISOString() },
  { ...driver, expires_at: new Date(Date.now() + 172_800_000).toISOString() },
  { usuario_id: driver.usuario_id, rol: 'CONDUCTOR' as const },
])('does not persist unsupported/expired hints: %j', value => {
  rememberDriver(driver)
  rememberDriver(value)
  expect(recallDriver()).toBeNull()
})

it.each(['not json', 'null', '123', '{}', JSON.stringify({ ...driver, rol: 'OPERADOR' }), JSON.stringify({ ...driver, expires_at: 'bad' })])('rejects corrupt local hints: %s', raw => {
  sessionStorage.setItem('ecologistica-driver-tab', raw)
  expect(recallDriver()).toBeNull()
})

it('expires a hint and tolerates unavailable storage', () => {
  rememberDriver({ ...driver, expires_at: new Date(Date.now() + 10).toISOString() })
  vi.spyOn(Date, 'now').mockReturnValue(Date.now() + 100)
  expect(recallDriver()).toBeNull()
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('disabled') })
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('disabled') })
  vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => { throw new Error('disabled') })
  rememberDriver(driver)
  expect(recallDriver()).toBeNull()
  expect(() => forgetDriver()).not.toThrow()
})
