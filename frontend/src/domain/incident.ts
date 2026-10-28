export const INCIDENT_TYPES = {
  TRAFICO: 'Tráfico', AVERIA: 'Avería', ACCIDENTE: 'Accidente',
  CLIMA: 'Clima', SEGURIDAD: 'Seguridad', OTRO: 'Otro',
} as const
export const INCIDENT_SEVERITIES = {
  BAJA: 'Baja · Permite continuar', MEDIA: 'Media · Dificulta la operación',
  ALTA: 'Alta · Impide continuar con seguridad',
} as const

export interface IncidentLocation {
  latitud: number
  longitud: number
  parada_id?: string
}
export interface IncidentDraft {
  operation_id?: string
  tipo: keyof typeof INCIDENT_TYPES | ''
  severidad: keyof typeof INCIDENT_SEVERITIES | ''
  ocurrida_en: string
  ubicacion: IncidentLocation | null
  observacion: string
}
export interface IncidentPayload extends IncidentLocation {
  operation_id: string
  tipo: keyof typeof INCIDENT_TYPES
  severidad: keyof typeof INCIDENT_SEVERITIES
  ocurrida_en: string
  observacion: string
}
export interface IncidentAcknowledgement {
  incidencia_id: string
  operation_id: string
  estado: 'PENDIENTE_VALIDACION'
  registrada_en: string
}
export interface StoredIncident {
  ownerId: string
  payload: IncidentPayload
  createdAt: number
  errorStatus?: number
  acknowledgement?: IncidentAcknowledgement
}
export type IncidentErrors = Partial<Record<keyof IncidentDraft, string>>

export function newIncidentDraft(): IncidentDraft {
  return { tipo: '', severidad: '', ocurrida_en: new Date().toISOString(), ubicacion: null, observacion: '' }
}
export function validLocation(value: IncidentLocation | null): value is IncidentLocation {
  return value !== null && Number.isFinite(value.latitud) && Math.abs(value.latitud) <= 90 &&
    Number.isFinite(value.longitud) && Math.abs(value.longitud) <= 180
}
export function validateIncident(draft: IncidentDraft): IncidentErrors {
  const errors: IncidentErrors = {}
  if (!Object.hasOwn(INCIDENT_TYPES, draft.tipo)) errors.tipo = 'Selecciona el tipo de incidencia.'
  if (!Object.hasOwn(INCIDENT_SEVERITIES, draft.severidad)) errors.severidad = 'Selecciona la severidad.'
  if (!validLocation(draft.ubicacion)) errors.ubicacion = 'Usa tu ubicación o selecciona una parada con coordenadas.'
  if (!Number.isFinite(Date.parse(draft.ocurrida_en)) || Date.parse(draft.ocurrida_en) > Date.now() + 300_000) {
    errors.ocurrida_en = 'La hora del dispositivo está adelantada. Revisa su reloj antes de crear otro reporte.'
  }
  if ([...draft.observacion].length > 500) errors.observacion = 'La observación admite hasta 500 caracteres.'
  return errors
}
