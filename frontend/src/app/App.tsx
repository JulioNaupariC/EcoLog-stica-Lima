import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { ShieldAlert } from 'lucide-react'
import { useIncidentSynchronization } from '../hooks/useIncidentSynchronization'
import { listIncidents } from '../services/incidentStorage'
import { LoginPage } from '../pages/LoginPage'
import { DriverShell, PublicShell, StaffShell } from '../components/layout/AppShell'
import { Alert, Button, EmptyState, LinkButton, ToastProvider, useToast } from '../components/ui'
import { SessionExpiryNotice } from '../components/SessionExpiryNotice'
import { captureSessionDraft, downloadSessionDraft } from '../services/sessionDraft'
import type { SessionDraft } from '../services/sessionDraft'
import type { SessionExtension } from '../services/auth'
import { canListVehicles, canManageOperations, canManageUsers, ROLE_LABEL } from '../domain/roles'
import { logout, type LoginResponse } from '../services/auth'
import { clearItinerary } from '../services/offlineStorage'
import { listPendingReports } from '../services/reportQueue'
import { forgetDriver, recallDriver, rememberDriver } from '../services/offlineAccess'
import { installPasswordChangeGuard } from '../services/passwordChangeGuard'

const CHANGE_PASSWORD_PATH = '/cambiar-contrasena'

const HomePage = lazy(() => import('../pages/HomePage').then(module => ({ default: module.HomePage })))
const DriverItineraryPage = lazy(() => import('../pages/DriverItineraryPage').then(module => ({ default: module.DriverItineraryPage })))
const IncidentCreatePage = lazy(() => import('../pages/IncidentCreatePage').then(module => ({ default: module.IncidentCreatePage })))
const NotFoundPage = lazy(() => import('../pages/NotFoundPage').then(module => ({ default: module.NotFoundPage })))
const OrderCreatePage = lazy(() => import('../pages/OrderCreatePage').then(module => ({ default: module.OrderCreatePage })))
const VehiclesPage = lazy(() => import('../pages/VehiclesPage').then(module => ({ default: module.VehiclesPage })))
const DriversPage = lazy(() => import('../pages/DriversPage').then(module => ({ default: module.DriversPage })))
const DeliveryPreferencesPage = lazy(() => import('../pages/DeliveryPreferencesPage').then(module => ({ default: module.DeliveryPreferencesPage })))
const UsersPage = lazy(() => import('../pages/UsersPage').then(module => ({ default: module.UsersPage })))
const OperationIncidentsPage = lazy(() => import('../pages/OperationIncidentsPage').then(module => ({ default: module.OperationIncidentsPage })))
const OperationRoutesPage = lazy(() => import('../pages/OperationRoutesPage').then(module => ({ default: module.OperationRoutesPage })))
const ChangePasswordPage = lazy(() => import('../pages/ChangePasswordPage').then(module => ({ default: module.ChangePasswordPage })))

// Commit the title effect with the resolved page, rather than the loading fallback.
function PageTitle() {
  const location = useLocation()
  useEffect(() => {
    const heading = document.querySelector('main h1')?.textContent?.trim()
    document.title = heading ? `${heading} — EcoLogística Lima` : 'EcoLogística Lima'
  }, [location.pathname])
  return null
}

function PageContent({ children }: { children: ReactNode }) {
  return <Suspense fallback={<p className="field-hint" role="status" aria-live="polite">Cargando página…</p>}>
    <PageTitle />{children}
  </Suspense>
}

function AccessDenied() {
  return <EmptyState icon={ShieldAlert} title="Acceso denegado" headingLevel={1} titleId="access-denied-title"
    action={<LinkButton to="/" variant="secondary">Volver al inicio</LinkButton>}>
    <p role="alert">No tienes permisos para acceder a esta función.</p>
  </EmptyState>
}

export function App() {
  return <ToastProvider><AppRoutes /></ToastProvider>
}

function AppRoutes() {
  const [identity, setIdentity] = useState<LoginResponse | null>(recallDriver)
  // Shown in the top bar only; kept in memory, never stored on the device.
  const [accountEmail, setAccountEmail] = useState('')
  const [logoutMessage, setLogoutMessage] = useState('')
  const [loggingOut, setLoggingOut] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const [expiredDraft, setExpiredDraft] = useState<SessionDraft | null>(null)
  const { notify } = useToast()
  const createOrdersAllowed = identity !== null && canManageOperations(identity.rol)
  const vehiclesAllowed = identity !== null && canListVehicles(identity.rol)
  const mustChangePassword = identity?.debe_cambiar_contrasena === true
  const signedIn = identity !== null
  useIncidentSynchronization(identity?.rol === 'CONDUCTOR' && !mustChangePassword ? identity.usuario_id : undefined)

  function handleLoginSuccess(loggedInIdentity: LoginResponse, email: string) {
    setExpiredDraft(current => current?.owner === loggedInIdentity.usuario_id ? current : null)
    // A temporary-password session is not remembered as a usable driver tab.
    if (!loggedInIdentity.debe_cambiar_contrasena) rememberDriver(loggedInIdentity)
    setIdentity(loggedInIdentity)
    setAccountEmail(email)
    setLogoutMessage('')
    void navigate(loggedInIdentity.debe_cambiar_contrasena ? CHANGE_PASSWORD_PATH : '/', { replace: true })
  }

  // ECL-77: any API 403 "Cambio de contraseña requerido" locks the app on the change page.
  useEffect(() => {
    if (!signedIn) return undefined
    return installPasswordChangeGuard(() => {
      forgetDriver()
      setIdentity(current => current ? { ...current, debe_cambiar_contrasena: true } : current)
      void navigate(CHANGE_PASSWORD_PATH, { replace: true })
    })
  }, [signedIn, navigate])

  function handlePasswordChanged() {
    if (identity) {
      const updated: LoginResponse = { usuario_id: identity.usuario_id, rol: identity.rol,
        ...(identity.max_expires_at ? { max_expires_at: identity.max_expires_at } : {}),
        ...(identity.expires_at ? { expires_at: identity.expires_at } : {}) }
      rememberDriver(updated)
      setIdentity(updated)
    }
    void navigate('/', { replace: true })
    notify('Contraseña actualizada.')
  }

  const handleSessionExpired = useCallback(() => {
    if (identity) {
      const draft = captureSessionDraft(identity.usuario_id, location.pathname)
      if (draft) setExpiredDraft(draft)
    }
    forgetDriver()
    setIdentity(null)
    setLogoutMessage('Tu sesión ha vencido. Vuelve a iniciar sesión.')
    void navigate('/login', { replace: true })
  }, [identity, location.pathname, navigate])

  function handleSessionExtended(extension: SessionExtension) {
    if (!identity) return
    const updated = { ...identity, ...extension }
    if (!updated.debe_cambiar_contrasena) rememberDriver(updated)
    else forgetDriver()
    setIdentity(updated)
    notify('Sesión renovada. Puedes continuar con tu trabajo.')
  }

  function saveAndExit() {
    if (identity) {
      const draft = captureSessionDraft(identity.usuario_id, location.pathname)
      if (draft) downloadSessionDraft(draft)
    }
    void handleLogout()
  }

  async function handleLogout() {
    if (!identity || loggingOut) return
    setLogoutMessage('')
    setLoggingOut(true)
    try {
      if (identity.rol === 'CONDUCTOR') {
        let pendingCount: number | null
        try {
          pendingCount = (await listPendingReports(identity.usuario_id)).length +
            (await listIncidents(identity.usuario_id)).filter(item => !item.acknowledgement).length
        } catch {
          pendingCount = null
        }
        if (pendingCount === null) {
          if (!window.confirm(
            'No se pudo verificar la cola offline. Los reportes locales no se eliminarán. ¿Cerrar sesión?',
          )) return
        } else if (pendingCount > 0 && !window.confirm(
          `Tienes ${pendingCount === 1 ? '1 reporte pendiente' : `${pendingCount} reportes pendientes`}. Se conservarán en este dispositivo y podrás sincronizarlos al volver a iniciar sesión. ¿Cerrar sesión?`,
        )) {
          return
        }
      }
      await logout()
      setExpiredDraft(null)
      forgetDriver()
      setIdentity(null)
      setAccountEmail('')
      await navigate('/login', { replace: true })
      notify('Sesión cerrada.')
      if (identity.rol === 'CONDUCTOR') {
        try {
          await clearItinerary(identity.usuario_id)
        } catch {
          setLogoutMessage('La sesión se cerró, pero no se pudo borrar el itinerario guardado en este dispositivo.')
        }
      }
    } catch (error) {
      setLogoutMessage(
        error instanceof Error ? error.message : 'No se pudo cerrar la sesión.',
      )
    } finally {
      setLoggingOut(false)
    }
  }

  if (identity === null) {
    return <PublicShell>
      <PageContent><Routes>
        <Route path="/login" element={<LoginPage onLoginSuccess={handleLoginSuccess} notice={logoutMessage} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes></PageContent>
    </PublicShell>
  }

  const draft = expiredDraft?.owner === identity.usuario_id ? expiredDraft : null
  const banner = <>
    {logoutMessage ? <div className="shell-banner"><Alert tone="danger">{logoutMessage}</Alert></div> : null}
    {draft ? <Alert tone="info" role="status" actions={<Button onClick={() => downloadSessionDraft(draft)}>Descargar borrador</Button>}>
      Conservamos un borrador del formulario anterior. Descárgalo antes de cerrar o recargar esta pestaña. Las contraseñas no se guardan.
    </Alert> : null}
  </>
  const sessionNotice = <SessionExpiryNotice key={identity.usuario_id} identity={identity}
    onExtended={handleSessionExtended} onExpired={handleSessionExpired}
    onLogout={() => { void handleLogout() }} onSaveAndExit={saveAndExit} />
  if (mustChangePassword) {
    return <PublicShell>
      {sessionNotice}
      {banner}
      <PageContent><Routes>
        <Route path={CHANGE_PASSWORD_PATH} element={<ChangePasswordPage required onChanged={handlePasswordChanged}
          onSessionExpired={handleSessionExpired} onLogout={() => { void handleLogout() }} />} />
        <Route path="*" element={<Navigate to={CHANGE_PASSWORD_PATH} replace />} />
      </Routes></PageContent>
    </PublicShell>
  }
  const guarded = (allowed: boolean, element: ReactNode) => allowed ? element : <AccessDenied />
  const shellProps = {
    role: identity.rol,
    accountName: accountEmail || ROLE_LABEL[identity.rol],
    loggingOut,
    onLogout: () => { void handleLogout() },
    banner,
  }
  const routes = <Routes>
    <Route path="/" element={<HomePage role={identity.rol} ownerId={identity.usuario_id} />} />
    <Route path="/login" element={<Navigate to="/" replace />} />
    <Route path="/pedidos/nuevo" element={guarded(createOrdersAllowed, <OrderCreatePage />)} />
    <Route path="/operacion/incidencias" element={guarded(createOrdersAllowed,
      <OperationIncidentsPage key={identity.usuario_id} onSessionExpired={handleSessionExpired} />)} />
    <Route path="/operacion/rutas" element={guarded(createOrdersAllowed,
      <OperationRoutesPage key={identity.usuario_id} onSessionExpired={handleSessionExpired} />)} />
    <Route path="/vehiculos" element={guarded(vehiclesAllowed, <VehiclesPage canCreate={createOrdersAllowed} />)} />
    <Route path="/conductor/itinerario" element={guarded(identity.rol === 'CONDUCTOR',
      <DriverItineraryPage key={identity.usuario_id} ownerId={identity.usuario_id} onSessionExpired={handleSessionExpired} />)} />
    <Route path="/conductor/incidencias/nueva" element={guarded(identity.rol === 'CONDUCTOR',
      <IncidentCreatePage key={identity.usuario_id} ownerId={identity.usuario_id} />)} />
    <Route path="/conductores" element={guarded(createOrdersAllowed,
      <DriversPage key={identity.usuario_id} onSessionExpired={handleSessionExpired} />)} />
    <Route path="/clientes/preferencias" element={guarded(createOrdersAllowed,
      <DeliveryPreferencesPage key={identity.usuario_id} onSessionExpired={handleSessionExpired} />)} />
    <Route path="/usuarios" element={guarded(canManageUsers(identity.rol),
      <UsersPage key={identity.usuario_id} ownId={identity.usuario_id} onSessionExpired={handleSessionExpired} />)} />
    <Route path={CHANGE_PASSWORD_PATH} element={<ChangePasswordPage required={false}
      onChanged={handlePasswordChanged} onSessionExpired={handleSessionExpired} />} />
    <Route path="*" element={<NotFoundPage />} />
  </Routes>
  return identity.rol === 'CONDUCTOR'
    ? <DriverShell {...shellProps}>{sessionNotice}<PageContent>{routes}</PageContent></DriverShell>
    : <StaffShell {...shellProps}>{sessionNotice}<PageContent>{routes}</PageContent></StaffShell>
}
