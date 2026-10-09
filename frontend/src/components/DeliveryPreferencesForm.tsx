import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { FormField } from './FormField'
import { PREFERENCE_LIMITS, preferencesPatch, valuesFromPreferences } from '../domain/deliveryPreferencesForm'
import type { PreferencesErrors } from '../domain/deliveryPreferencesForm'
import { PreferencesServiceError, updateDeliveryPreferences } from '../services/deliveryPreferences'
import type { DeliveryPreferences, PreferenceField } from '../services/deliveryPreferences'

const FIELDS: { name: PreferenceField; label: string; clearLabel: string; hint: string }[] = [
  { name: 'horario_preferido', label: 'Horario preferido', clearLabel: 'Sin horario preferido',
    hint: 'Describe el horario, por ejemplo: lunes a viernes por la mañana. No modifica la ventana de un pedido.' },
  { name: 'referencia', label: 'Referencia de ubicación', clearLabel: 'Sin referencia de ubicación',
    hint: 'Incluye una referencia que facilite encontrar el lugar de entrega.' },
  { name: 'restriccion_acceso', label: 'Restricciones de acceso', clearLabel: 'Sin restricciones de acceso definidas',
    hint: 'Indica condiciones de ingreso, por ejemplo: avisar a recepción al llegar.' },
]
interface Props {
  preferences: DeliveryPreferences
  onSaved: (preferences: DeliveryPreferences) => void
  onCancel: () => void
  onAccessError: (error: PreferencesServiceError) => void
  onSavingChange: (saving: boolean) => void
  onEdit: () => void
}
export function DeliveryPreferencesForm({ preferences, onSaved, onCancel, onAccessError, onSavingChange, onEdit }: Props) {
  const [values, setValues] = useState(() => valuesFromPreferences(preferences))
  const [errors, setErrors] = useState<PreferencesErrors>({})
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)
  const [blocked, setBlocked] = useState(false)
  const inFlight = useRef(false)
  const active = useRef(false)
  const heading = useRef<HTMLHeadingElement>(null)
  const alert = useRef<HTMLDivElement>(null)
  useEffect(() => {
    active.current = true
    heading.current?.focus()
    return () => { active.current = false }
  }, [])
  useEffect(() => { if (message) alert.current?.focus() }, [message])

  function change(field: PreferenceField, value?: string, cleared?: boolean) {
    onEdit()
    setValues(previous => ({ ...previous, [field]: { ...previous[field],
      ...(value !== undefined ? { value } : {}), ...(cleared !== undefined ? { cleared } : {}) } }))
    setErrors(previous => ({ ...previous, [field]: undefined }))
    setMessage('')
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (inFlight.current || blocked) return
    const result = preferencesPatch(preferences, values)
    setErrors(result.errors)
    if (Object.keys(result.errors).length) { setMessage('Revisa los campos indicados antes de guardar.'); return }
    if (!Object.keys(result.patch).length) { setMessage('No hay cambios para guardar.'); return }
    inFlight.current = true
    setSaving(true)
    onSavingChange(true)
    setMessage('')
    try {
      const saved = await updateDeliveryPreferences(preferences.cliente_id, result.patch)
      if (active.current) onSaved(saved)
    } catch (error) {
      if (!active.current) return
      if (error instanceof PreferencesServiceError) {
        if (error.kind === 'forbidden' || error.kind === 'unauthorized' || error.kind === 'not_found') setBlocked(true)
        onAccessError(error)
        setErrors(Object.fromEntries(error.fields.map(field => [field, 'Revisa este campo.'])))
        setMessage(error.kind === 'network'
          ? 'No se pudo confirmar el guardado. Conservamos tus cambios en pantalla; consulta de nuevo para comprobar el resultado.'
          : error.message)
      } else setMessage('No se pudieron guardar las preferencias. Intenta nuevamente.')
    } finally {
      inFlight.current = false
      if (active.current) { setSaving(false); onSavingChange(false) }
    }
  }
  return <section aria-labelledby="preferences-form-title">
    <h2 id="preferences-form-title" ref={heading} tabIndex={-1}>Preferencias del cliente</h2>
    <p className="preferences-client">Cliente: {preferences.cliente_id}</p>
    <form className="order-form preferences-form" aria-label="Editar preferencias de entrega" aria-busy={saving}
      noValidate onSubmit={event => { void submit(event) }}>
      {message ? <div className="form-alert error-alert" role="alert" tabIndex={-1} ref={alert}>{message}</div> : null}
      <fieldset disabled={saving || blocked}>
        <legend>Condiciones de entrega</legend>
        {FIELDS.map(field => {
          const id = 'preference-' + field.name
          const input = values[field.name]
          return <div className="preference-entry" key={field.name}>
            <FormField id={id} label={field.label} hint={field.hint} error={errors[field.name]}>
              <textarea id={id} name={field.name} rows={field.name === 'horario_preferido' ? 2 : 3}
                value={input.value} disabled={input.cleared} onChange={event => change(field.name, event.target.value)}
                aria-invalid={Boolean(errors[field.name])}
                aria-describedby={`${id}-hint ${id}-count${errors[field.name] ? ` ${id}-error` : ''}`} />
              <p className="field-hint" id={`${id}-count`}>{Array.from(input.value).length} / {PREFERENCE_LIMITS[field.name]} caracteres</p>
            </FormField>
            <label className="preference-clear"><input type="checkbox" checked={input.cleared}
              onChange={event => change(field.name, undefined, event.target.checked)} />{field.clearLabel}</label>
          </div>
        })}
      </fieldset>
      <p className="field-hint">Marcar una opción “Sin…” elimina esa preferencia al guardar. Las demás se conservan.</p>
      <div className="preferences-actions">
        <button type="submit" className="submit-button" disabled={saving || blocked}>{saving ? 'Guardando…' : 'Guardar preferencias'}</button>
        <button type="button" className="preferences-secondary" disabled={saving} onClick={onCancel}>Cancelar cambios</button>
      </div>
    </form>
  </section>
}
