import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { changedDriverFields, EMPTY_DRIVER, licenseExpired, validateDriver, valuesFromDriver } from '../domain/driverForm'
import type { DriverErrors, DriverValues } from '../domain/driverForm'
import { Save, X } from 'lucide-react'
import { Alert, Badge, Button, FormActions, FormSection, StatusBadge } from './ui'
import { createDriver, DriverServiceError, updateDriver } from '../services/drivers'
import type { DriverDetail, DriverField, DriverSummary } from '../services/drivers'

const FIELDS: { name: DriverField; label: string; type: string; max?: number; hint: string }[] = [
  { name: 'nombre', label: 'Nombre completo', type: 'text', max: 160, hint: 'Como figura en su documento.' },
  { name: 'dni', label: 'DNI', type: 'text', max: 8, hint: '8 dígitos. No se muestra en el listado.' },
  { name: 'licencia_numero', label: 'Número de licencia', type: 'text', max: 20, hint: 'Hasta 20 caracteres.' },
  { name: 'licencia_vigente_hasta', label: 'Licencia vigente hasta', type: 'date', hint: 'Una licencia vencida impide la asignación.' },
  { name: 'experiencia_anios', label: 'Experiencia (años)', type: 'number', hint: 'Años completos de experiencia.' },
  { name: 'telefono', label: 'Teléfono', type: 'tel', max: 16, hint: 'Formato internacional. Ej.: +51987654321.' },
  { name: 'punto_partida', label: 'Punto de partida', type: 'text', max: 255, hint: 'Base desde la que inicia su jornada.' },
  { name: 'disponible_desde', label: 'Disponible desde (hora de Lima)', type: 'datetime-local', hint: 'Inicio de la franja de disponibilidad.' },
  { name: 'disponible_hasta', label: 'Disponible hasta (hora de Lima)', type: 'datetime-local', hint: 'Debe ser posterior al inicio.' },
  { name: 'email', label: 'Correo del conductor', type: 'email', max: 255, hint: 'Será su usuario para iniciar sesión.' },
  { name: 'password', label: 'Contraseña inicial', type: 'password', max: 1024, hint: 'Se envía solo al registrar; no se guarda en el navegador.' },
]

const GROUPS: { legend: string; fields: DriverField[]; createOnly?: boolean }[] = [
  { legend: 'Identidad y licencia', fields: ['nombre', 'dni', 'licencia_numero', 'licencia_vigente_hasta', 'experiencia_anios'] },
  { legend: 'Contacto y base', fields: ['telefono', 'punto_partida'] },
  { legend: 'Disponibilidad', fields: ['disponible_desde', 'disponible_hasta'] },
  { legend: 'Cuenta de acceso', fields: ['email', 'password'], createOnly: true },
]

interface Props {
  driver: DriverDetail | null
  onSaved: (driver: DriverSummary, created: boolean) => void
  onCancel: () => void
  onAccessError: (error: DriverServiceError) => void
}
export function DriverForm({ driver, onSaved, onCancel, onAccessError }: Props) {
  const [values, setValues] = useState<DriverValues>(() => driver ? valuesFromDriver(driver) : { ...EMPTY_DRIVER })
  const [clearAvailability, setClearAvailability] = useState(driver?.disponible_desde === null)
  const [errors, setErrors] = useState<DriverErrors>({})
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)
  const inFlight = useRef(false)
  const title = useRef<HTMLHeadingElement>(null)
  const alert = useRef<HTMLDivElement>(null)
  useEffect(() => { title.current?.focus() }, [])
  useEffect(() => { if (message) alert.current?.focus() }, [message])

  // Inline validation: checks a field with content when the user leaves it.
  function validateField(field: DriverField) {
    if (!values[field]) return
    const fieldError = validateDriver(values, driver !== null, clearAvailability).errors[field]
    setErrors(previous => ({ ...previous, [field]: fieldError }))
  }
  function change(field: DriverField, value: string) {
    setValues(previous => ({ ...previous, [field]: value }))
    setErrors(previous => ({ ...previous, [field]: undefined }))
    setMessage('')
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (inFlight.current) return
    const result = validateDriver(values, driver !== null, clearAvailability)
    setErrors(result.errors)
    if (!result.profile) {
      setMessage('Revisa los campos indicados antes de guardar.')
      return
    }
    if (driver && Object.keys(changedDriverFields(driver, values, result.profile)).length === 0) {
      setMessage('No hay cambios para guardar.')
      return
    }
    inFlight.current = true
    setSaving(true)
    setMessage('')
    try {
      const saved = driver
        ? await updateDriver(driver.conductor_id, changedDriverFields(driver, values, result.profile))
        : await createDriver(result.create!)
      setValues(previous => ({ ...previous, password: '' }))
      onSaved(saved, driver === null)
    } catch (error) {
      setValues(previous => ({ ...previous, password: '' }))
      if (error instanceof DriverServiceError) {
        onAccessError(error)
        setErrors(Object.fromEntries(error.fields.map(field => [field, 'Revisa este campo.'])))
        setMessage(error.kind === 'network' && !driver
          ? 'No se pudo confirmar el registro. Actualiza el listado antes de reintentar; vuelve a ingresar la contraseña.'
          : error.message)
      } else {
        setMessage('No se pudo guardar el conductor.')
      }
    } finally {
      inFlight.current = false
      setSaving(false)
    }
  }
  function renderField(name: DriverField) {
    const field = FIELDS.find(item => item.name === name)!
    const availability = name === 'disponible_desde' || name === 'disponible_hasta'
    const error = errors[name]
    const describedBy = [error ? 'driver-error-' + name : null, 'driver-hint-' + name].filter(Boolean).join(' ')
    return <div className="form-field" key={name}>
      <label htmlFor={'driver-' + name}>{field.label}</label>
      <input id={'driver-' + name} name={name} type={field.type}
        value={values[name]} onChange={event => { change(name, event.target.value) }}
        onBlur={() => validateField(name)}
        maxLength={field.max} min={name === 'experiencia_anios' ? 0 : undefined}
        step={availability ? '0.001' : name === 'experiencia_anios' ? '1' : undefined}
        inputMode={name === 'dni' ? 'numeric' : undefined}
        autoComplete={name === 'password' ? 'new-password' : 'off'}
        disabled={availability && clearAvailability} required={!clearAvailability || !availability}
        aria-invalid={Boolean(error)} aria-describedby={describedBy} />
      {error ? <p className="field-error" id={'driver-error-' + name}>{error}</p> : null}
      <p className="field-hint" id={'driver-hint-' + name}>{field.hint}</p>
    </div>
  }
  const expired = driver ? licenseExpired(driver.licencia_vigente_hasta) : false
  return (
    <section className="card driver-editor" aria-labelledby="driver-form-title">
      <div className="card-header">
        <div className="card-heading">
          <h2 id="driver-form-title" className="card-title" tabIndex={-1} ref={title}>
            {driver ? 'Perfil de ' + driver.nombre : 'Registrar conductor'}
          </h2>
          <p className="card-description">{driver
            ? 'Consulta y actualiza el perfil. La cuenta y sus credenciales no se modifican aquí.'
            : 'Registra el perfil y una cuenta independiente con rol Conductor. Todos los campos son obligatorios.'}</p>
        </div>
        {driver ? <div className="badge-row">
          <StatusBadge status={driver.habilitado_asignacion ? 'HABILITADO' : 'NO_HABILITADO'} />
          {expired ? <StatusBadge status="VENCIDA" /> : null}
          {driver.disponible_desde === null ? <Badge tone="warning">Sin disponibilidad</Badge> : null}
        </div> : null}
      </div>
      {driver && !driver.habilitado_asignacion ? <Alert tone="warning" role="note">
        No habilitado para asignación: revisa vigencia, disponibilidad y estado de la cuenta.
      </Alert> : null}
      <form className="form-stack driver-form" onSubmit={event => { void submit(event) }} noValidate aria-label={driver ? 'Editar conductor' : 'Registrar conductor'} aria-busy={saving}>
        {message ? <Alert tone="danger" tabIndex={-1} ref={alert}>{message}</Alert> : null}
        <fieldset disabled={saving} className="form-stack">
          <legend className="visually-hidden">Datos del conductor</legend>
          {GROUPS.filter(group => !driver || !group.createOnly).map(group => (
            <FormSection key={group.legend} legend={group.legend}>
              <div className="form-grid">{group.fields.map(renderField)}</div>
              {group.legend === 'Disponibilidad' ? <>
                {driver ? <label className="checkbox-field">
                  <input type="checkbox" checked={clearAvailability} onChange={event => {
                    setClearAvailability(event.target.checked); setMessage('')
                    setErrors(previous => ({ ...previous, disponible_desde: undefined, disponible_hasta: undefined }))
                  }} />
                  <span>Sin disponibilidad (retirar la franja actual)</span>
                </label> : null}
                <p className="field-hint">Las fechas y horas de disponibilidad corresponden a Lima (UTC−05:00).
                  Una licencia vencida puede guardarse, pero no habilita la asignación.</p>
              </> : null}
            </FormSection>
          ))}
        </fieldset>
        <FormActions>
          <Button type="submit" icon={Save} disabled={saving}>
            {saving ? 'Guardando…' : driver ? 'Guardar cambios' : 'Registrar conductor'}
          </Button>
          <Button variant="secondary" icon={X} disabled={saving} onClick={onCancel}>Cancelar</Button>
        </FormActions>
        {saving ? <p className="field-hint" role="status">Guardando conductor…</p> : null}
      </form>
    </section>
  )
}
