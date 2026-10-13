import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { DeliveryPreferencesForm } from '../components/DeliveryPreferencesForm'
import { ClientCombobox } from '../components/ClientCombobox'
import { Search, Users } from 'lucide-react'
import { Alert, Button, PageHeader } from '../components/ui'
import { getDeliveryPreferences, isClientId, PreferencesServiceError } from '../services/deliveryPreferences'
import type { ClientOption } from '../services/clients'
import type { DeliveryPreferences } from '../services/deliveryPreferences'

export function DeliveryPreferencesPage({ onSessionExpired }: { onSessionExpired: () => void }) {
  const [client, setClient] = useState<ClientOption | null>(null)
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
    const id = client?.cliente_id ?? ''
    if (!isClientId(id)) {
      setIdError('Selecciona un cliente de la lista.')
      setMessage('Selecciona un cliente antes de consultar.')
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
    <PageHeader titleId="preferences-title" title="Preferencias de entrega" eyebrow="Gestión operativa"
      breadcrumbs={[{ label: 'Inicio', to: '/' }, { label: 'Preferencias de entrega' }]}
      description="Consulta y actualiza horarios, referencias y condiciones de acceso de un cliente existente." />
    <form className="card preferences-lookup" aria-label="Consultar cliente" aria-busy={loading}
      noValidate onSubmit={event => { void load(event) }}>
      <ClientCombobox id="preferences-client-id" label="Cliente" error={idError}
        hint="Escribe parte del nombre o pega el identificador del cliente."
        selected={client} disabled={loading || blocked || preferences !== null}
        onSelect={option => { setClient(option); setIdError(''); setMessage(''); setSuccess('') }} />
      <div className="lookup-actions">
        <Button type="submit" icon={Search} disabled={loading || blocked || preferences !== null}>
          {loading ? 'Consultando…' : 'Consultar preferencias'}</Button>
      </div>
    </form>
    {loading ? <p className="field-hint" role="status">Cargando preferencias…</p> : null}
    {message ? <Alert tone="danger" ref={alert} tabIndex={-1}>{message}</Alert> : null}
    {success ? <Alert tone="success" role="status">{success}</Alert> : null}
    {preferences ? <>
      <DeliveryPreferencesForm key={`${preferences.cliente_id}-${revision}`} preferences={preferences}
        clientName={client?.cliente_id === preferences.cliente_id ? client.nombre : undefined}
        onAccessError={accessError} onEdit={() => setSuccess('')} onSavingChange={value => { setSaving(value); if (value) setSuccess('') }} onSaved={saved => {
          setPreferences(saved); setRevision(value => value + 1)
          setSaving(false)
          setSuccess('Preferencias guardadas correctamente.'); setMessage('')
        }} onCancel={() => { setRevision(value => value + 1); setSuccess('Cambios descartados. Se muestran las preferencias consultadas.') }} />
      <Button variant="ghost" icon={Users} className="preferences-change-client" disabled={saving} onClick={() => {
        setPreferences(null); setSuccess(''); setMessage('')
        // Input becomes enabled after React commits the state change.
        queueMicrotask(() => document.getElementById('preferences-client-id')?.focus())
      }}>Consultar de nuevo u otro cliente</Button>
    </> : null}
  </section>
}
