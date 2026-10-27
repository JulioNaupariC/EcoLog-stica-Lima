import { INCIDENT_SEVERITIES, INCIDENT_TYPES, newIncidentDraft, validateIncident, validLocation } from './incident'

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

const catalogCases = Object.keys(INCIDENT_TYPES).flatMap(tipo => Object.keys(INCIDENT_SEVERITIES).map(severidad =>
  [tipo as keyof typeof INCIDENT_TYPES, severidad as keyof typeof INCIDENT_SEVERITIES] as const))
it.each(catalogCases)('I14 ruta de borde: admite catálogo %s / %s', (tipo, severidad) => {
  expect(validateIncident({ ...newIncidentDraft(), tipo, severidad,
    ubicacion: { latitud: -12, longitud: -77 } })).toEqual({})
})

it.each([-86_400_000_000, 0, 300_000, 301_000])(
  'I05/I14 ruta de borde: reloj fijo y desfase %i ms', offset => {
    vi.useFakeTimers()
    try {
      vi.setSystemTime(new Date('2026-10-27T14:16:02Z'))
      const errors = validateIncident({ ...newIncidentDraft(), tipo: 'OTRO', severidad: 'BAJA',
        ubicacion: { latitud: 90, longitud: -180 }, ocurrida_en: new Date(Date.now() + offset).toISOString() })
      expect(Boolean(errors.ocurrida_en)).toBe(offset > 300_000)
    } finally { vi.useRealTimers() }
  },
)
