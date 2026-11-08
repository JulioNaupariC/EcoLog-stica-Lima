import { lazy, Suspense, useState } from 'react'
import type { ReactNode } from 'react'
import { AlertTriangle, Map, ShieldAlert } from 'lucide-react'
import { Alert, Badge, Button } from './ui'
import { DRIVER_ASSIGNMENT_REASONS, routeTime } from '../domain/operationRoutes'
import type { OperationRoute, OptimizationDetail, RouteAlert, RouteStop } from '../domain/operationRoutes'

const OperationRouteMap = lazy(() => import('./OperationRouteMap').then(module => ({ default: module.OperationRouteMap })))
const NUMBER = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 2 })
const STOP_STATE = { PENDIENTE: 'Pendiente', ATENDIDA: 'Atendida', NO_ATENDIDA: 'No atendida' }

export function RouteAlerts({ alerts }: { alerts: RouteAlert[] }) {
  return <ul className="route-alerts">{alerts.map(a => <li key={a.id}>
    <Badge tone={a.bloqueo ? 'danger' : 'warning'} icon={a.bloqueo ? ShieldAlert : AlertTriangle}>
      {a.bloqueo ? 'Bloqueo configurado' : 'Riesgo informativo'} · Severidad {a.severidad.toLowerCase()}
    </Badge>
    <p>{a.tipo}: {a.texto}</p><p className="field-hint">Fuente: {a.fuente} · <time dateTime={a.hora}>{routeTime(a.hora)} (Lima)</time> · Alcance: {a.alcance}</p>
    {!a.bloqueo ? <p className="field-hint">Esta alerta no excluye automáticamente una vía.</p> : null}
  </li>)}</ul>
}

export function OperationRouteDetail({ route, detail, routeActions, renderStopActions }: {
  route: OperationRoute; detail: OptimizationDetail; routeActions?: ReactNode; renderStopActions?: (stop: RouteStop) => ReactNode
}) {
  const [showMap, setShowMap] = useState(true)
  const [selectedStopId, setSelectedStopId] = useState<string>()
  const alerts = detail.alertas.filter(a => a.rutaId === route.ruta_id)
  const traffic = detail.trafico
  return <section className="card route-detail" aria-labelledby="selected-route-title">
    <h2 id="selected-route-title">Ruta {route.vehiculo.placa}</h2>
    <p>Estado: {route.estado.replaceAll('_', ' ').toLowerCase()} · {route.conductor ? route.conductor.nombre : DRIVER_ASSIGNMENT_REASONS[route.motivo_sin_conductor ?? 'SIN_CONDUCTOR_ELEGIBLE']}</p>
    {routeActions}
    <dl className="route-metrics">
      <div><dt>Distancia</dt><dd>{NUMBER.format(route.metricas.distancia_km)} km</dd></div>
      <div><dt>Duración planificada</dt><dd>{NUMBER.format(route.tiempo_min)} min</dd></div>
      <div><dt>Emisiones estimadas</dt><dd>{NUMBER.format(route.metricas.co2_kg)} kg CO₂</dd></div>
      <div><dt>Combustible</dt><dd>{NUMBER.format(route.metricas.combustible_l)} L</dd></div>
      <div><dt>Costo</dt><dd>S/ {NUMBER.format(route.metricas.costo_soles)}</dd></div>
    </dl>
    <p className="field-hint">ETA del plan, estimación {detail.finalizada_en ? 'calculada en' : 'sin hora de cálculo informada; solicitud en'} <time dateTime={detail.finalizada_en ?? detail.solicitada_en}>{routeTime(detail.finalizada_en ?? detail.solicitada_en)} (Lima)</time>. No representa atención real ni tráfico en vivo.</p>
    <p>Salida: {routeTime(route.salida)} · Regreso previsto: {routeTime(route.regreso)} (Lima).</p>
    {traffic.estado === 'SIN_DATOS' ? <Alert tone="warning" title="Sin datos de tráfico">No hay una medición de tráfico disponible ni una hora de fuente. Se conserva la ETA del plan.</Alert>
      : <Alert tone={traffic.estado === 'DEGRADADO' ? 'warning' : 'info'}
        title={traffic.estado === 'DEGRADADO' ? 'Tráfico no disponible; último dato conservado' : 'Último dato de tráfico'}>
        Fuente: {traffic.fuente} · <time dateTime={traffic.actualizado_en ?? undefined}>{traffic.actualizado_en ? routeTime(traffic.actualizado_en) : 'Hora no disponible'} (Lima)</time>.
        {traffic.estado === 'DEGRADADO' ? ' Estado degradado; esta hora corresponde al dato, no a la consulta.' : null}
      </Alert>}
    {traffic.tramos.filter(t => t.rutaId === route.ruta_id).length ? <section aria-label="Tiempos de tráfico por tramo">
      <h3>Tiempos por tramo</h3><ul>{traffic.tramos.filter(t => t.rutaId === route.ruta_id).map((t, i) =>
        <li key={i}>{t.origen} → {t.destino}: {NUMBER.format(t.tiempo_min)} min · Fuente: {traffic.fuente}</li>)}</ul>
    </section> : <p className="field-hint">Sin tiempos medidos por tramo. No se calculan restando las ETA.</p>}
    <section aria-labelledby="route-alerts-title"><h3 id="route-alerts-title">Alertas de la ruta</h3>
      {!detail.alertasDisponibles ? <p>El servicio actual no publica alertas. Esto no garantiza ausencia de riesgos.</p>
        : alerts.length ? <RouteAlerts alerts={alerts} /> : <p>Sin alertas en la fuente y corte consultados.</p>}
    </section>
    <div className="route-map-actions">
      <a href="#route-stop-list">Ir a la lista accesible de paradas</a>
      <Button variant="secondary" icon={Map} aria-expanded={showMap} aria-controls="route-map"
        onClick={() => setShowMap(value => !value)}>{showMap ? 'Ocultar mapa' : 'Mostrar mapa'}</Button>
    </div>
    {showMap ? <div id="route-map"><Suspense fallback={<p role="status">Cargando mapa… La lista de paradas ya está disponible.</p>}>
      <OperationRouteMap key={route.ruta_id} route={route} alerts={alerts} selectedStopId={selectedStopId} />
    </Suspense></div> : null}
    <section aria-labelledby="route-stop-list" className="route-stop-section">
      <h3 id="route-stop-list" tabIndex={-1}>Secuencia de paradas</h3>
      <ol className="route-stop-list">{route.paradas.map(stop => <li key={stop.parada_id}>
        <h4>Parada {stop.secuencia}</h4><p>Pedido: <span className="route-id">{stop.pedido_id}</span></p>
        <p>Ubicación: {stop.latitud.toFixed(5)}, {stop.longitud.toFixed(5)} (latitud, longitud).</p>
        <dl>
          <div><dt>ETA estimada (Lima)</dt><dd><time dateTime={stop.eta}>{routeTime(stop.eta)}</time></dd></div>
          <div><dt>Ventana de atención (Lima)</dt><dd>{routeTime(stop.ventana_inicio)} a {routeTime(stop.ventana_fin)}</dd></div>
          <div><dt>Estado de la parada</dt><dd>{STOP_STATE[stop.estado]}</dd></div>
        </dl>
        {renderStopActions?.(stop)}
        <RouteAlerts alerts={alerts.filter(a => !a.paradaId || a.paradaId === stop.parada_id)} />
        <Button variant="secondary" onClick={() => { setSelectedStopId(stop.parada_id); setShowMap(true) }}>
          Ver parada {stop.secuencia} en mapa
        </Button>
      </li>)}</ol>
    </section>
  </section>
}
