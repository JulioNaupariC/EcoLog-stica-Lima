import { useEffect, useRef, useState } from 'react'
import { DEMO_ITINERARY } from '../data/demoDriverItinerary'
import { DELIVERY_LABEL, getNextStop, getStopAlerts } from '../domain/driverItinerary'
import type { DeliveryState, DemoItinerary, DriverAlert, DriverStop } from '../domain/driverItinerary'
import './DriverItineraryPage.css'

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

function StopCard({ stop, next = false }: { stop: DriverStop; next?: boolean }) {
  return <span className={`driver-card driver-card-${stop.state.toLowerCase()}${next ? ' driver-card-next' : ''}`}>
    <span className="driver-card-state">{next ? 'Siguiente' : DELIVERY_LABEL[stop.state]} · {String(stop.sequence).padStart(2, '0')}</span>
    <strong>{stop.client}</strong><span>{stop.address}</span><small>{stop.window} · {stop.load}</small>
  </span>
}

export function DriverItineraryPage({ itinerary = DEMO_ITINERARY }: { itinerary?: DemoItinerary | null }) {
  const [selected, setSelected] = useState<DriverStop | null>(null)
  const [filter, setFilter] = useState<'TODAS' | DeliveryState>('TODAS')
  const [showEmpty, setShowEmpty] = useState(false)
  const heading = useRef<HTMLHeadingElement>(null)
  const current = showEmpty ? null : itinerary
  const next = getNextStop(current?.stops ?? [])
  const visible = (current?.stops ?? []).filter((stop) => filter === 'TODAS' || stop.state === filter)
  const detail = current !== null && selected !== null
  useEffect(() => { heading.current?.focus() }, [selected, showEmpty])

  return <section className="driver-page" aria-labelledby="driver-title">
    <div className="driver-demo-warning" role="note">
      <strong>Datos de demostración · Vista de demostración.</strong>
      <span>Ruta, pedidos, horarios, direcciones y alertas ficticios. No se consultan itinerarios reales.</span>
    </div>
    <p className="driver-eyebrow">EcoLogística Lima</p>
    <h1 id="driver-title" ref={heading} tabIndex={-1}>{detail ? 'Detalle de parada' : 'Mi itinerario'}</h1>
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
