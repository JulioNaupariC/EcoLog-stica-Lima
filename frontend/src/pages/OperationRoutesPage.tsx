import { useCallback, useEffect, useRef, useState } from 'react'
import { Map, RefreshCw } from 'lucide-react'
import { Alert, Badge, Button, EmptyState, PageHeader } from '../components/ui'
import { RouteExecution } from '../components/RouteExecution'
import { InvalidRouteData, operationDateInLima, retainTraffic, routeTime, UNASSIGNED_REASONS, validOperationDate } from '../domain/operationRoutes'
import type { OptimizationDetail, OptimizationPage } from '../domain/operationRoutes'
import { OperationRoutesError, operationRoutesApi } from '../services/operationRoutes'
import type { RouteSource } from '../services/operationRoutes'
import type { AuthRole } from '../services/auth'
import type { ClosedRoute, UpdatedStop } from '../domain/routeOutcomes'
import type { RouteOutcomeSource } from '../services/routeOutcomes'

const STATE = { EN_PROCESO: 'En proceso', COMPLETADA: 'Completada', FALLIDA: 'Fallida' }
const ROUTE_STATE = { PLANIFICADA: 'Planificada', EN_CURSO: 'En curso', CERRADA: 'Cerrada' }
const safeMessage = (error: unknown) => error instanceof OperationRoutesError ? error.message
  : error instanceof InvalidRouteData ? error.message : 'No se pudo cargar la información de rutas. Intenta de nuevo.'

export function OperationRoutesPage({ onSessionExpired, source = operationRoutesApi, role, outcomes }: {
  onSessionExpired: () => void; source?: RouteSource; role?: AuthRole; outcomes?: RouteOutcomeSource
}) {
  const [date, setDate] = useState(operationDateInLima)
  const [page, setPage] = useState(1)
  const [listing, setListing] = useState<OptimizationPage | null>(null)
  const [selectedId, setSelectedId] = useState('')
  const [detail, setDetail] = useState<OptimizationDetail | null>(null)
  const [routeId, setRouteId] = useState('')
  const [listBusy, setListBusy] = useState(true)
  const [detailBusy, setDetailBusy] = useState(false)
  const [listError, setListError] = useState('')
  const [detailError, setDetailError] = useState('')
  const listRequest = useRef(0), detailRequest = useRef(0)
  const listAbort = useRef<AbortController | null>(null), detailAbort = useRef<AbortController | null>(null)
  const latestDetail = useRef<OptimizationDetail | null>(null)

  const expire = useCallback((error: unknown) => {
    if (error instanceof OperationRoutesError && error.kind === 'unauthorized') { onSessionExpired(); return true }
    return false
  }, [onSessionExpired])
  const loadDetail = useCallback(async (id: string, expectedDate: string) => {
    const number = ++detailRequest.current
    detailAbort.current?.abort()
    const controller = new AbortController(); detailAbort.current = controller
    setSelectedId(id); setDetailBusy(true); setDetailError('')
    try {
      const value = await source.detail(id, controller.signal)
      if (number !== detailRequest.current || controller.signal.aborted) return false
      if (value.fecha_operacion !== expectedDate) throw new Error('Wrong date')
      const result = retainTraffic(latestDetail.current, value)
      latestDetail.current = result; setDetail(result)
      setRouteId(current => result.rutas.some(r => r.ruta_id === current) ? current : result.rutas[0]?.ruta_id ?? '')
      return true
    } catch (error) {
      if (number !== detailRequest.current || controller.signal.aborted || expire(error)) return false
      setDetailError(safeMessage(error))
      // Keep the previous plan only for a failed refresh of that same optimization.
      if (latestDetail.current?.optimizacion_id !== id) { latestDetail.current = null; setDetail(null) }
      return false
    } finally { if (number === detailRequest.current && !controller.signal.aborted) setDetailBusy(false) }
  }, [source, expire])
  const loadList = useCallback(async (chosenDate: string, chosenPage: number) => {
    const number = ++listRequest.current
    listAbort.current?.abort(); detailAbort.current?.abort(); detailRequest.current++
    const controller = new AbortController(); listAbort.current = controller
    setListing(null); setSelectedId(''); setDetail(null); latestDetail.current = null
    setRouteId(''); setListError(''); setDetailError(''); setListBusy(true); setDetailBusy(false)
    try {
      if (!validOperationDate(chosenDate)) throw new Error('Invalid date')
      const result = await source.list(chosenDate, chosenPage, controller.signal)
      if (number !== listRequest.current || controller.signal.aborted) return
      setListing(result); setPage(result.page)
      if (result.items[0]) void loadDetail(result.items[0].optimizacion_id, chosenDate)
    } catch (error) {
      if (number === listRequest.current && !controller.signal.aborted && !expire(error)) setListError(safeMessage(error))
    } finally { if (number === listRequest.current && !controller.signal.aborted) setListBusy(false) }
  }, [source, expire, loadDetail])
  useEffect(() => {
    let active = true
    const currentList = listRequest, currentDetail = detailRequest
    void Promise.resolve().then(() => { if (active) void loadList(date, 1) })
    return () => { active = false; currentList.current++; currentDetail.current++; listAbort.current?.abort(); detailAbort.current?.abort() }
  }, [date, loadList])
  const route = detail?.rutas.find(r => r.ruta_id === routeId)
  const pages = listing ? Math.max(1, Math.ceil(listing.total / listing.page_size)) : 1
  function updateRoute(result: UpdatedStop | ClosedRoute) {
    const current = latestDetail.current
    if (!current || current.optimizacion_id !== selectedId) return
    const updated = { ...current, rutas: current.rutas.map(route => route.ruta_id !== result.ruta_id ? route : {
      ...route, estado: 'ruta_estado' in result ? result.ruta_estado : result.estado,
      paradas: route.paradas.map(stop => 'parada_id' in result && stop.parada_id === result.parada_id ? { ...stop, estado: result.estado } : stop),
    }) }
    latestDetail.current = updated; setDetail(updated)
  }

  return <section className="operation-routes-page" aria-labelledby="operation-routes-title">
    <PageHeader titleId="operation-routes-title" title="Rutas y alertas en mapa" eyebrow="Operación"
      description="Selecciona una fecha y una optimización para consultar el plan y su secuencia de paradas. Hora de Lima (UTC−5)."
      breadcrumbs={[{ label: 'Inicio', to: '/' }, { label: 'Rutas y alertas en mapa' }]} />
    <section className="card route-filters" aria-label="Consulta de optimizaciones">
      <div className="form-field"><label htmlFor="route-date">Fecha de operación</label>
        <input id="route-date" type="date" value={date} required onChange={event => setDate(event.target.value)} /></div>
      <Button variant="secondary" icon={RefreshCw} disabled={listBusy || !validOperationDate(date)} onClick={() => { void loadList(date, 1) }}>Actualizar optimizaciones</Button>
      {listing?.items.length ? <div className="form-field"><label htmlFor="optimization-select">Optimización</label>
        <select id="optimization-select" value={selectedId} onChange={event => { latestDetail.current = null; setDetail(null); void loadDetail(event.target.value, date) }}>
          {listing.items.map(item => <option key={item.optimizacion_id} value={item.optimizacion_id}>{routeTime(item.solicitada_en)} · {STATE[item.estado]} · {item.optimizacion_id.slice(0, 8)}</option>)}
        </select></div> : null}
    </section>
    {listing?.simulado || detail?.simulado ? <Alert tone="warning" title="Datos simulados">Plan de demostración, sin tráfico real confirmado. El trazado no acredita una red vial medida.</Alert> : null}
    {listBusy ? <p role="status">Consultando optimizaciones…</p> : null}
    {listError ? <Alert tone="danger" title="No se pudo consultar la fecha">{listError}</Alert> : null}
    {listing?.total === 0 ? <EmptyState icon={Map} headingLevel={2} title="Sin optimizaciones en esta fecha">
      <p>Solicita al responsable de optimización que genere una solución para esta fecha y actualiza el listado.</p>
    </EmptyState> : null}
    {listing && listing.total > 0 ? <nav className="pagination" aria-label="Páginas de optimizaciones">
      <Button variant="secondary" disabled={listBusy || page <= 1} onClick={() => { void loadList(date, page - 1) }}>Anterior</Button>
      <span>Página {page} de {pages}</span>
      <Button variant="secondary" disabled={listBusy || page >= pages} onClick={() => { void loadList(date, page + 1) }}>Siguiente</Button>
    </nav> : null}
    {detailBusy ? <p role="status">Consultando el plan seleccionado…</p> : null}
    {detailError ? <Alert tone="danger" title="No se pudo cargar el plan" actions={<Button variant="secondary" onClick={() => { void loadDetail(selectedId, date) }}>Reintentar plan</Button>}>
      {detailError}{detail ? ' Se conserva la última versión del plan; no se pudo confirmar su vigencia.' : ''}
    </Alert> : null}
    {detail?.estado === 'EN_PROCESO' ? <p role="status">La optimización está en proceso. Usa Actualizar plan para consultar su resultado.</p> : null}
    {detail?.estado === 'FALLIDA' ? <Alert tone="danger" title="La optimización falló">No se generó una solución. Consulta al responsable y selecciona otra ejecución o vuelve a consultar.</Alert> : null}
    {detail ? <Button variant="secondary" icon={RefreshCw} disabled={detailBusy} onClick={() => { void loadDetail(selectedId, date) }}>Actualizar plan</Button> : null}
    {detail?.estado === 'COMPLETADA' ? <>
      {detail.rutas.length === 0 ? <EmptyState icon={Map} title="La solución no contiene rutas" headingLevel={2} /> : <div className="operation-routes-layout">
        <section className="card route-picker" aria-labelledby="route-picker-title"><h2 id="route-picker-title">Rutas de la solución</h2>
          <ul>{detail.rutas.map(r => <li key={r.ruta_id}><Button variant={r.ruta_id === routeId ? 'primary' : 'secondary'}
            aria-pressed={r.ruta_id === routeId} onClick={() => setRouteId(r.ruta_id)}>
            Ruta {r.vehiculo.placa} · {r.paradas.length} paradas · {r.metricas.distancia_km} km · {r.tiempo_min} min
          </Button><Badge tone="neutral">{ROUTE_STATE[r.estado]}</Badge></li>)}</ul>
        </section>
        {route ? <RouteExecution key={`${detail.optimizacion_id}-${route.ruta_id}`} route={route} detail={detail}
          canRecord={role === 'OPERADOR'} disabled={detailBusy || Boolean(detailError)} source={outcomes}
          onRecorded={updateRoute} onClosed={updateRoute} onRefresh={() => loadDetail(selectedId, date)} onSessionExpired={onSessionExpired} /> : null}
      </div>}
      <section className="card" aria-labelledby="unassigned-title"><h2 id="unassigned-title">Pedidos no asignados</h2>
        {detail.no_asignados.length ? <ul>{detail.no_asignados.map(item => <li key={item.pedido_id}><span className="route-id">{item.pedido_id}</span>: {UNASSIGNED_REASONS[item.motivo]}</li>)}</ul>
          : <p>No hay pedidos no asignados en esta solución.</p>}
      </section>
    </> : null}
  </section>
}
