import { useCallback, useEffect, useRef, useState } from 'react'
import { DriverForm } from '../components/DriverForm'
import { DriverServiceError, getDriver, listDrivers } from '../services/drivers'
import type { DriverDetail, DriverPage, DriverSummary } from '../services/drivers'
import './DriversPage.css'

const dateFormat = new Intl.DateTimeFormat('es-PE', { timeZone: 'America/Lima', dateStyle: 'short', timeStyle: 'short' })
function availability(start: string | null, end: string | null): string {
  return start && end ? dateFormat.format(new Date(start)) + ' — ' + dateFormat.format(new Date(end)) : 'Sin disponibilidad'
}
interface ListState { status: 'loading' | 'ready' | 'error'; result: DriverPage | null; error: string }
type Editor = { mode: 'create' } | { mode: 'edit'; driver: DriverDetail } | null

export function DriversPage({ onSessionExpired }: { onSessionExpired: () => void }) {
  const [list, setList] = useState<ListState>({ status: 'loading', result: null, error: '' })
  const [page, setPage] = useState(1)
  const [editor, setEditor] = useState<Editor>(null)
  const [opening, setOpening] = useState<string | null>(null)
  const [detailError, setDetailError] = useState('')
  const [saved, setSaved] = useState<DriverSummary | null>(null)
  const [success, setSuccess] = useState('')
  const [blocked, setBlocked] = useState(false)
  const requestNumber = useRef(0)
  const detailNumber = useRef(0)
  const listHeading = useRef<HTMLHeadingElement>(null)
  const accessError = useCallback((error: DriverServiceError) => {
    if (error.kind === 'unauthorized') onSessionExpired()
    if (error.kind === 'forbidden') {
      setBlocked(true); setEditor(null); setDetailError(error.message)
      setList({ status: 'error', result: null, error: error.message })
    }
  }, [onSessionExpired])
  const load = useCallback(async (nextPage: number) => {
    const number = ++requestNumber.current
    setPage(nextPage)
    setList({ status: 'loading', result: null, error: '' })
    try {
      const result = await listDrivers(nextPage)
      if (number === requestNumber.current) setList({ status: 'ready', result, error: '' })
    } catch (error) {
      if (number !== requestNumber.current) return
      if (error instanceof DriverServiceError) accessError(error)
      setList({ status: 'error', result: null, error: error instanceof DriverServiceError ? error.message : 'No se pudo cargar el listado.' })
    }
  }, [accessError])
  useEffect(() => {
    const lists = requestNumber
    const details = detailNumber
    const number = ++lists.current
    void listDrivers(1).then(result => {
      if (number === lists.current) setList({ status: 'ready', result, error: '' })
    }).catch((error: unknown) => {
      if (number !== lists.current) return
      if (error instanceof DriverServiceError) accessError(error)
      setList({ status: 'error', result: null, error: error instanceof DriverServiceError ? error.message : 'No se pudo cargar el listado.' })
    })
    return () => { lists.current++; details.current++ }
  }, [accessError])

  async function open(id: string) {
    const number = ++detailNumber.current
    setOpening(id); setDetailError(''); setEditor(null)
    try {
      const driver = await getDriver(id)
      if (number === detailNumber.current) setEditor({ mode: 'edit', driver })
    } catch (error) {
      if (number !== detailNumber.current) return
      if (error instanceof DriverServiceError) accessError(error)
      setDetailError(error instanceof DriverServiceError ? error.message : 'No se pudo consultar el perfil.')
    } finally {
      if (number === detailNumber.current) setOpening(null)
    }
  }
  function closeEditor() {
    setEditor(null)
    listHeading.current?.focus()
  }
  function savedDriver(driver: DriverSummary, created: boolean) {
    setSaved(driver)
    setSuccess(created ? 'Conductor registrado correctamente.' : 'Conductor actualizado correctamente.')
    closeEditor()
    void load(created ? 1 : page)
  }
  const totalPages = Math.max(1, Math.ceil((list.result?.total ?? 0) / 10))
  return <section className="drivers-page" aria-labelledby="drivers-title">
    <div className="driver-page-heading">
      <div><p className="eyebrow">Gestión operativa</p><h1 id="drivers-title">Conductores</h1></div>
      <button className="submit-button" type="button" disabled={blocked || opening !== null} onClick={() => {
        setEditor({ mode: 'create' }); setSaved(null); setSuccess(''); setDetailError('')
      }}>Nuevo conductor</button>
    </div>
    <p className="form-intro">Consulta los perfiles registrados y mantén sus datos y disponibilidad. Horarios de Lima.</p>
    {success && saved ? <div className="form-alert success-alert" role="status">
      <strong>{success}</strong><span>{saved.nombre} · {saved.habilitado_asignacion ? 'Habilitado para asignación' : 'No habilitado para asignación'}</span>
      <button className="drivers-secondary" type="button" disabled={blocked || opening !== null} onClick={() => { void open(saved.conductor_id) }}>Consultar perfil guardado</button>
    </div> : null}
    <section className="driver-list" aria-labelledby="driver-list-title" aria-busy={list.status === 'loading'}>
      <div className="driver-list-heading">
        <h2 id="driver-list-title" ref={listHeading} tabIndex={-1}>Conductores registrados</h2>
        <button className="drivers-secondary" type="button" disabled={list.status === 'loading' || blocked} onClick={() => { void load(page) }}>Actualizar listado</button>
      </div>
      {list.status === 'loading' ? <p className="drivers-empty" role="status">Cargando conductores…</p> : null}
      {list.status === 'error' ? <div className="form-alert error-alert" role="alert">
        <strong>No se pudo cargar el listado.</strong><span>{list.error}</span>
        {!blocked ? <button className="drivers-secondary" type="button" onClick={() => { void load(page) }}>Reintentar carga</button> : null}
      </div> : null}
      {list.status === 'ready' && list.result ? <>
        <p className="driver-count">{list.result.total} {list.result.total === 1 ? 'conductor registrado' : 'conductores registrados'}</p>
        {list.result.items.length === 0 ? <p className="drivers-empty" role="status">{list.result.total === 0 ? 'Aún no hay conductores registrados. Usa “Nuevo conductor” para comenzar.' : 'No hay conductores en esta página.'}</p> : null}
        <div className="driver-cards">
          {list.result.items.map(driver => <article className="driver-list-card" key={driver.conductor_id}>
            <div className="driver-card-heading"><h3>{driver.nombre}</h3><span className="driver-state">{driver.estado === 'ACTIVO' ? 'Activo' : 'Inactivo'}</span></div>
            <p className={'driver-assignment ' + (driver.habilitado_asignacion ? '' : 'driver-warning')}>
              {driver.habilitado_asignacion ? 'Habilitado para asignación' : 'No habilitado para asignación'}</p>
            <p><strong>Disponibilidad · Lima</strong><br />{availability(driver.disponible_desde, driver.disponible_hasta)}</p>
            <button className="drivers-secondary" type="button" disabled={blocked || opening !== null}
              aria-label={'Ver y editar ' + driver.nombre} onClick={() => { void open(driver.conductor_id) }}>Ver y editar perfil</button>
          </article>)}
        </div>
        <nav className="driver-pagination" aria-label="Páginas de conductores">
          <button className="drivers-secondary" type="button" disabled={page <= 1} onClick={() => { void load(page - 1) }}>Anterior</button>
          <span>Página {page} de {totalPages}</span>
          <button className="drivers-secondary" type="button" disabled={page >= totalPages} onClick={() => { void load(page + 1) }}>Siguiente</button>
        </nav>
      </> : null}
    </section>
    {opening ? <p className="drivers-empty" role="status">Cargando perfil…</p> : null}
    {detailError ? <div className="form-alert error-alert" role="alert">{detailError}</div> : null}
    {editor ? <DriverForm key={editor.mode === 'edit' ? editor.driver.conductor_id : 'create'}
      driver={editor.mode === 'edit' ? editor.driver : null} onSaved={savedDriver} onCancel={closeEditor} onAccessError={accessError} /> : null}
  </section>
}
