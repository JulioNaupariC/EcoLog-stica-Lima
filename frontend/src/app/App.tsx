import { useState } from 'react'
import { Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { HomePage } from '../pages/HomePage'
import { DriverItineraryPage } from '../pages/DriverItineraryPage'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { OrderCreatePage } from '../pages/OrderCreatePage'
import { VehiclesPage } from '../pages/VehiclesPage'
import { logout, type AuthRole, type LoginResponse } from '../services/auth'
import { clearItinerary } from '../services/offlineStorage'
import { listPendingReports } from '../services/reportQueue'

function canCreateOrders(role: AuthRole): boolean {
  return role === 'ADMINISTRADOR' || role === 'OPERADOR'
}

function getVehicleAccess(role: AuthRole | undefined) {
  const canCreate = role === 'ADMINISTRADOR' || role === 'OPERADOR'
  return { canList: canCreate || role === 'AUDITOR', canCreate }
}

function AccessDenied() {
  return (
    <section className="access-denied" aria-labelledby="access-denied-title">
      <h1 id="access-denied-title">Acceso denegado</h1>
      <p role="alert">No tienes permisos para acceder a esta función.</p>
    </section>
  )
}

export function App() {
  const [identity, setIdentity] = useState<LoginResponse | null>(null)
  const [logoutMessage, setLogoutMessage] = useState('')
  const [loggingOut, setLoggingOut] = useState(false)
  const navigate = useNavigate()
  const createOrdersAllowed = identity !== null && canCreateOrders(identity.rol)
  const vehicleAccess = getVehicleAccess(identity?.rol)

  function handleLoginSuccess(loggedInIdentity: LoginResponse) {
    setIdentity(loggedInIdentity)
    setLogoutMessage('')
    void navigate('/', { replace: true })
  }

  async function handleLogout() {
    if (!identity || loggingOut) return
    setLogoutMessage('')
    setLoggingOut(true)
    try {
      if (identity.rol === 'CONDUCTOR') {
        let pendingCount: number | null
        try {
          pendingCount = (await listPendingReports(identity.usuario_id)).length
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
      setIdentity(null)
      await navigate('/login', { replace: true })
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

  return (
    <div className="app-shell">
      <header className="site-header">
        <nav className="container" aria-label="Navegación principal">
          <Link className="brand" to="/">
            EcoLogística Lima
          </Link>
          <div className="nav-actions">
            {identity ? <span className="identity-role">Rol: {identity.rol}</span> : (
              <Link className="nav-link" to="/login">Iniciar sesión</Link>
            )}
            {identity ? (
              <button className="nav-link" type="button" disabled={loggingOut} onClick={() => { void handleLogout() }}>
                {loggingOut ? 'Cerrando sesión…' : 'Cerrar sesión'}
              </button>
            ) : null}
            {createOrdersAllowed ? (
              <Link className="nav-link" to="/pedidos/nuevo">Registrar pedido</Link>
            ) : null}
            {vehicleAccess.canList ? (
              <Link className="nav-link" to="/vehiculos">Vehículos</Link>
            ) : null}
            {identity?.rol === 'CONDUCTOR' ? (
              <Link className="nav-link" to="/conductor/itinerario">Mi itinerario</Link>
            ) : null}
          </div>
        </nav>
      </header>
      {logoutMessage ? <p className="container" role="alert">{logoutMessage}</p> : null}
      <main id="contenido-principal" className="container main-content">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route
            path="/login"
            element={identity ? <Navigate to="/" replace /> : <LoginPage onLoginSuccess={handleLoginSuccess} />}
          />
          <Route
            path="/pedidos/nuevo"
            element={identity === null ? <Navigate to="/login" replace /> : (
              createOrdersAllowed ? <OrderCreatePage /> : <AccessDenied />
            )}
          />
          <Route
            path="/vehiculos"
            element={identity === null ? <Navigate to="/login" replace /> : (
              vehicleAccess.canList ? <VehiclesPage canCreate={vehicleAccess.canCreate} /> : <AccessDenied />
            )}
          />
          <Route
            path="/conductor/itinerario"
            element={identity === null ? <Navigate to="/login" replace /> : (
              identity.rol === 'CONDUCTOR' ? (
                <DriverItineraryPage key={identity.usuario_id} ownerId={identity.usuario_id} />
              ) : <AccessDenied />
            )}
          />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
      <footer className="site-footer">
        <div className="container">
          <p>Base técnica del optimizador de rutas sostenibles.</p>
        </div>
      </footer>
    </div>
  )
}
