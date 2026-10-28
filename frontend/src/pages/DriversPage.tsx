import { useCallback, useEffect, useRef, useState } from 'react'
import { CalendarClock, ChevronLeft, ChevronRight, Pencil, Plus, RefreshCw, UserRound } from 'lucide-react'
import { DriverForm } from '../components/DriverForm'
import { Alert, Button, EmptyState, PageHeader, Skeleton, StatusBadge } from '../components/ui'
import { DriverServiceError, getDriver, listDrivers } from '../services/drivers'
import type { DriverDetail, DriverPage, DriverSummary } from '../services/drivers'

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
    <PageHeader titleId="drivers-title" title="Conductores" eyebrow="Gestión operativa"
      breadcrumbs={[{ label: 'Inicio', to: '/' }, { label: 'Conductores' }]}
      description="Consulta los perfiles registrados y mantén sus datos y disponibilidad. Horarios de Lima."
      actions={<Button icon={Plus} disabled={blocked || opening !== null} onClick={() => {
        setEditor({ mode: 'create' }); setSaved(null); setSuccess(''); setDetailError('')
      }}>Nuevo conductor</Button>} />
    {success && saved ? <Alert tone="success" role="status" title={success}
      actions={<Button variant="secondary" size="sm" disabled={blocked || opening !== null} onClick={() => { void open(saved.conductor_id) }}>Consultar perfil guardado</Button>}>
      {saved.nombre} · {saved.habilitado_asignacion ? 'Habilitado para asignación' : 'No habilitado para asignación'}
    </Alert> : null}
    {editor ? <DriverForm key={editor.mode === 'edit' ? editor.driver.conductor_id : 'create'}
      driver={editor.mode === 'edit' ? editor.driver : null} onSaved={savedDriver} onCancel={closeEditor} onAccessError={accessError} /> : null}
    <section className="card driver-list" aria-labelledby="driver-list-title" aria-busy={list.status === 'loading'}>
      <div className="card-header">
        <div className="card-heading">
          <h2 id="driver-list-title" className="card-title" ref={listHeading} tabIndex={-1}>Conductores registrados</h2>
          {list.status === 'ready' && list.result ? <p className="card-description">
            {list.result.total} {list.result.total === 1 ? 'conductor registrado' : 'conductores registrados'}
          </p> : null}
        </div>
        <div className="card-actions">
          <Button variant="secondary" size="sm" icon={RefreshCw} disabled={list.status === 'loading' || blocked} onClick={() => { void load(page) }}>Actualizar listado</Button>
        </div>
      </div>
      {list.status === 'loading' ? <>
        <p className="field-hint" role="status">Cargando conductores…</p>
        <div className="entity-grid"><Skeleton variant="card" /><Skeleton variant="card" /></div>
      </> : null}
      {list.status === 'error' ? <Alert tone="danger" title="No se pudo cargar el listado."
        actions={!blocked ? <Button variant="secondary" size="sm" onClick={() => { void load(page) }}>Reintentar carga</Button> : undefined}>
        {list.error}
      </Alert> : null}
      {list.status === 'ready' && list.result ? <>
        {list.result.items.length === 0 ? <EmptyState icon={UserRound} headingLevel={3}
          title={list.result.total === 0 ? 'Sin conductores' : 'Página vacía'}>
          <p role="status">{list.result.total === 0 ? 'Aún no hay conductores registrados. Usa “Nuevo conductor” para comenzar.' : 'No hay conductores en esta página.'}</p>
        </EmptyState> : null}
        <ul className="entity-grid">
          {list.result.items.map(driver => <li key={driver.conductor_id}>
            <article className="entity-card">
              <div className="entity-card-head">
                <h3>{driver.nombre}</h3>
                <StatusBadge status={driver.estado === 'ACTIVO' ? 'ACTIVO' : 'INACTIVO'} />
              </div>
              <StatusBadge status={driver.habilitado_asignacion ? 'HABILITADO' : 'NO_HABILITADO'} />
              <p className="visually-hidden">{driver.habilitado_asignacion ? 'Habilitado para asignación' : 'No habilitado para asignación'}</p>
              <dl className="entity-meta">
                <div><dt><CalendarClock aria-hidden="true" size={16} /> Disponibilidad · Lima</dt>
                  <dd>{availability(driver.disponible_desde, driver.disponible_hasta)}</dd></div>
              </dl>
              <Button variant="secondary" size="sm" icon={Pencil} disabled={blocked || opening !== null}
                aria-label={'Ver y editar perfil de ' + driver.nombre} onClick={() => { void open(driver.conductor_id) }}>Ver y editar perfil</Button>
            </article>
          </li>)}
        </ul>
        <nav className="pagination" aria-label="Páginas de conductores">
          <Button variant="secondary" size="sm" icon={ChevronLeft} disabled={page <= 1} onClick={() => { void load(page - 1) }}>Anterior</Button>
          <span>Página {page} de {totalPages}</span>
          <Button variant="secondary" size="sm" icon={ChevronRight} disabled={page >= totalPages} onClick={() => { void load(page + 1) }}>Siguiente</Button>
        </nav>
      </> : null}
    </section>
    {opening ? <p className="field-hint" role="status">Cargando perfil…</p> : null}
    {detailError ? <Alert tone="danger">{detailError}</Alert> : null}
  </section>
}
