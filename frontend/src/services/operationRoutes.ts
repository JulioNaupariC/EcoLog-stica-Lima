import { buildApiUrl } from './api'
import { validUuid } from '../types/driverReport'
import { InvalidRouteData, parseOptimization, parseOptimizationPage, validOperationDate } from '../domain/operationRoutes'
import type { OptimizationDetail, OptimizationPage } from '../domain/operationRoutes'

export interface RouteSource {
  list: (date: string, page: number, signal: AbortSignal) => Promise<OptimizationPage>
  detail: (id: string, signal: AbortSignal) => Promise<OptimizationDetail>
}
type ErrorKind = 'unauthorized' | 'forbidden' | 'not_found' | 'unavailable'
const MESSAGES: Record<ErrorKind, string> = {
  unauthorized: 'Tu sesión ha vencido. Vuelve a iniciar sesión.',
  forbidden: 'Solo Administrador y Operador pueden consultar el detalle de las rutas.',
  not_found: 'La optimización ya no está disponible. Actualiza el listado.',
  unavailable: 'No se pudieron cargar las rutas. Revisa tu conexión e intenta de nuevo.',
}
export class OperationRoutesError extends Error {
  constructor(readonly kind: ErrorKind) { super(MESSAGES[kind]); this.name = 'OperationRoutesError' }
}
async function request(path: string, signal: AbortSignal): Promise<unknown> {
  let response: Response
  try {
    response = await fetch(buildApiUrl(path), { credentials: 'include', cache: 'no-store',
      signal: AbortSignal.any([signal, AbortSignal.timeout(15_000)]) })
  } catch (error) {
    if (signal.aborted) throw error
    throw new OperationRoutesError('unavailable')
  }
  if (response.status !== 200) throw new OperationRoutesError(response.status === 401 ? 'unauthorized'
    : response.status === 403 ? 'forbidden' : response.status === 404 ? 'not_found' : 'unavailable')
  try { return await response.json() } catch { throw new InvalidRouteData() }
}
/** Same GET contract for ST-045 fixtures and ST-047's future optimizer. */
export const operationRoutesApi: RouteSource = {
  async list(date, page, signal) {
    if (!validOperationDate(date) || !Number.isInteger(page) || page < 1) throw new InvalidRouteData()
    const result = parseOptimizationPage(await request(`optimizaciones?fecha=${date}&page=${page}&page_size=12`, signal))
    if (result.page !== page || result.page_size !== 12 || result.items.some(item => item.fecha_operacion !== date)) throw new InvalidRouteData()
    return result
  },
  async detail(id, signal) {
    if (!validUuid(id)) throw new InvalidRouteData()
    const result = parseOptimization(await request(`optimizaciones/${id}`, signal))
    if (result.optimizacion_id !== id) throw new InvalidRouteData()
    return result
  },
}
