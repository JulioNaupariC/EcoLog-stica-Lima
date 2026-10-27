import type { IncidentPage, PendingIncident } from '../services/incidentList'

/** Synthetic examples for ECL-75; no real drivers or contact information. */
export const pendingIncident: PendingIncident = {
  incidencia_id: '123e4567-e89b-42d3-a456-426614174000',
  tipo: 'AVERIA', severidad: 'ALTA', ocurrida_en: '2026-10-26T14:15:00Z',
  registrada_en: '2026-10-26T09:16:00-05:00',
  conductor: { conductor_id: '223e4567-e89b-42d3-a456-426614174000', nombre: 'Conductor de prueba' },
  latitud: -12.0464123, longitud: -77.0428123,
  observacion: 'Llanta pinchada en avenida de ejemplo.', estado: 'PENDIENTE_VALIDACION',
}

export const pendingIncidentPage: IncidentPage = {
  items: [pendingIncident], page: 1, page_size: 20, total: 1,
}
