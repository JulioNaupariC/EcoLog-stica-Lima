import { useEffect, useRef, useState } from 'react'
import { Alert, Button, LinkButton } from './ui'
import { OperationRouteDetail } from './OperationRouteDetail'
import { StopOutcomeForm } from './StopOutcomeForm'
import type { OperationRoute, OptimizationDetail } from '../domain/operationRoutes'
import { routeTime } from '../domain/operationRoutes'
import type { ClosedRoute, StopOutcome, UpdatedStop } from '../domain/routeOutcomes'
import { routeOutcomesApi, RouteOutcomeError } from '../services/routeOutcomes'
import type { RouteOutcomeSource } from '../services/routeOutcomes'
import '../styles/routeExecution.css'

export function RouteExecution({ route, detail, canRecord, disabled, source = routeOutcomesApi, onRecorded, onClosed, onRefresh, onSessionExpired }: {
  route: OperationRoute; detail: OptimizationDetail; canRecord: boolean; disabled: boolean; source?: RouteOutcomeSource
  onRecorded: (result: UpdatedStop) => void; onClosed: (result: ClosedRoute) => void
  onRefresh: () => Promise<boolean>; onSessionExpired: () => void
}) {
  const [pending, setPending] = useState(false), [uncertain, setUncertain] = useState<OptimizationDetail | null>(null), [forbidden, setForbidden] = useState(false)
  const [error, setError] = useState(''), [notice, setNotice] = useState(''), [confirm, setConfirm] = useState(false)
  const lock = useRef(false), request = useRef(0), abort = useRef<AbortController | null>(null)
  const errorRef = useRef<HTMLDivElement>(null), noticeRef = useRef<HTMLDivElement>(null)
  const cancelRef = useRef<HTMLButtonElement>(null), closeRef = useRef<HTMLButtonElement>(null)
  useEffect(() => () => { request.current++; abort.current?.abort() }, [])
  const needsRefresh = uncertain === detail
  const shownError = !uncertain || needsRefresh ? error : ''
  useEffect(() => { if (shownError) errorRef.current?.focus() }, [shownError])
  useEffect(() => { if (notice) noticeRef.current?.focus() }, [notice])
  useEffect(() => { if (confirm) cancelRef.current?.focus() }, [confirm])
  const pendingStops = route.paradas.filter(stop => stop.estado === 'PENDIENTE').length
  const editable = canRecord && !detail.simulado && !forbidden && route.estado !== 'CERRADA'
  const blocked = disabled || pending || needsRefresh
  const isCurrent = (current: number, signal: AbortSignal) => current === request.current && !signal.aborted

  function handleFailure(caught: unknown) {
    const failure = caught instanceof RouteOutcomeError ? caught : new RouteOutcomeError('unavailable')
    if (failure.kind === 'invalid') throw failure
    if (failure.kind === 'unauthorized') { onSessionExpired(); return }
    if (failure.kind === 'forbidden') setForbidden(true)
    else setUncertain(detail)
    setConfirm(false); setError(failure.message)
  }

  async function refresh() {
    if (lock.current) return
    lock.current = true; setPending(true)
    const current = request.current
    try {
      if (await onRefresh() && current === request.current) { setUncertain(null); setError(''); setConfirm(false) }
    } finally { if (current === request.current) setPending(false); lock.current = false }
  }
  async function perform(action: (signal: AbortSignal) => Promise<() => void>) {
    if (!editable || blocked || lock.current) return
    lock.current = true; setPending(true); setError(''); setNotice('')
    const current = ++request.current, controller = new AbortController(); abort.current = controller
    try {
      const commit = await action(controller.signal)
      if (isCurrent(current, controller.signal)) commit()
    } catch (caught) {
      if (isCurrent(current, controller.signal)) handleFailure(caught)
    } finally { if (current === request.current) setPending(false); lock.current = false }
  }
  const record = (stopId: string, sequence: number, outcome: StopOutcome) => perform(async signal => {
    const result = await source.record(route.ruta_id, stopId, outcome, signal)
    return () => { onRecorded(result); setNotice(`Resultado de parada ${sequence} registrado: ${result.estado === 'ATENDIDA' ? 'atendida' : 'no atendida'}.`) }
  })
  async function close() {
    if (pendingStops || !confirm) return
    try {
      await perform(async signal => {
        const result = await source.close(route.ruta_id, signal)
        if (result.paradas_atendidas + result.paradas_no_atendidas !== route.paradas.length) throw new RouteOutcomeError('unavailable')
        return () => { onClosed(result); setConfirm(false); setNotice(`Ruta cerrada el ${routeTime(result.cerrada_en)} (Lima). ${result.paradas_atendidas} atendidas y ${result.paradas_no_atendidas} no atendidas.`) }
      })
    } catch (caught) { setError(caught instanceof RouteOutcomeError ? caught.message : 'No se pudo cerrar la ruta.'); setConfirm(false) }
  }
  const actions = <div className="route-execution">
    {pending ? <p role="status">Confirmando operación con el servicio…</p> : null}
    {notice ? <Alert ref={noticeRef} tabIndex={-1} tone="success">{notice}</Alert> : null}
    {shownError ? <Alert ref={errorRef} tabIndex={-1} tone="danger" title="No se pudo confirmar la operación"
      actions={needsRefresh ? <Button variant="secondary" disabled={pending || disabled} onClick={() => { void refresh() }}>Actualizar estado de la ruta</Button> : undefined}>{shownError}</Alert> : null}
    {route.estado === 'CERRADA' ? <><p>Ruta cerrada. Sus resultados ya no se pueden editar.</p><LinkButton to="/indicadores/sostenibilidad" variant="secondary">Ver dashboard de sostenibilidad</LinkButton></> : null}
    {editable ? <>
      <p>{pendingStops ? `Faltan ${pendingStops} paradas por registrar.` : 'Todas las paradas tienen resultado. Puedes cerrar la ruta.'}</p>
      <Button ref={closeRef} disabled={blocked || pendingStops > 0} onClick={() => setConfirm(true)}>Cerrar ruta</Button>
      {confirm ? <section className="route-close-confirm" aria-labelledby="route-close-confirm-title">
        <h3 id="route-close-confirm-title">Confirmar cierre de ruta {route.vehiculo.placa}</h3>
        <p>Se cerrará esta ruta con {route.paradas.filter(stop => stop.estado === 'ATENDIDA').length} paradas atendidas y {route.paradas.filter(stop => stop.estado === 'NO_ATENDIDA').length} no atendidas. Los resultados quedarán bloqueados y alimentarán el dashboard del periodo de cierre.</p>
        <div className="form-actions"><Button ref={cancelRef} variant="secondary" disabled={pending} onClick={() => { setConfirm(false); closeRef.current?.focus() }}>Cancelar cierre</Button>
          <Button disabled={blocked || pendingStops > 0} onClick={() => { void close() }}>Confirmar cierre</Button></div>
      </section> : null}
    </> : null}
  </div>
  return <OperationRouteDetail route={route} detail={detail} routeActions={actions}
    renderStopActions={editable ? stop => stop.estado === 'PENDIENTE'
      ? <StopOutcomeForm sequence={stop.secuencia} stopId={stop.parada_id} operationDate={detail.fecha_operacion} disabled={blocked}
        onSave={outcome => record(stop.parada_id, stop.secuencia, outcome)} />
      : <p className="field-hint">Resultado final registrado; no se puede editar.</p> : undefined} />
}
