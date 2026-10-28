import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, CircleAlert, Info, MapPin } from 'lucide-react'
import { Alert, Button, FormActions, FormSection, LinkButton, PageHeader } from '../components/ui'
import { FormField } from '../components/FormField'
import { useOnlineStatus } from '../hooks/useOnlineStatus'
import { INCIDENT_SEVERITIES, INCIDENT_TYPES, newIncidentDraft, validateIncident, validLocation } from '../domain/incident'
import type { IncidentDraft, IncidentErrors, IncidentPayload, StoredIncident } from '../domain/incident'
import { correctRejectedIncident, enqueueIncident, listIncidents, loadIncidentDraft, saveIncidentDraft } from '../services/incidentStorage'
import { INCIDENTS_CHANGED, isSynchronizingIncidents, notifyIncidentsChanged, synchronizeIncidents } from '../services/incidentSync'
import { IncidentServiceError } from '../services/incidents'
import { loadItinerary } from '../services/offlineStorage'
import type { StopSummary } from '../services/offlineStorage'

const SEVERITY_ICONS = { BAJA: Info, MEDIA: CircleAlert, ALTA: AlertTriangle }

export function IncidentCreatePage({ ownerId }: { ownerId: string }) {
  const [draft, setDraft] = useState<IncidentDraft>(newIncidentDraft)
  const [loaded, setLoaded] = useState(false)
  const [errors, setErrors] = useState<IncidentErrors>({})
  const [storageMessage, setStorageMessage] = useState('')
  const [locationMessage, setLocationMessage] = useState('')
  const [locating, setLocating] = useState(false)
  const [busy, setBusy] = useState(false)
  const [sending, setSending] = useState(false)
  const [reports, setReports] = useState<StoredIncident[]>([])
  const [stops, setStops] = useState<StopSummary[]>([])
  const online = useOnlineStatus()
  const form = useRef<HTMLFormElement>(null)
  const saving = useRef(Promise.resolve())
  const submitting = useRef(false)
  const alive = useRef(true)
  const syncController = useRef(new AbortController())

  useEffect(() => {
    alive.current = true
    syncController.current = new AbortController()
    let active = true
    async function refresh() {
      if (active) setSending(isSynchronizingIncidents(ownerId))
      try {
        const items = await listIncidents(ownerId)
        if (active) setReports(items)
      } catch {
        if (active) setStorageMessage('No se pudo leer la cola local. No hay confirmación de guardado.')
      }
    }
    void loadIncidentDraft(ownerId).then(saved => {
      if (active) { if (saved) setDraft(saved); setLoaded(true) }
    }).catch(() => {
      if (active) {
        setStorageMessage('No se pudo recuperar el borrador local. Comprueba el almacenamiento del navegador.')
        setLoaded(true)
      }
    })
    void loadItinerary(ownerId).then(snapshot => {
      if (active) setStops(snapshot?.stops.filter(stop => stop.status === 'PENDIENTE' || stop.status === 'EN_RUTA') ?? [])
    }).catch(() => { /* GPS still available when no itinerary is cached. */ })
    const refreshListener = () => { void refresh() }
    void refresh()
    window.addEventListener(INCIDENTS_CHANGED, refreshListener)
    return () => {
      active = false; alive.current = false; syncController.current.abort()
      window.removeEventListener(INCIDENTS_CHANGED, refreshListener)
    }
  }, [ownerId])

  function change(next: IncidentDraft) {
    setDraft(next)
    const validation = validateIncident(next)
    setErrors(current => Object.fromEntries(Object.keys(current).map(field =>
      [field, validation[field as keyof IncidentDraft]])))
    // Serialize writes so an older draft cannot replace a newer one.
    saving.current = saving.current.catch(() => {}).then(() => saveIncidentDraft(ownerId, next))
      .then(() => { if (alive.current) setStorageMessage('Borrador guardado en este dispositivo.') })
      .catch(() => { if (alive.current) setStorageMessage('No se pudo guardar el borrador. Mantén esta pantalla abierta y reintenta.') })
  }
  function validateField(field: keyof IncidentDraft) {
    setErrors(current => ({ ...current, [field]: validateIncident(draft)[field] }))
  }
  function locate() {
    if (!navigator.geolocation) {
      setLocationMessage('Este navegador no ofrece ubicación. Selecciona una parada con coordenadas.'); return
    }
    setLocating(true)
    navigator.geolocation.getCurrentPosition(position => {
      if (!alive.current) return
      setLocating(false)
      const ubicacion = { latitud: position.coords.latitude, longitud: position.coords.longitude }
      if (!validLocation(ubicacion)) { setLocationMessage('No se recibió una ubicación válida. Usa una parada.'); return }
      // Functional update avoids overwriting edits made while GPS was pending.
      setDraft(current => {
        const next = { ...current, ubicacion }
        saving.current = saving.current.catch(() => {}).then(() => saveIncidentDraft(ownerId, next))
          .catch(() => { if (alive.current) setStorageMessage('No se pudo guardar la ubicación localmente.') })
        return next
      })
      setErrors(current => ({ ...current, ubicacion: undefined }))
      setLocationMessage('Ubicación del dispositivo seleccionada.')
    }, () => {
      if (!alive.current) return
      setLocating(false)
      setLocationMessage('No se pudo acceder a tu ubicación. Puedes continuar con una parada que tenga coordenadas.')
    }, { timeout: 10_000, maximumAge: 60_000, enableHighAccuracy: false })
  }
  async function submit(event: React.SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submitting.current) return
    const found = validateIncident(draft)
    setErrors(found)
    if (Object.keys(found).length) {
      change(draft)
      const field = Object.keys(found)[0]
      form.current?.querySelector<HTMLElement>(`[data-field="${field}"]`)?.focus()
      return
    }
    submitting.current = true; setBusy(true)
    try {
      await saving.current
      const payload: IncidentPayload = {
        ...draft.ubicacion!, operation_id: draft.operation_id ?? crypto.randomUUID(),
        tipo: draft.tipo as IncidentPayload['tipo'], severidad: draft.severidad as IncidentPayload['severidad'],
        ocurrida_en: draft.ocurrida_en, observacion: draft.observacion,
      }
      if (draft.operation_id) {
        await correctRejectedIncident(ownerId, payload)
      } else await enqueueIncident({ ownerId, payload, createdAt: Date.now() })
      if (!alive.current) return
      setDraft(newIncidentDraft())
      setStorageMessage('Pendiente de envío · guardada en este dispositivo.')
      notifyIncidentsChanged()
    } catch {
      if (alive.current) setStorageMessage('No se pudo guardar la incidencia. Conservamos los campos en pantalla; vuelve a intentar.')
    } finally { submitting.current = false; if (alive.current) setBusy(false) }
  }
  async function retry() {
    setBusy(true)
    try { await synchronizeIncidents(ownerId, syncController.current.signal, true) }
    catch { setStorageMessage('No se pudo sincronizar. Los reportes conservan su identificador.') }
    finally { setBusy(false) }
  }
  const described = (field: keyof IncidentDraft) => errors[field] ? `${field}-error` : undefined
  return <section className="driver-page incident-page" aria-labelledby="incident-title">
    <PageHeader titleId="incident-title" title="Reportar incidencia"
      description="Describe lo ocurrido. El reporte quedará pendiente de validación por Operación." />
    <LinkButton to="/conductor/itinerario" variant="ghost">Volver al itinerario</LinkButton>
    <Alert tone={online ? 'info' : 'warning'} role="status">
      {online ? 'Con conexión. Confirmaremos el registro cuando responda el servidor.' : 'Sin conexión. Guardaremos el reporte y lo enviaremos al reconectar.'}
    </Alert>
    {sending ? <p role="status">Enviando incidencias… Esperando confirmación del servidor.</p> : null}
    {storageMessage ? <p role="status" className="field-hint">{storageMessage}</p> : null}
    <form ref={form} noValidate onSubmit={event => { void submit(event) }}>
      <fieldset disabled={!loaded || busy || locating} className="incident-fields">
        <FormField id="tipo" label="Tipo" error={errors.tipo}>
          <select id="tipo" data-field="tipo" value={draft.tipo} aria-required="true" aria-invalid={Boolean(errors.tipo)}
            aria-describedby={described('tipo')} onBlur={() => validateField('tipo')}
            onChange={event => change({ ...draft, tipo: event.target.value as IncidentDraft['tipo'] })}>
            <option value="">Selecciona un tipo</option>
            {Object.entries(INCIDENT_TYPES).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </FormField>
        <FormSection legend="Severidad">
          <div role="radiogroup" aria-label="Severidad" aria-required="true" aria-invalid={Boolean(errors.severidad)}
            aria-describedby={described('severidad')} onBlur={() => validateField('severidad')}>
            {Object.entries(INCIDENT_SEVERITIES).map(([value, label], index) => {
              const Icon = SEVERITY_ICONS[value as keyof typeof SEVERITY_ICONS]
              return <label className="incident-choice" key={value}>
                <input type="radio" name="severidad" value={value} data-field={index === 0 ? 'severidad' : undefined}
                  checked={draft.severidad === value} onChange={() => change({ ...draft, severidad: value as IncidentDraft['severidad'] })} />
                <Icon size={20} aria-hidden="true" /><span>{label}</span>
              </label>
            })}
          </div>
          {errors.severidad ? <p id="severidad-error" className="field-error">{errors.severidad}</p> : null}
        </FormSection>
        <FormSection legend="Ubicación" description="Usa la posición del dispositivo o una parada del itinerario guardado.">
          <Button icon={MapPin} data-field="ubicacion" aria-describedby={described('ubicacion')}
            onClick={locate} variant="secondary">{locating ? 'Obteniendo ubicación…' : 'Usar mi ubicación'}</Button>
          <div className="form-field"><label htmlFor="parada">Parada actual</label>
          <select id="parada" value={draft.ubicacion?.parada_id ?? ''} onBlur={() => validateField('ubicacion')}
            onChange={event => {
              const stop = stops.find(item => item.stopId === event.target.value)
              if (stop?.location) change({ ...draft, ubicacion: { ...stop.location, parada_id: stop.stopId } })
            }}>
            <option value="">Selecciona una parada</option>
            {stops.map(stop => <option key={stop.stopId} value={stop.stopId} disabled={!stop.location}>
              Parada {stop.position}{stop.location ? '' : ' · Sin coordenadas disponibles'}
            </option>)}
          </select></div>
          {!stops.some(stop => stop.location) ? <p className="field-hint">No hay paradas con coordenadas disponibles en el itinerario guardado.</p> : null}
          {draft.ubicacion ? <p>Ubicación seleccionada: {draft.ubicacion.latitud.toFixed(5)}, {draft.ubicacion.longitud.toFixed(5)}</p> : null}
          {locationMessage ? <p role="status">{locationMessage}</p> : null}
          {errors.ubicacion ? <p id="ubicacion-error" className="field-error">{errors.ubicacion}</p> : null}
        </FormSection>
        <FormField id="ocurrida_en" label="Hora (automática)" error={errors.ocurrida_en}>
          <input id="ocurrida_en" data-field="ocurrida_en" readOnly value={new Date(draft.ocurrida_en).toLocaleString('es-PE')}
            aria-describedby={described('ocurrida_en')} />
        </FormField>
        <FormField id="observacion" label="Observación (opcional)" error={errors.observacion} hint="Evita incluir nombres, teléfonos u otros datos personales.">
          <textarea id="observacion" data-field="observacion" rows={4} value={draft.observacion}
            aria-invalid={Boolean(errors.observacion)} aria-describedby={`observacion-hint observacion-count ${described('observacion') ?? ''}`}
            onBlur={() => validateField('observacion')} onChange={event => change({ ...draft, observacion: event.target.value })} />
          <p id="observacion-count" className="field-hint">{[...draft.observacion].length}/500 caracteres</p>
        </FormField>
        <FormActions><Button type="submit">{busy ? 'Guardando…' : 'Enviar incidencia'}</Button></FormActions>
      </fieldset>
    </form>
    {reports.length ? <section aria-label="Mis envíos de incidencias" className="incident-reports">
      <h2>Mis envíos</h2>
      {reports.map(report => <article className="stop-card" key={report.payload.operation_id}>
        <h3>{INCIDENT_TYPES[report.payload.tipo]} · {report.payload.severidad}</h3>
        {report.acknowledgement ? <p role="status">Incidencia registrada · pendiente de validación<br />ID: {report.acknowledgement.incidencia_id}</p>
          : report.errorStatus ? <p role="alert">{new IncidentServiceError(report.errorStatus).message}</p>
          : <p role="status">Pendiente de envío · se sincronizará al reconectar.</p>}
        {report.errorStatus === 422 ? <Button variant="secondary" disabled={busy} onClick={() => {
          const { latitud, longitud, parada_id, ...fields } = report.payload
          change({ ...fields, ubicacion: { latitud, longitud, ...(parada_id ? { parada_id } : {}) } })
          form.current?.querySelector<HTMLElement>('[data-field="tipo"]')?.focus()
        }}>Corregir datos conservando el identificador</Button> : null}
      </article>)}
      {reports.some(report => !report.acknowledgement && report.errorStatus !== 401 && report.errorStatus !== 409) ? <Button disabled={busy || !online} onClick={() => { void retry() }} variant="secondary">
        {busy ? 'Enviando…' : 'Reintentar envíos pendientes'}</Button> : null}
    </section> : null}
  </section>
}
