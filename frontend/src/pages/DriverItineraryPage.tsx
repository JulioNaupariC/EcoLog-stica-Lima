import { useCallback, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { DEMO_ITINERARY, isDemoItineraryEnabled } from '../data/demoDriverItinerary'
import { DELIVERY_LABEL, formatWindow, getNextStop, getStopAlerts } from '../domain/driverItinerary'
import type { DeliveryState, DemoItinerary, DriverAlert, DriverStop } from '../domain/driverItinerary'
import { OfflineReportPanel } from '../components/OfflineReportPanel'
import { clearItinerary, loadItinerary, saveItinerary } from '../services/offlineStorage'
import type { StopSummary } from '../services/offlineStorage'
import type { PendingDriverReport } from '../types/driverReport'
import {
  DriverItineraryServiceError,
  driverReportTransport,
  getDriverItinerary,
} from '../services/driverItinerary'
import { CalendarClock, CheckCircle2, CloudOff, MapPin, MapPinned, Navigation, RefreshCw } from 'lucide-react'
import { Alert, Button, EmptyState, PageHeader, Skeleton, StatusBadge } from '../components/ui'
import { useReportSynchronization } from '../hooks/useReportSynchronization'

function OperationalAlerts({ alerts }: { alerts: readonly DriverAlert[] }) {
  return <section className="driver-alerts" aria-label="Alertas operativas de demostración">
    {alerts.length === 0 ? <p>No hay alertas operativas en este ejemplo.</p> : alerts.map((alert) => (
      <div className="driver-alert" key={alert.id}>
        <p className="driver-alert-title">{alert.title}</p><strong>{alert.description}</strong>
        <p>{alert.instruction}</p><small>Alerta de demostración · Sin información de tráfico real</small>
      </div>
    ))}
  </section>
}

function ItineraryLayout({ children, description }: { children: ReactNode, description?: ReactNode }) {
  return <section className="driver-page" aria-labelledby="driver-title">
    <PageHeader titleId="driver-title" title="Mi itinerario" description={description} />
    {children}
  </section>
}

function StopDetails({ stop }: { stop: StopSummary }) {
  return <>
    <div className="stop-head">
      <span className="stop-position" aria-hidden="true">{stop.position}</span>
      <h3 className="stop-title">Parada {stop.position}</h3>
      <StatusBadge status={stop.status} />
    </div>
    {stop.delivery ? <dl className="stop-details">
      <div className="stop-detail stop-detail--address">
        <dt><MapPin aria-hidden="true" size={16} /> Dirección de entrega</dt>
        <dd>{stop.delivery.address}</dd>
      </div>
      {stop.delivery.reference ? <div className="stop-detail">
        <dt><MapPinned aria-hidden="true" size={16} /> Referencia</dt>
        <dd>{stop.delivery.reference}</dd>
      </div> : null}
      <div className="stop-detail">
        <dt><CalendarClock aria-hidden="true" size={16} /> Horario de entrega</dt>
        <dd>{formatWindow(stop.delivery.windowStart, stop.delivery.windowEnd)}</dd>
      </div>
    </dl> : <p className="stop-missing">La asignación todavía no contiene dirección ni horario. Solicita al coordinador una asignación vinculada a su pedido.</p>}
    <p className="stop-id">Ref. de parada {stop.stopId.slice(0, 8)}</p>
  </>
}

function StopCard({ stop, next = false }: { stop: DriverStop; next?: boolean }) {
  return <span className={`driver-card driver-card-${stop.state.toLowerCase()}${next ? ' driver-card-next' : ''}`}>
    <span className="driver-card-state">{next ? 'Siguiente' : DELIVERY_LABEL[stop.state]} · {String(stop.sequence).padStart(2, '0')}</span>
    <strong>{stop.client}</strong><span>{stop.address}</span><small>{stop.window} · {stop.load}</small>
  </span>
}

export function DriverItineraryPage({
  itinerary = DEMO_ITINERARY,
  ownerId,
  onSessionExpired,
}: {
  itinerary?: DemoItinerary | null
  ownerId?: string
  onSessionExpired?: () => void
}) {
  const [reloadKey, setReloadKey] = useState(0)
  const [selected, setSelected] = useState<DriverStop | null>(null)
  const [filter, setFilter] = useState<'TODAS' | DeliveryState>('TODAS')
  const [showEmpty, setShowEmpty] = useState(false)
  const [assignedStops, setAssignedStops] = useState<StopSummary[] | null>(null)
  const [loadingAssignedStops, setLoadingAssignedStops] = useState(Boolean(ownerId))
  const [assignedStopsError, setAssignedStopsError] = useState('')
  const [usingCachedItinerary, setUsingCachedItinerary] = useState(false)
  const handleConfirmed = useCallback((report: PendingDriverReport) => {
    if (report.ownerId !== ownerId) return
    setAssignedStops(stops => stops?.map(stop => stop.stopId === report.stopId
      ? { ...stop, status: report.status }
      : stop) ?? null)
  }, [ownerId])
  const heading = useRef<HTMLHeadingElement>(null)
  const verifyForSynchronization = useCallback(async () => {
    if (!ownerId) return false
    try {
      const stops = await getDriverItinerary(ownerId)
      if (stops.length) {
        const savedAt = Date.now()
        await saveItinerary({ ownerId, savedAt, expiresAt: savedAt + 24 * 60 * 60 * 1000, stops })
      } else await clearItinerary(ownerId)
      setAssignedStops(stops)
      setUsingCachedItinerary(false)
      return true
    } catch (error) {
      if (error instanceof DriverItineraryServiceError && (error.status === 401 || error.status === 403)) {
        onSessionExpired?.()
        return false
      }
      throw error
    }
  }, [ownerId, onSessionExpired])
  const syncMessage = useReportSynchronization(ownerId, Boolean(assignedStops), verifyForSynchronization, handleConfirmed)
  const current = showEmpty ? null : itinerary
  const next = getNextStop(current?.stops ?? [])
  const visible = (current?.stops ?? []).filter((stop) => filter === 'TODAS' || stop.state === filter)
  const detail = current !== null && selected !== null
  useEffect(() => { heading.current?.focus() }, [selected, showEmpty])
  useEffect(() => {
    if (!ownerId) return
    let active = true
    void (async () => {
      try {
        const stops = await getDriverItinerary(ownerId)
        if (!active) return
        try {
          if (stops.length === 0) {
            await clearItinerary(ownerId)
          } else {
            const savedAt = Date.now()
            await saveItinerary({
              ownerId,
              savedAt,
              expiresAt: savedAt + 24 * 60 * 60 * 1000,
              stops,
            })
          }
        } catch {
          if (active) setAssignedStopsError('No se pudo actualizar el itinerario guardado en este dispositivo.')
        }
        if (active) setAssignedStops(stops)
      } catch (error) {
        if (!active) return
        if (error instanceof DriverItineraryServiceError && (error.status === 401 || error.status === 403)) {
          onSessionExpired?.()
          return
        }
        const retryable = error instanceof DriverItineraryServiceError && error.retryable
        if (retryable) {
          try {
            const cached = await loadItinerary(ownerId)
            if (active && cached) {
              setAssignedStops(cached.stops)
              setUsingCachedItinerary(true)
              return
            }
          } catch {
            if (active) setAssignedStopsError('No se pudo abrir el itinerario guardado en este dispositivo.')
            return
          }
        }
        setAssignedStopsError(
          error instanceof DriverItineraryServiceError
            ? error.message
            : 'No se pudo cargar el itinerario asignado.',
        )
      } finally {
        if (active) setLoadingAssignedStops(false)
      }
    })()
    return () => { active = false }
  }, [ownerId, onSessionExpired, reloadKey])

  function retry() {
    setAssignedStopsError('')
    setLoadingAssignedStops(true)
    setReloadKey(value => value + 1)
  }

  if (ownerId && loadingAssignedStops) {
    return <ItineraryLayout>
      <p className="field-hint" role="status">Consultando paradas asignadas…</p>
      <div className="stop-list"><Skeleton variant="card" lines={4} /><Skeleton variant="card" lines={4} /></div>
    </ItineraryLayout>
  }

  if (ownerId && assignedStops?.length) {
    const nextStop = assignedStops
      .filter(stop => stop.status === 'PENDIENTE' || stop.status === 'EN_RUTA')
      .sort((a, b) => a.position - b.position)[0]
    const rest = assignedStops.filter(stop => stop !== nextStop).sort((a, b) => a.position - b.position)
    const done = assignedStops.filter(stop => stop.status === 'ENTREGADO' || stop.status === 'NO_ENTREGADO').length
    const panel = (stop: StopSummary) => <OfflineReportPanel variant="stop"
      ownerId={ownerId}
      stopId={stop.stopId}
      stopLabel={`la parada ${stop.position}`}
      transport={driverReportTransport}
      allowNewReport={stop.status === 'PENDIENTE' || stop.status === 'EN_RUTA'}
      onConfirmed={handleConfirmed}
    />
    return (
      <ItineraryLayout description={`${assignedStops.length} ${assignedStops.length === 1 ? 'parada asignada' : 'paradas asignadas'} · ${done} ${done === 1 ? 'completada' : 'completadas'}. Los reportes se guardan en el dispositivo y se envían con confirmación del servidor.`}>
        {usingCachedItinerary ? (
          <Alert tone="warning" role="status">Sin conexión: itinerario previamente guardado en este dispositivo.</Alert>
        ) : null}
        {assignedStopsError ? <Alert tone="danger">{assignedStopsError}</Alert> : null}
        {syncMessage ? <p className="field-hint" role="status">{syncMessage}</p> : null}
        {nextStop ? <section className="stop-card stop-card--next" aria-labelledby="next-stop-title">
          <p className="stop-card-label" id="next-stop-title"><Navigation aria-hidden="true" size={16} /> Siguiente parada</p>
          <StopDetails stop={nextStop} />
          {panel(nextStop)}
        </section> : <Alert tone="success" role="status" title="Recorrido completado">
          Todas las paradas tienen un resultado registrado.
        </Alert>}
        {rest.length ? <section aria-labelledby="route-title" className="route-section">
          <h2 id="route-title" className="section-title">{nextStop ? 'Resto del recorrido' : 'Recorrido'}</h2>
          <ol className="stop-list">
            {rest.map(stop => <li className="stop-card" key={stop.stopId}>
              <StopDetails stop={stop} />
              {panel(stop)}
            </li>)}
          </ol>
        </section> : null}
        <section className="card report-sync">
          <OfflineReportPanel variant="sync" ownerId={ownerId} stopId="" transport={driverReportTransport} onConfirmed={handleConfirmed} />
        </section>
      </ItineraryLayout>
    )
  }

  if (ownerId && assignedStops === null && assignedStopsError) {
    return <ItineraryLayout>
      <EmptyState icon={CloudOff} title="No se pudo cargar tu itinerario"
        action={<Button icon={RefreshCw} onClick={retry}>Reintentar</Button>}>
        <p role="alert">{assignedStopsError}</p>
        <p>Comprueba tu conexión. Si el problema continúa, avisa a tu coordinador.</p>
      </EmptyState>
    </ItineraryLayout>
  }

  if (ownerId && assignedStops?.length === 0) {
    return <ItineraryLayout>
      {assignedStopsError ? <Alert tone="danger">{assignedStopsError}</Alert> : null}
      {syncMessage ? <p className="field-hint" role="status">{syncMessage}</p> : null}
      <EmptyState icon={CheckCircle2} title="Aún no tienes paradas asignadas">
        <p>El servidor no tiene paradas asignadas a esta sesión. Cuando el coordinador te asigne una ruta, aparecerá aquí.</p>
      </EmptyState>
    </ItineraryLayout>
  }

  // Production default: never mix fictitious data with the driver's real state.
  if (!isDemoItineraryEnabled()) {
    return <ItineraryLayout>
      <EmptyState icon={CheckCircle2} title="Aún no tienes paradas asignadas">
        <p>Cuando el coordinador te asigne una ruta, aparecerá aquí.</p>
      </EmptyState>
    </ItineraryLayout>
  }

  return <section className="driver-page" aria-labelledby="driver-title">
    <div className="driver-demo-warning" role="note">
      <strong>Datos de demostración · Vista de demostración.</strong>
      <span>Ruta, pedidos, horarios, direcciones y alertas ficticios. No se consultan itinerarios reales.</span>
    </div>
    <p className="driver-eyebrow">EcoLogística Lima</p>
    <h1 id="driver-title" ref={heading} tabIndex={-1}>{detail ? 'Detalle de parada' : 'Mi itinerario'}</h1>
    {assignedStopsError ? <p role="alert">{assignedStopsError} Se muestra únicamente el ejemplo ficticio.</p> : null}
    <p className="driver-route-label">{current ? `Ruta ${current.id} · ${current.stops.length} paradas · Ejemplo ficticio` : 'Estado de demostración · Sin asignación'}</p>
    {current === null ? <>
      <div className="driver-empty driver-panel"><p className="driver-card-state">Sin asignación</p>
        <h2>Aún no tienes un itinerario</h2><p>Cuando se te asigne una ruta, verás aquí las paradas y las alertas operativas.</p>
        <strong>No hay paradas pendientes en este ejemplo.</strong>
      </div>
      <p>Si esperabas una ruta, solicita la asignación a tu coordinador.</p>
      {showEmpty ? <button className="driver-primary" type="button" onClick={() => { setShowEmpty(false); setFilter('TODAS') }}>Cargar ejemplo de itinerario</button> : null}
    </> : detail ? <>
      <StopCard stop={selected} next={selected.id === next?.id} />
      <section className="driver-panel" aria-labelledby="driver-info-title">
        <h2 id="driver-info-title">Información de entrega</h2><dl>
          <div><dt>Ventana de atención</dt><dd>{selected.window}</dd></div>
          <div><dt>Carga de demostración</dt><dd>{selected.load}</dd></div>
          <div><dt>Pedido de prueba</dt><dd>{selected.order}</dd></div>
          <div><dt>Recepción</dt><dd>{selected.reception}</dd></div>
          <div><dt>Estado</dt><dd>{DELIVERY_LABEL[selected.state]}</dd></div>
        </dl>
      </section>
      <OperationalAlerts alerts={getStopAlerts(current.alerts, selected.id)} />
      <section className="driver-panel" aria-labelledby="driver-instructions-title">
        <h2 id="driver-instructions-title">Antes de llegar</h2>
        <ol>{selected.instructions.map((instruction) => <li key={instruction}>{instruction}</li>)}</ol>
        <small>Estas indicaciones son ficticias.</small>
      </section>
      <button className="driver-primary" type="button" onClick={() => setSelected(null)}>Volver al itinerario</button>
    </> : <>
      <OperationalAlerts alerts={current.alerts} />
      <section aria-labelledby="driver-next-title"><h2 id="driver-next-title">Siguiente parada</h2>
        {next ? <><StopCard stop={next} next /><button className="driver-primary" type="button" onClick={() => setSelected(next)}>Ver detalle de parada</button></> : <p>No hay paradas pendientes en este ejemplo.</p>}
      </section>
      <section aria-labelledby="driver-list-title"><h2 id="driver-list-title">Recorrido de hoy</h2>
        <label className="driver-filter-label" htmlFor="driver-filter">Filtrar por estado</label>
        <select id="driver-filter" className="driver-filter" value={filter} onChange={(event) => setFilter(event.target.value as typeof filter)}>
          <option value="TODAS">Todas las paradas</option><option value="PENDIENTE">Pendientes</option>
          <option value="EN_RUTA">En ruta</option><option value="ENTREGADO">Completadas</option><option value="DEMORADO">Con demora prevista</option>
        </select>
        <ol className="driver-stops">{visible.map((stop) => <li key={stop.id}>
          <button className="driver-stop" type="button" onClick={() => setSelected(stop)} aria-label={`Ver parada ${stop.sequence}: ${stop.client}`}><StopCard stop={stop} next={stop.id === next?.id} /></button>
        </li>)}</ol>
        {visible.length === 0 ? <p role="status">No hay paradas con este estado.</p> : null}
      </section>
      <button className="driver-secondary" type="button" onClick={() => { setSelected(null); setShowEmpty(true) }}>Ver ejemplo sin asignación</button>
    </>}
    <p className="driver-footnote">Datos de demostración. No se consulta una ruta real ni se modifican entregas. Sin GPS o sincronización offline.</p>
  </section>
}
