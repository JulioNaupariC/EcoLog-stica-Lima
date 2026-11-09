import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Button } from './ui'
import { attendanceTime, limaDateTimeInput } from '../domain/routeOutcomes'
import type { StopOutcome } from '../domain/routeOutcomes'
import { RouteOutcomeError } from '../services/routeOutcomes'

function OutcomeEditor({ sequence, stopId, operationDate, disabled, onSave, onCancel }: {
  sequence: number; stopId: string; operationDate: string; disabled: boolean
  onSave: (outcome: StopOutcome) => Promise<void>; onCancel: () => void
}) {
  const [state, setState] = useState<'ATENDIDA' | 'NO_ATENDIDA'>('ATENDIDA')
  const [time, setTime] = useState(limaDateTimeInput)
  const [error, setError] = useState('')
  const input = useRef<HTMLInputElement>(null), select = useRef<HTMLSelectElement>(null)
  useEffect(() => { input.current?.focus() }, [])
  useEffect(() => { if (error && !disabled) (input.current ?? select.current)?.focus() }, [error, disabled])
  async function save(event: FormEvent) {
    event.preventDefault()
    if (disabled) return
    setError('')
    let payload: StopOutcome
    try { payload = state === 'ATENDIDA' ? { estado: state, atendida_en: attendanceTime(time, operationDate) } : { estado: state } }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'Revisa la hora de atención.'); (input.current ?? select.current)?.focus(); return }
    try { await onSave(payload) }
    catch (caught) { if (caught instanceof RouteOutcomeError && caught.kind === 'invalid') setError(caught.message) }
  }
  const base = `outcome-${stopId}`
  return <form className="stop-outcome-form" onSubmit={event => { void save(event) }} noValidate>
    <fieldset disabled={disabled}>
      <legend>Resultado de parada {sequence}</legend>
      <div className="form-field"><label htmlFor={`${base}-state`}>Resultado de parada {sequence}</label>
        <select ref={select} id={`${base}-state`} value={state} aria-invalid={Boolean(error)} aria-describedby={error ? `${base}-error` : undefined}
          onChange={event => { setState(event.target.value as typeof state); setError('') }}>
          <option value="ATENDIDA">Atendida</option><option value="NO_ATENDIDA">No atendida</option>
        </select></div>
      {state === 'ATENDIDA' ? <div className="form-field">
        <label htmlFor={`${base}-time`}>Hora real de parada {sequence} (Lima)</label>
        <input ref={input} id={`${base}-time`} name="atendida_en" type="datetime-local" step="1" required value={time}
          min={`${operationDate}T00:00:00`} max={limaDateTimeInput()} aria-invalid={Boolean(error)}
          aria-describedby={`${base}-value ${base}-hint${error ? ` ${base}-error` : ''}`} onChange={event => { setTime(event.target.value); setError('') }} />
        <p id={`${base}-value`} className="field-hint">Hora de Lima (24 h): {time ? time.replace('T', ' ') : 'sin hora seleccionada'}.</p>
        <p id={`${base}-hint`} className="field-hint">Hora actual como propuesta editable. Confirma la atención real; no se toma de la ETA. No puede ser futura ni anterior al día de la ruta.</p>
      </div> : <p className="field-hint">No atendida cuenta como incumplida para el indicador de ventanas.</p>}
      {error ? <p id={`${base}-error`} role="alert" className="field-error">{error}</p> : null}
      <div className="form-actions"><Button type="submit">Guardar resultado de parada {sequence}</Button>
        <Button variant="secondary" onClick={onCancel}>Cancelar registro de parada {sequence}</Button></div>
    </fieldset>
  </form>
}

export function StopOutcomeForm({ sequence, stopId, operationDate, disabled, onSave }: {
  sequence: number; stopId: string; operationDate: string; disabled: boolean; onSave: (outcome: StopOutcome) => Promise<void>
}) {
  const [open, setOpen] = useState(false)
  const opener = useRef<HTMLButtonElement>(null), returnFocus = useRef(false)
  useEffect(() => { if (!open && returnFocus.current) { opener.current?.focus(); returnFocus.current = false } }, [open])
  return open ? <OutcomeEditor sequence={sequence} stopId={stopId} operationDate={operationDate} disabled={disabled} onSave={onSave}
    onCancel={() => { returnFocus.current = true; setOpen(false) }} />
    : <Button ref={opener} disabled={disabled} onClick={() => setOpen(true)}>Registrar resultado de parada {sequence}</Button>
}
