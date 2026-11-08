import { buildApiUrl } from './api'
import { InvalidSustainability, parseSustainability, validPeriod } from '../domain/sustainability'
import type { Period, Sustainability } from '../domain/sustainability'

type ErrorKind = 'unauthorized' | 'forbidden' | 'invalid_period' | 'unavailable'
const MESSAGES: Record<ErrorKind, string> = {
  unauthorized: 'Tu sesión ha vencido. Vuelve a iniciar sesión.',
  forbidden: 'No tienes permisos para consultar los indicadores de sostenibilidad.',
  invalid_period: 'Revisa el periodo: indica fechas válidas y un inicio anterior o igual al fin.',
  unavailable: 'No se pudieron cargar los indicadores. Revisa tu conexión e intenta de nuevo.',
}
export class SustainabilityError extends Error {
  constructor(readonly kind: ErrorKind) { super(MESSAGES[kind]); this.name = 'SustainabilityError' }
}
export interface SustainabilitySource {
  load: (period: Period, signal: AbortSignal) => Promise<Sustainability>
}
export const sustainabilityApi: SustainabilitySource = {
  async load(period, signal) {
    if (!validPeriod(period)) throw new SustainabilityError('invalid_period')
    let response: Response
    try {
      response = await fetch(buildApiUrl(`indicadores/sostenibilidad?${new URLSearchParams({ ...period })}`), {
        credentials: 'include', cache: 'no-store', signal: AbortSignal.any([signal, AbortSignal.timeout(15_000)]),
      })
    } catch (error) { if (signal.aborted) throw error; throw new SustainabilityError('unavailable') }
    if (response.status !== 200) throw new SustainabilityError(response.status === 401 ? 'unauthorized'
      : response.status === 403 ? 'forbidden' : response.status === 422 ? 'invalid_period' : 'unavailable')
    let raw: unknown
    try {
      const text = await response.text()
      if (new TextEncoder().encode(text).length > 250_000) throw new InvalidSustainability()
      raw = JSON.parse(text)
    } catch { throw new InvalidSustainability() }
    return parseSustainability(raw, period)
  },
}
