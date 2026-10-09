import type { DriverCreate, DriverDetail, DriverField, DriverProfile } from '../services/drivers'

export type DriverValues = Record<DriverField, string>
export type DriverErrors = Partial<Record<DriverField, string>>
export const EMPTY_DRIVER: DriverValues = {
  nombre: '', dni: '', licencia_numero: '', licencia_vigente_hasta: '', experiencia_anios: '',
  telefono: '', punto_partida: '', disponible_desde: '', disponible_hasta: '', email: '', password: '',
}
export function limaInput(iso: string | null): string {
  if (!iso) return ''
  // Lima is UTC-05:00. Do not use the browser's timezone for the operational form.
  return new Date(Date.parse(iso) - 5 * 60 * 60 * 1000).toISOString().slice(0, -1)
}
export function valuesFromDriver(driver: DriverDetail): DriverValues {
  return { nombre: driver.nombre, dni: driver.dni, licencia_numero: driver.licencia_numero,
    licencia_vigente_hasta: driver.licencia_vigente_hasta, experiencia_anios: String(driver.experiencia_anios),
    telefono: driver.telefono, punto_partida: driver.punto_partida,
    disponible_desde: limaInput(driver.disponible_desde), disponible_hasta: limaInput(driver.disponible_hasta),
    email: '', password: '' }
}
export function validateDriver(values: DriverValues, editing: boolean, clearAvailability: boolean): {
  errors: DriverErrors; profile?: DriverProfile; create?: DriverCreate
} {
  const errors: DriverErrors = {}
  const nombre = values.nombre.trim()
  const dni = values.dni.trim()
  const licencia = values.licencia_numero.trim().toUpperCase()
  const telefono = values.telefono.trim()
  const partida = values.punto_partida.trim()
  if (!nombre || Array.from(nombre).length > 160) errors.nombre = 'Ingresa un nombre de 1 a 160 caracteres.'
  if (!/^[0-9]{8}$/u.test(dni)) errors.dni = 'El DNI debe tener exactamente 8 dígitos.'
  if (!licencia || Array.from(licencia).length > 20) errors.licencia_numero = 'Ingresa una licencia de 1 a 20 caracteres.'
  const expiry = values.licencia_vigente_hasta
  if (!/^\d{4}-\d{2}-\d{2}$/u.test(expiry) || (!Number.isFinite(Date.parse(expiry)) || Number(expiry.slice(0, 4)) < 1) ||
    new Date(expiry).toISOString().slice(0, 10) !== expiry) errors.licencia_vigente_hasta = 'Ingresa una fecha de vencimiento válida.'
  if (!/^[0-9]+$/u.test(values.experiencia_anios) || Number(values.experiencia_anios) > 2147483647) {
    errors.experiencia_anios = 'Ingresa años de experiencia como un entero no negativo.'
  }
  if (!/^\+[1-9][0-9]{7,14}$/u.test(telefono)) errors.telefono = 'Usa formato internacional, por ejemplo +51987654321.'
  if (!partida || Array.from(partida).length > 255) errors.punto_partida = 'Ingresa un punto de partida de 1 a 255 caracteres.'
  let desde: string | null = null
  let hasta: string | null = null
  if (!editing || !clearAvailability) {
    const pattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,3})?)?$/u
    for (const field of ['disponible_desde', 'disponible_hasta'] as const) {
      if (!pattern.test(values[field]) || (!Number.isFinite(Date.parse(values[field] + '-05:00')) || Number(values[field].slice(0, 4)) < 1 ||
        new Date(values[field] + 'Z').toISOString().slice(0, 10) !== values[field].slice(0, 10))) {
        errors[field] = 'Ingresa fecha y hora de Lima.'
      }
    }
    if (!errors.disponible_desde && !errors.disponible_hasta) {
      desde = new Date(values.disponible_desde + '-05:00').toISOString()
      hasta = new Date(values.disponible_hasta + '-05:00').toISOString()
      if (hasta <= desde) errors.disponible_hasta = 'El final debe ser posterior al inicio.'
    }
  }
  const email = values.email.trim()
  if (!editing) {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/u.test(email) || Array.from(email).length > 255) errors.email = 'Ingresa un correo electrónico válido.'
    if (!values.password || Array.from(values.password).length > 1024) errors.password = 'Ingresa una contraseña inicial de 1 a 1024 caracteres.'
  }
  if (Object.keys(errors).length) return { errors }
  const profile: DriverProfile = { nombre, dni, licencia_numero: licencia, licencia_vigente_hasta: expiry,
    experiencia_anios: Number(values.experiencia_anios), telefono, punto_partida: partida, disponible_desde: desde, disponible_hasta: hasta }
  return { errors, profile, ...(!editing ? { create: { ...profile, email, password: values.password } } : {}) }
}
export function changedDriverFields(original: DriverDetail, values: DriverValues, profile: DriverProfile): Partial<DriverProfile> {
  const before = valuesFromDriver(original)
  const changes: Partial<DriverProfile> = {}
  for (const field of ['nombre', 'dni', 'licencia_numero', 'licencia_vigente_hasta', 'experiencia_anios', 'telefono', 'punto_partida'] as const) {
    if (profile[field] !== original[field]) Object.assign(changes, { [field]: profile[field] })
  }
  const clearing = profile.disponible_desde === null
  if ((clearing && original.disponible_desde !== null) || (!clearing &&
    (values.disponible_desde !== before.disponible_desde || values.disponible_hasta !== before.disponible_hasta))) {
    changes.disponible_desde = profile.disponible_desde
    changes.disponible_hasta = profile.disponible_hasta
  }
  return changes
}
