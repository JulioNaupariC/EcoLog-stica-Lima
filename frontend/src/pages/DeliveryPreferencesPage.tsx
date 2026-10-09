import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { DeliveryPreferencesForm } from '../components/DeliveryPreferencesForm'
import { FormField } from '../components/FormField'
import { getDeliveryPreferences, isClientId, PreferencesServiceError } from '../services/deliveryPreferences'
import type { DeliveryPreferences } from '../services/deliveryPreferences'
import './DeliveryPreferencesPage.css'

export function DeliveryPreferencesPage({ onSessionExpired }: { onSessionExpired: () => void }) {
  const [clientId, setClientId] = useState('')
  const [idError, setIdError] = useState('')
  const [message, setMessage] = useState('')
  const [success, setSuccess] = useState('')
  const [preferences, setPreferences] = useState<DeliveryPreferences | null>(null)
  const [loading, setLoading] = useState(false)
  const [blocked, setBlocked] = useState(false)
  const [saving, setSaving] = useState(false)
  const [revision, setRevision] = useState(0)
  const requestNumber = useRef(0)
  const busy = useRef(false)
  const alert = useRef<HTMLDivElement>(null)
  const search = useRef<HTMLInputElement>(null)
  useEffect(() => {
    const requests = requestNumber
    return () => { requests.current++ }
  }, [])
  useEffect(() => { if (message) alert.current?.focus() }, [message])

  function accessError(error: PreferencesServiceError) {
    if (error.kind === 'unauthorized' || error.kind === 'not_found') {
      setPreferences(null)
      setMessage(error.message)
      setSaving(false)
      if (error.kind === 'unauthorized') { setBlocked(true); onSessionExpired() }
    }
    if (error.kind === 'forbidden') {
      setBlocked(true)
      setSaving(false)
      setPreferences(null)
      setMessage(error.message)
    }
  }
  async function load(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy.current || blocked) return
    setSuccess('')
    setMessage('')
    setPreferences(null)
    const id = clientId.trim()
    if (!isClientId(id)) {
      setIdError('Ingresa un identificador de cliente válido (UUID).')
      setMessage('Revisa el identificador del cliente antes de consultar.')
      return
    }
    setIdError('')
    busy.current = true
    setLoading(true)
    const number = ++requestNumber.current
    try {
      const saved = await getDeliveryPreferences(id)
      if (number === requestNumber.current) setPreferences(saved)
    } catch (error) {
      if (number !== requestNumber.current) return
      if (error instanceof PreferencesServiceError) accessError(error)
      setMessage(error instanceof PreferencesServiceError ? error.message : 'No se pudieron consultar las preferencias. Intenta nuevamente.')
    } finally {
      busy.current = false
      if (number === requestNumber.current) setLoading(false)
    }
  }
  return <section className="preferences-page" aria-labelledby="preferences-title">
    <p className="eyebrow">Gestión operativa</p>
    <h1 id="preferences-title">Preferencias de entrega</h1>
    <p className="form-intro">Consulta y actualiza horarios, referencias y condiciones de acceso de un cliente existente.</p>
    <form className="order-form preferences-lookup" aria-label="Consultar cliente" aria-busy={loading}
      noValidate onSubmit={event => { void load(event) }}>
      <FormField id="preferences-client-id" label="ID del cliente" error={idError}
        hint="Usa el identificador del cliente que deseas consultar.">
        <input id="preferences-client-id" ref={search} type="text" autoComplete="off" spellCheck={false} value={clientId}
          disabled={loading || blocked || preferences !== null} aria-invalid={Boolean(idError)}
          aria-describedby={`preferences-client-id-hint${idError ? ' preferences-client-id-error' : ''}`}
          onChange={event => { setClientId(event.target.value); setIdError(''); setMessage(''); setSuccess('') }} />
      </FormField>
      <button type="submit" className="submit-button" disabled={loading || blocked || preferences !== null}>
        {loading ? 'Consultando…' : 'Consultar preferencias'}</button>
    </form>
    {loading ? <p role="status">Cargando preferencias…</p> : null}
    {message ? <div className="form-alert error-alert" role="alert" ref={alert} tabIndex={-1}>{message}</div> : null}
    {success ? <p className="form-alert success-alert" role="status">{success}</p> : null}
    {preferences ? <>
      <DeliveryPreferencesForm key={`${preferences.cliente_id}-${revision}`} preferences={preferences}
        onAccessError={accessError} onEdit={() => setSuccess('')} onSavingChange={value => { setSaving(value); if (value) setSuccess('') }} onSaved={saved => {
          setPreferences(saved); setRevision(value => value + 1)
          setSaving(false)
          setSuccess('Preferencias guardadas correctamente.'); setMessage('')
        }} onCancel={() => { setRevision(value => value + 1); setSuccess('Cambios descartados. Se muestran las preferencias consultadas.') }} />
      <button type="button" className="preferences-secondary preferences-change-client" disabled={saving} onClick={() => {
        setPreferences(null); setSuccess(''); setMessage(''); search.current?.focus()
        // Input becomes enabled after React commits the state change.
        queueMicrotask(() => search.current?.focus())
      }}>Consultar de nuevo u otro cliente</button>
    </> : null}
  </section>
}
