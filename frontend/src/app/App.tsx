import { useCallback, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { ShieldAlert } from 'lucide-react'
import { HomePage } from '../pages/HomePage'
import { DriverItineraryPage } from '../pages/DriverItineraryPage'
import { IncidentCreatePage } from '../pages/IncidentCreatePage'
import { useIncidentSynchronization } from '../hooks/useIncidentSynchronization'
import { listIncidents } from '../services/incidentStorage'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { OrderCreatePage } from '../pages/OrderCreatePage'
import { VehiclesPage } from '../pages/VehiclesPage'
import { DriversPage } from '../pages/DriversPage'
import { DeliveryPreferencesPage } from '../pages/DeliveryPreferencesPage'
import { UsersPage } from '../pages/UsersPage'
import { OperationIncidentsPage } from '../pages/OperationIncidentsPage'
import { ChangePasswordPage } from '../pages/ChangePasswordPage'
import { DriverShell, PublicShell, StaffShell } from '../components/layout/AppShell'
import { Alert, EmptyState, LinkButton, ToastProvider, useToast } from '../components/ui'
import { canListVehicles, canManageOperations, canManageUsers, ROLE_LABEL } from '../domain/roles'
import { logout, type LoginResponse } from '../services/auth'
import { clearItinerary } from '../services/offlineStorage'
import { listPendingReports } from '../services/reportQueue'
import { forgetDriver, recallDriver, rememberDriver } from '../services/offlineAccess'
import { installPasswordChangeGuard } from '../services/passwordChangeGuard'

const CHANGE_PASSWORD_PATH = '/cambiar-contrasena'

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
  const { notify } = useToast()
  const createOrdersAllowed = identity !== null && canManageOperations(identity.rol)
  const vehiclesAllowed = identity !== null && canListVehicles(identity.rol)
  const mustChangePassword = identity?.debe_cambiar_contrasena === true
  const signedIn = identity !== null
  // WCAG 2.4.2: the tab identifies the screen, including denied and public routes.
  useEffect(() => {
    const heading = document.querySelector('main h1')?.textContent?.trim()
    document.title = heading ? `${heading} — EcoLogística Lima` : 'EcoLogística Lima'
  }, [location.pathname, identity?.rol, mustChangePassword])
  useIncidentSynchronization(identity?.rol === 'CONDUCTOR' && !mustChangePassword ? identity.usuario_id : undefined)

  function handleLoginSuccess(loggedInIdentity: LoginResponse, email: string) {
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
        ...(identity.expires_at ? { expires_at: identity.expires_at } : {}) }
      rememberDriver(updated)
      setIdentity(updated)
    }
    void navigate('/', { replace: true })
    notify('Contraseña actualizada.')
  }

  const handleSessionExpired = useCallback(() => {
    forgetDriver()
    setIdentity(null)
    setLogoutMessage('Tu sesión ha vencido. Vuelve a iniciar sesión.')
    void navigate('/login', { replace: true })
  }, [navigate])

  useEffect(() => {
    if (!identity?.expires_at) return
    const remaining = Date.parse(identity.expires_at) - Date.now()
    const timer = setTimeout(handleSessionExpired, Math.max(0, remaining))
    return () => clearTimeout(timer)
  }, [identity, handleSessionExpired])

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
      <Routes>
        <Route path="/login" element={<LoginPage onLoginSuccess={handleLoginSuccess} notice={logoutMessage} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </PublicShell>
  }

  const banner = logoutMessage
    ? <div className="shell-banner"><Alert tone="danger">{logoutMessage}</Alert></div>
    : null
  if (mustChangePassword) {
    return <PublicShell>
      {banner}
      <Routes>
        <Route path={CHANGE_PASSWORD_PATH} element={<ChangePasswordPage required onChanged={handlePasswordChanged}
          onSessionExpired={handleSessionExpired} onLogout={() => { void handleLogout() }} />} />
        <Route path="*" element={<Navigate to={CHANGE_PASSWORD_PATH} replace />} />
      </Routes>
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
    ? <DriverShell {...shellProps}>{routes}</DriverShell>
    : <StaffShell {...shellProps}>{routes}</StaffShell>
}
