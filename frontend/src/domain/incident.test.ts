import { newIncidentDraft, validateIncident, validLocation } from './incident'

it('ruta infeliz: identifica obligatorios y conserva las cadenas sin truncar', () => {
  const draft = newIncidentDraft()
  expect(Object.keys(validateIncident(draft))).toEqual(['tipo', 'severidad', 'ubicacion'])
  draft.observacion = '😀'.repeat(501)
  expect(validateIncident(draft).observacion).toBeDefined()
  expect([...draft.observacion]).toHaveLength(501)
})
it('ruta de borde: mide Unicode por puntos de código y admite extremos de coordenadas', () => {
  expect(validateIncident({ ...newIncidentDraft(), tipo: 'OTRO', severidad: 'BAJA',
    ubicacion: { latitud: -90, longitud: 180 }, observacion: '😀'.repeat(500) })).toEqual({})
  expect(validLocation({ latitud: NaN, longitud: 0 })).toBe(false)
  expect(validLocation({ latitud: 90.1, longitud: 0 })).toBe(false)
  expect(validLocation({ latitud: 0, longitud: Infinity })).toBe(false)
})
it('ruta infeliz: detecta hora inválida o adelantada más de cinco minutos', () => {
  expect(validateIncident({ ...newIncidentDraft(), ocurrida_en: 'invalid' }).ocurrida_en).toBeDefined()
  expect(validateIncident({ ...newIncidentDraft(), ocurrida_en: new Date(Date.now() + 301_000).toISOString() }).ocurrida_en).toBeDefined()
})
