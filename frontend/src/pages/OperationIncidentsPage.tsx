import { useCallback, useEffect, useRef, useState } from 'react'
import { AlertTriangle, ChevronLeft, ChevronRight, ClipboardList, ExternalLink, Info, RefreshCw, ShieldAlert } from 'lucide-react'
import { Alert, Badge, Button, DataTable, EmptyState, PageHeader, Skeleton } from '../components/ui'
import type { BadgeTone, Column } from '../components/ui'
import { INCIDENT_TYPES } from '../domain/incident'
import { IncidentListError, listPendingIncidents } from '../services/incidentList'
import type { IncidentPage, PendingIncident } from '../services/incidentList'

const PAGE_SIZE = 20
const limaTime = new Intl.DateTimeFormat('es-PE', {
  timeZone: 'America/Lima', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
})
const fullLimaTime = new Intl.DateTimeFormat('es-PE', {
  timeZone: 'America/Lima', dateStyle: 'full', timeStyle: 'short', hourCycle: 'h23',
})
const SEVERITIES = {
  BAJA: { label: 'Baja', tone: 'info' as BadgeTone, icon: Info },
  MEDIA: { label: 'Media', tone: 'warning' as BadgeTone, icon: AlertTriangle },
  ALTA: { label: 'Alta', tone: 'danger' as BadgeTone, icon: ShieldAlert },
}

function occurrence(value: string) {
  const parts = limaTime.formatToParts(new Date(value))
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find(item => item.type === type)?.value
  return `${part('day')}/${part('month')} ${part('hour')}:${part('minute')}`
}

function Observation({ text }: { text: string }) {
  if (!text) return <span className="field-hint">Sin observación</span>
  const characters = [...text]
  if (characters.length <= 100) return <span className="incident-observation">{text}</span>
  return <div className="incident-observation">
    <p>{characters.slice(0, 100).join('')}…</p>
    <details>
      <summary>Ver observación completa</summary>
      <p>{text}</p>
    </details>
  </div>
}

function LoadingIncidents() {
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    const timer = window.setTimeout(() => setSlow(true), 1_000)
    return () => window.clearTimeout(timer)
  }, [])
  return <div className="incident-loading">
    <p className="field-hint" role="status">Cargando incidencias pendientes…</p>
    {slow ? <Skeleton variant="card" lines={6} /> : null}
  </div>
}

const columns: Column<PendingIncident>[] = [
  { key: 'hora', header: 'Hora (Lima)', render: item => <time dateTime={item.ocurrida_en}
    aria-label={`${fullLimaTime.format(new Date(item.ocurrida_en))}, hora de Lima`}>{occurrence(item.ocurrida_en)}</time> },
  { key: 'tipo', header: 'Tipo', primary: true, render: item => INCIDENT_TYPES[item.tipo] },
  { key: 'severidad', header: 'Severidad', render: item => {
    const severity = SEVERITIES[item.severidad]
    return <Badge tone={severity.tone} icon={severity.icon}>{severity.label}</Badge>
  } },
  { key: 'conductor', header: 'Conductor', render: item => <span>{item.conductor.nombre}</span> },
  { key: 'ubicacion', header: 'Ubicación', render: item => <div className="incident-location">
    <span>{item.latitud.toFixed(5)}, {item.longitud.toFixed(5)}</span>
    <a href={`https://www.openstreetmap.org/?mlat=${item.latitud}&mlon=${item.longitud}#map=17/${item.latitud}/${item.longitud}`}
      target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">
      Ver en mapa <ExternalLink size={14} aria-hidden="true" />
      <span className="visually-hidden"> (nueva pestaña)</span>
    </a>
  </div> },
  { key: 'observacion', header: 'Observación', render: item => <Observation text={item.observacion} /> },
]

type ListState =
  | { status: 'loading'; page: number }
  | { status: 'ready'; page: number; result: IncidentPage }
  | { status: 'error'; page: number; message: string; forbidden: boolean }

/** ECL-75: read-only pending incidents for Administrator and Operator. */
export function OperationIncidentsPage({ onSessionExpired }: { onSessionExpired: () => void }) {
  const [list, setList] = useState<ListState>({ status: 'loading', page: 1 })
  const requests = useRef(0)
  const controller = useRef<AbortController | null>(null)

  const load = useCallback(async (page: number) => {
    const number = ++requests.current
    controller.current?.abort()
    const current = new AbortController()
    controller.current = current
    setList({ status: 'loading', page })
    try {
      let result = await listPendingIncidents(page, PAGE_SIZE, current.signal)
      if (number !== requests.current || current.signal.aborted) return
      // A concurrent validation can remove the last page. Return to a valid page.
      const lastPage = Math.max(1, Math.ceil(result.total / PAGE_SIZE))
      if (page > lastPage) result = await listPendingIncidents(lastPage, PAGE_SIZE, current.signal)
      if (number === requests.current && !current.signal.aborted) {
        setList({ status: 'ready', page: result.page, result })
      }
    } catch (error) {
      if (number !== requests.current || current.signal.aborted) return
      if (error instanceof IncidentListError && error.kind === 'unauthorized') { onSessionExpired(); return }
      setList({ status: 'error', page,
        message: error instanceof IncidentListError ? error.message : 'No se pudo cargar el listado. Intenta de nuevo.',
        forbidden: error instanceof IncidentListError && error.kind === 'forbidden' })
    }
  }, [onSessionExpired])

  useEffect(() => {
    let mounted = true
    void Promise.resolve().then(() => { if (mounted) void load(1) })
    const activeRequests = requests
    const activeController = controller
    return () => {
      mounted = false
      activeRequests.current++
      activeController.current?.abort()
    }
  }, [load])

  const busy = list.status === 'loading'
  const totalPages = list.status === 'ready' ? Math.max(1, Math.ceil(list.result.total / PAGE_SIZE)) : list.page

  return <section className="incidents-page" aria-labelledby="incidents-title">
    <PageHeader titleId="incidents-title" title="Incidencias pendientes" eyebrow="Operación"
      breadcrumbs={[{ label: 'Inicio', to: '/' }, { label: 'Incidencias pendientes' }]}
      description="Consulta los reportes de los conductores pendientes de validación, del más reciente al más antiguo."
      actions={<Button variant="secondary" icon={RefreshCw} disabled={busy} onClick={() => { void load(list.page) }}>
        Actualizar listado
      </Button>} />
    <section className="card" aria-labelledby="incident-list-title" aria-busy={busy}>
      <div className="card-header">
        <div className="card-heading">
          <h2 id="incident-list-title" className="card-title">Reportes por revisar</h2>
          <p className="card-description" role="status">
            {list.status === 'ready'
              ? `${list.result.total} ${list.result.total === 1 ? 'incidencia pendiente' : 'incidencias pendientes'} · Hora de Lima (UTC−5)`
              : 'Los reportes se muestran en hora de Lima (UTC−5).'}
          </p>
        </div>
        <Badge tone="warning">Pendiente de validación</Badge>
      </div>
      {busy ? <LoadingIncidents /> : null}
      {list.status === 'error' ? <Alert tone="danger"
        title={list.forbidden ? 'Acceso denegado' : 'No se pudo cargar el listado'}
        actions={<Button variant="secondary" onClick={() => { void load(list.page) }}>Reintentar</Button>}>
        {list.message}
      </Alert> : null}
      {list.status === 'ready' ? <>
        {list.result.items.length === 0 ? <EmptyState icon={ClipboardList} headingLevel={3}
          title={list.result.total === 0 ? 'No hay incidencias pendientes de validación' : 'No hay incidencias en esta página'}>
          <p>Puedes actualizar el listado para consultar nuevos reportes.</p>
        </EmptyState> : <DataTable columns={columns} rows={list.result.items} rowKey={item => item.incidencia_id}
          caption="Incidencias pendientes, ordenadas por hora de ocurrencia descendente" label="Incidencias pendientes" />}
      </> : null}
      <nav className="pagination" aria-label="Páginas de incidencias" hidden={list.status !== 'ready'}>
        <Button variant="secondary" size="sm" icon={ChevronLeft} disabled={busy || list.page <= 1}
          onClick={() => { void load(list.page - 1) }}>Anterior</Button>
        <span aria-live="polite">Página {list.page} de {totalPages}</span>
        <Button variant="secondary" size="sm" icon={ChevronRight} disabled={busy || list.page >= totalPages}
          onClick={() => { void load(list.page + 1) }}>Siguiente</Button>
      </nav>
    </section>
  </section>
}
