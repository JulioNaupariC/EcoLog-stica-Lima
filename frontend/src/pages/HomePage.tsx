import { useEffect, useState } from 'react'
import {
  BarChart3, Building2, CheckCircle2, ClipboardList, Leaf, Map, Package, Route as RouteIcon, Truck, UploadCloud, UserRound,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Badge, Card, LinkButton, PageHeader, StatCard } from '../components/ui'
import { canListVehicles, canManageOperations, canViewOperationIndicators, ROLE_LABEL } from '../domain/roles'
import type { AuthRole } from '../services/auth'
import { getOperationIndicators } from '../services/indicators'
import { loadItinerary } from '../services/offlineStorage'
import { listPendingReports } from '../services/reportQueue'

type Figure<T> = { status: 'loading' } | { status: 'ready', value: T } | { status: 'error' }

/** Loads one real figure; failures are shown as unavailable, never estimated. */
function useFigure<T>(enabled: boolean, load: () => Promise<T>): Figure<T> {
  const [figure, setFigure] = useState<Figure<T>>({ status: 'loading' })
  useEffect(() => {
    if (!enabled) return undefined
    let active = true
    load().then(value => { if (active) setFigure({ status: 'ready', value }) })
      .catch(() => { if (active) setFigure({ status: 'error' }) })
    return () => { active = false }
    // `load` is a module-level function per call site; only `enabled` matters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled])
  return figure
}

const NUMBER = new Intl.NumberFormat('es-PE')
const TIME = new Intl.DateTimeFormat('es-PE', { timeStyle: 'short', timeZone: 'America/Lima' })

function plural(count: number, one: string, many: string) {
  return `${NUMBER.format(count)} ${count === 1 ? one : many}`
}

const UNAVAILABLE = 'No disponible en este momento'

function QuickLink({ to, icon: Icon, title, description }: { to: string, icon: LucideIcon, title: string, description: string }) {
  return <li>
    <Link to={to} className="quick-link">
      <span className="quick-link-icon"><Icon aria-hidden="true" size={20} /></span>
      <span className="quick-link-text"><strong>{title}</strong><span>{description}</span></span>
    </Link>
  </li>
}

function ComingSoon() {
  return <Card title="Próximamente" titleId="home-next-title" className="coming-soon" tone="muted"
    description="Funciones planificadas que todavía no muestran datos.">
    <ul className="coming-soon-list">
      <li><RouteIcon aria-hidden="true" size={18} /> Rutas optimizadas (VRPTW) <Badge tone="neutral" icon={null}>Próximamente</Badge></li>
      <li><BarChart3 aria-hidden="true" size={18} /> Indicadores de CO₂ por ruta <Badge tone="neutral" icon={null}>Próximamente</Badge></li>
    </ul>
  </Card>
}

function StaffHome({ role }: { role: AuthRole }) {
  const manage = canManageOperations(role)
  const vehiclesVisible = canListVehicles(role)
  const summaryVisible = canViewOperationIndicators(role)
  // One aggregated request (ECL-25): no lists are downloaded just to count them.
  const indicators = useFigure(summaryVisible, getOperationIndicators)
  const ready = indicators.status === 'ready' ? indicators.value : null
  const loading = indicators.status === 'loading'
  const unavailable = indicators.status === 'error' ? UNAVAILABLE : undefined
  return <>
    {summaryVisible ? <section aria-labelledby="home-summary-title" className="home-section">
      <h2 id="home-summary-title" className="section-title">Resumen de la operación</h2>
      <div className="stat-grid">
        <StatCard icon={Truck} label="Vehículos registrados" loading={loading}
          value={ready ? NUMBER.format(ready.vehiculos.total) : '—'}
          detail={ready ? plural(ready.vehiculos.activos, 'activo', 'activos') : unavailable} />
        <StatCard icon={UserRound} label="Conductores registrados" loading={loading}
          value={ready ? NUMBER.format(ready.conductores.total) : '—'}
          detail={ready
            ? plural(ready.conductores.habilitadosAsignacion, 'habilitado para asignación', 'habilitados para asignación')
            : unavailable} />
        <StatCard icon={Package} label="Pedidos registrados" loading={loading}
          value={ready ? NUMBER.format(ready.pedidos.total) : '—'}
          detail={ready ? plural(ready.pedidos.porEstado.PENDIENTE ?? 0, 'pendiente', 'pendientes') : unavailable} />
      </div>
      {ready ? <p className="home-note">Cifras agregadas a las {TIME.format(new Date(ready.generadoEn))}.</p> : null}
    </section> : <p className="page-description">Tu rol no tiene acceso a los indicadores de la operación.</p>}
    {manage || vehiclesVisible ? <section aria-labelledby="home-shortcuts-title" className="home-section">
      <h2 id="home-shortcuts-title" className="section-title">Accesos rápidos</h2>
      <ul className="quick-links">
        {manage ? <QuickLink to="/pedidos/nuevo" icon={ClipboardList} title="Registrar pedido" description="Con propuesta de preferencias del cliente" /> : null}
        {manage ? <QuickLink to="/clientes/preferencias" icon={Building2} title="Preferencias de entrega" description="Horarios, referencias y accesos" /> : null}
        {vehiclesVisible ? <QuickLink to="/vehiculos" icon={Truck} title="Vehículos" description={manage ? 'Flota y registro de unidades' : 'Consulta de la flota'} /> : null}
        {manage ? <QuickLink to="/conductores" icon={UserRound} title="Conductores" description="Perfiles y disponibilidad" /> : null}
      </ul>
    </section> : null}
    <ComingSoon />
  </>
}

function DriverHome({ ownerId }: { ownerId: string }) {
  // Local data only: the itinerary page owns the API request and saves its snapshot.
  const saved = useFigure(true, () => loadItinerary(ownerId))
  const pending = useFigure(true, () => listPendingReports(ownerId))
  const stops = saved.status === 'ready' && saved.value ? saved.value.stops : null
  const open = stops ? stops.filter(stop => stop.status === 'PENDIENTE' || stop.status === 'EN_RUTA').length : 0
  return <>
    <section aria-labelledby="home-summary-title" className="home-section">
      <h2 id="home-summary-title" className="section-title">Tu jornada</h2>
      <div className="stat-grid">
        <StatCard icon={Map} label="Paradas en tu itinerario" loading={saved.status === 'loading'}
          value={stops ? stops.length : '—'}
          detail={stops ? plural(open, 'por atender', 'por atender') + ' · último itinerario guardado'
            : saved.status === 'loading' ? undefined : 'Abre tu itinerario para cargarlo'} />
        <StatCard icon={UploadCloud} label="Reportes por sincronizar" loading={pending.status === 'loading'}
          value={pending.status === 'ready' ? pending.value.length : '—'}
          detail={pending.status === 'ready'
            ? pending.value.length ? 'Guardados en este dispositivo' : 'Todo sincronizado'
            : pending.status === 'error' ? UNAVAILABLE : undefined} />
      </div>
    </section>
    <LinkButton to="/conductor/itinerario" icon={Map} block>Abrir mi itinerario</LinkButton>
    <p className="home-note"><CheckCircle2 aria-hidden="true" size={16} /> Los reportes se guardan en el dispositivo y se envían al recuperar la conexión.</p>
  </>
}

export function HomePage({ role, ownerId }: { role: AuthRole, ownerId: string }) {
  return <>
    <PageHeader titleId="home-title" title="Inicio" eyebrow={<><Leaf aria-hidden="true" size={14} /> {ROLE_LABEL[role]}</>}
      description={role === 'CONDUCTOR'
        ? 'Tus paradas del día y los reportes pendientes de sincronizar.'
        : 'Resumen con datos actuales del sistema y accesos a las tareas frecuentes.'} />
    {role === 'CONDUCTOR' ? <DriverHome ownerId={ownerId} /> : <StaffHome role={role} />}
  </>
}
