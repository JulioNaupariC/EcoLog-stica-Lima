import { buildApiUrl, parseApiBaseUrl } from './api'

describe('configuración de API', () => {
  it('acepta una URL base HTTP válida', () => {
    expect(parseApiBaseUrl('http://127.0.0.1:8000').href).toBe(
      'http://127.0.0.1:8000/',
    )
  })

  it('acepta una URL base HTTPS válida', () => {
    expect(parseApiBaseUrl('https://api.example.test/v1').href).toBe(
      'https://api.example.test/v1',
    )
  })

  it('acepta una URL base con trailing slash', () => {
    expect(parseApiBaseUrl('https://api.example.test/v1/').href).toBe(
      'https://api.example.test/v1/',
    )
  })

  it('construye un path relativo dentro de la ruta base configurada', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/v1')

    expect(buildApiUrl('status')).toBe('https://api.example.test/v1/status')
  })

  it('combina barras sin producir separadores duplicados', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/v1/')

    expect(buildApiUrl('/status')).toBe('https://api.example.test/v1/status')
  })

  it.each([undefined, '', '   '])('rechaza una variable ausente: %s', (value) => {
    expect(() => parseApiBaseUrl(value)).toThrow(
      'VITE_API_BASE_URL es obligatoria.',
    )
  })

  it('rechaza una URL inválida', () => {
    expect(() => parseApiBaseUrl('no-es-una-url')).toThrow(
      'VITE_API_BASE_URL debe ser una URL válida.',
    )
  })

  it('rechaza protocolos no permitidos', () => {
    expect(() => parseApiBaseUrl('ftp://example.test')).toThrow(
      'VITE_API_BASE_URL debe usar el protocolo http o https.',
    )
  })

  it.each([
    'http://otro-host.test/resource',
    'https://otro-host.test/resource',
    '//otro-host.test/resource',
  ])('rechaza un path capaz de sustituir el origen: %s', (path) => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/v1')

    expect(() => buildApiUrl(path)).toThrow(
      'El path del API debe ser relativo a VITE_API_BASE_URL.',
    )
  })

  it('rechaza traversal fuera del pathname base', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/v1')

    expect(() => buildApiUrl('../status')).toThrow(
      'El path del API no puede cambiar el origen ni escapar de la ruta base.',
    )
  })

  it.each([
    'http://user@localhost:8000',
    'http://user:password@localhost:8000',
  ])('rechaza una base con credenciales: %s', (baseUrl) => {
    expect(() => parseApiBaseUrl(baseUrl)).toThrow(
      'VITE_API_BASE_URL no debe incluir credenciales.',
    )
  })

  it('rechaza una base con query', () => {
    expect(() => parseApiBaseUrl('http://localhost:8000?x=1')).toThrow(
      'VITE_API_BASE_URL no debe incluir parámetros de consulta.',
    )
  })

  it('rechaza una base con fragmento', () => {
    expect(() => parseApiBaseUrl('http://localhost:8000#fragment')).toThrow(
      'VITE_API_BASE_URL no debe incluir fragmentos.',
    )
  })
})
