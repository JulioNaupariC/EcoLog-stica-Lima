import { registerOfflineShell } from './offlineShell'

afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals() })

it('registers the public worker only in production and at the configured base', () => {
  const register = vi.fn().mockResolvedValue({})
  vi.stubGlobal('navigator', { serviceWorker: { register } })
  vi.stubEnv('PROD', true)
  vi.stubEnv('BASE_URL', '/ecolog/')
  registerOfflineShell()
  expect(register).toHaveBeenCalledWith('/ecolog/sw.js')
})

it('does not install a worker in development or unsupported browsers', () => {
  const register = vi.fn()
  vi.stubGlobal('navigator', { serviceWorker: { register } })
  vi.stubEnv('PROD', false)
  registerOfflineShell()
  expect(register).not.toHaveBeenCalled()
  vi.stubEnv('PROD', true)
  vi.stubGlobal('navigator', {})
  expect(() => registerOfflineShell()).not.toThrow()
})

it('handles registration failure without claiming offline readiness', async () => {
  vi.stubEnv('PROD', true)
  vi.stubGlobal('navigator', { serviceWorker: { register: vi.fn().mockRejectedValue(new Error('storage disabled')) } })
  registerOfflineShell()
  await Promise.resolve()
})
