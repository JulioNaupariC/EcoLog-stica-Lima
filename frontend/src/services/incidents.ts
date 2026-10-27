import type { IncidentAcknowledgement, IncidentPayload } from '../domain/incident'
import { validUuid } from '../types/driverReport'
import { buildApiUrl } from './api'

export class IncidentServiceError extends Error {
  constructor(readonly status: number) {
    super(status === 401 ? 'Tu sesión venció. Inicia sesión con la misma cuenta para continuar.'
      : status === 403 ? 'No se pudo registrar: la sesión no tiene permiso para esta incidencia.'
      : status === 409 ? 'Hay un conflicto con este envío. Conservamos el reporte; solicita revisión antes de crear otro.'
      : status === 422 ? 'El servicio solicita corregir los datos. Conservamos el reporte para revisarlo.'
      : 'El servicio no está disponible. Conservamos el reporte para reintentar.')
    this.name = 'IncidentServiceError'
  }
}
export async function sendIncident(payload: IncidentPayload, ownerId: string, signal?: AbortSignal): Promise<IncidentAcknowledgement> {
  if (!validUuid(ownerId)) throw new Error('Identidad inválida.')
  const timeout = AbortSignal.timeout(15_000)
  const response = await fetch(buildApiUrl('conductor/incidencias'), {
    method: 'POST', credentials: 'include', cache: 'no-store',
    signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    headers: { 'Content-Type': 'application/json', 'X-Expected-Owner-ID': ownerId }, body: JSON.stringify(payload),
  })
  if (response.status !== 200 && response.status !== 201) throw new IncidentServiceError(response.status)
  const body: unknown = await response.json()
  if (!body || typeof body !== 'object') throw new Error('Confirmación inválida.')
  const ack = body as Partial<IncidentAcknowledgement>
  if (ack.operation_id !== payload.operation_id || !validUuid(ack.incidencia_id) ||
    ack.estado !== 'PENDIENTE_VALIDACION' || typeof ack.registrada_en !== 'string' ||
    !Number.isFinite(Date.parse(ack.registrada_en))) throw new Error('Confirmación inválida.')
  return ack as IncidentAcknowledgement
}
