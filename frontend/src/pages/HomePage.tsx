import { useEffect, useState } from 'react'
import {
  BarChart3, Building2, CheckCircle2, ClipboardList, Leaf, Map, Route as RouteIcon, Truck, UploadCloud, UserRound,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Badge, Card, LinkButton, PageHeader, StatCard } from '../components/ui'
import { canListVehicles, canManageOperations, ROLE_LABEL } from '../domain/roles'
import type { AuthRole } from '../services/auth'
import { listVehicles } from '../services/vehicles'
import { listDrivers } from '../services/drivers'
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

function plural(count: number, one: string, many: string) {
  return `${count} ${count === 1 ? one : many}`
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
  const vehicles = useFigure(vehiclesVisible, listVehicles)
  const drivers = useFigure(manage, () => listDrivers(1, 100))
  return <>
    {vehiclesVisible || manage ? <section aria-labelledby="home-summary-title" className="home-section">
      <h2 id="home-summary-title" className="section-title">Resumen de recursos</h2>
      <div className="stat-grid">
        {vehiclesVisible ? <StatCard icon={Truck} label="Vehículos registrados" loading={vehicles.status === 'loading'}
          value={vehicles.status === 'ready' ? vehicles.value.length : '—'}
          detail={vehicles.status === 'ready'
            ? plural(vehicles.value.filter(item => item.estado === 'ACTIVO').length, 'activo', 'activos')
            : vehicles.status === 'error' ? UNAVAILABLE : undefined} /> : null}
        {manage ? <StatCard icon={UserRound} label="Conductores registrados" loading={drivers.status === 'loading'}
          value={drivers.status === 'ready' ? drivers.value.total : '—'}
          detail={drivers.status === 'ready'
            ? plural(drivers.value.items.filter(item => item.habilitado_asignacion).length,
              'habilitado para asignación', 'habilitados para asignación')
              + (drivers.value.total > drivers.value.items.length ? ' (primeros 100)' : '')
            : drivers.status === 'error' ? UNAVAILABLE : undefined} /> : null}
      </div>
    </section> : <p className="page-description">Tu rol no tiene acceso a los listados operativos de esta versión.</p>}
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
