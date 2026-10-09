import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { changedDriverFields, EMPTY_DRIVER, validateDriver, valuesFromDriver } from '../domain/driverForm'
import type { DriverErrors, DriverValues } from '../domain/driverForm'
import { createDriver, DriverServiceError, updateDriver } from '../services/drivers'
import type { DriverDetail, DriverField, DriverSummary } from '../services/drivers'

const FIELDS: { name: DriverField; label: string; type: string; max?: number }[] = [
  { name: 'nombre', label: 'Nombre completo', type: 'text', max: 160 },
  { name: 'dni', label: 'DNI', type: 'text', max: 8 },
  { name: 'licencia_numero', label: 'Número de licencia', type: 'text', max: 20 },
  { name: 'licencia_vigente_hasta', label: 'Licencia vigente hasta', type: 'date' },
  { name: 'experiencia_anios', label: 'Experiencia (años)', type: 'number' },
  { name: 'telefono', label: 'Teléfono', type: 'tel', max: 16 },
  { name: 'punto_partida', label: 'Punto de partida', type: 'text', max: 255 },
  { name: 'disponible_desde', label: 'Disponible desde (hora de Lima)', type: 'datetime-local' },
  { name: 'disponible_hasta', label: 'Disponible hasta (hora de Lima)', type: 'datetime-local' },
  { name: 'email', label: 'Correo del conductor', type: 'email', max: 255 },
  { name: 'password', label: 'Contraseña inicial', type: 'password', max: 1024 },
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
  return (
    <section className="driver-editor" aria-labelledby="driver-form-title">
      <h2 id="driver-form-title" tabIndex={-1} ref={title}>
        {driver ? 'Perfil de ' + driver.nombre : 'Registrar conductor'}
      </h2>
      <p className="form-intro">{driver
        ? 'Consulta y actualiza el perfil. La cuenta y sus credenciales no se modifican aquí.'
        : 'Registra el perfil y una cuenta independiente con rol Conductor. Todos los campos son obligatorios.'}</p>
      {driver ? <p className={'driver-assignment ' + (driver.habilitado_asignacion ? '' : 'driver-warning')}>
        {driver.habilitado_asignacion ? 'Habilitado para asignación' : 'No habilitado para asignación: revisa vigencia, disponibilidad y estado de la cuenta.'}
      </p> : null}
      <form className="driver-form" onSubmit={event => { void submit(event) }} noValidate aria-label={driver ? "Editar conductor" : "Registrar conductor"} aria-busy={saving}>
        {message ? <div className="form-alert error-alert" role="alert" tabIndex={-1} ref={alert}>{message}</div> : null}
        <fieldset disabled={saving}>
          <legend>Datos del conductor</legend>
          <div className="form-grid">
            {FIELDS.filter(field => !driver || (field.name !== 'email' && field.name !== 'password')).map(field => {
              const availability = field.name === 'disponible_desde' || field.name === 'disponible_hasta'
              const error = errors[field.name]
              return <div className="form-field" key={field.name}>
                <label htmlFor={'driver-' + field.name}>{field.label}</label>
                <input id={'driver-' + field.name} name={field.name} type={field.type}
                  value={values[field.name]} onChange={event => { change(field.name, event.target.value) }}
                  maxLength={field.max} min={field.name === 'experiencia_anios' ? 0 : undefined}
                  step={availability ? '0.001' : field.name === 'experiencia_anios' ? '1' : undefined}
                  inputMode={field.name === 'dni' ? 'numeric' : undefined}
                  autoComplete={field.name === 'password' ? 'new-password' : 'off'}
                  disabled={availability && clearAvailability} required={!clearAvailability || !availability}
                  aria-invalid={Boolean(error)} aria-describedby={error ? 'driver-error-' + field.name : undefined} />
                {error ? <p className="field-error" id={'driver-error-' + field.name}>{error}</p> : null}
              </div>
            })}
          </div>
          {driver ? <label className="driver-checkbox">
            <input type="checkbox" checked={clearAvailability} onChange={event => {
              setClearAvailability(event.target.checked); setMessage('')
              setErrors(previous => ({ ...previous, disponible_desde: undefined, disponible_hasta: undefined }))
            }} />
            Sin disponibilidad (retirar la franja actual)
          </label> : null}
          <p className="driver-help">Las fechas y horas de disponibilidad corresponden a Lima (UTC−05:00).
            Una licencia vencida puede guardarse, pero no habilita la asignación.</p>
          {!driver ? <p className="driver-help">La contraseña se envía únicamente al registrar. No se muestra en el listado ni se guarda en el navegador.</p> : null}
        </fieldset>
        <div className="driver-actions">
          <button className="submit-button" disabled={saving} type="submit">
            {saving ? 'Guardando…' : driver ? 'Guardar cambios' : 'Registrar conductor'}
          </button>
          <button className="drivers-secondary" disabled={saving} type="button" onClick={onCancel}>Cancelar</button>
        </div>
        {saving ? <p role="status">Guardando conductor…</p> : null}
      </form>
    </section>
  )
}
