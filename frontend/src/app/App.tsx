import { useState } from 'react'
import { Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { HomePage } from '../pages/HomePage'
import { DriverItineraryPage } from '../pages/DriverItineraryPage'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { OrderCreatePage } from '../pages/OrderCreatePage'
import { VehiclesPage } from '../pages/VehiclesPage'
import type { AuthRole, LoginResponse } from '../services/auth'

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
  const navigate = useNavigate()
  const createOrdersAllowed = identity !== null && canCreateOrders(identity.rol)
  const vehicleAccess = getVehicleAccess(identity?.rol)

  function handleLoginSuccess(loggedInIdentity: LoginResponse) {
    setIdentity(loggedInIdentity)
    void navigate('/', { replace: true })
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#contenido-principal">Saltar al contenido principal</a>
      <header className="site-header">
        <nav className="container" aria-label="Navegación principal">
          <Link className="brand" to="/">
            EcoLogística Lima
          </Link>
          <div className="nav-actions">
            {identity ? <span className="identity-role">Rol: {identity.rol}</span> : (
              <Link className="nav-link" to="/login">Iniciar sesión</Link>
            )}
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
              identity.rol === 'CONDUCTOR' ? <DriverItineraryPage /> : <AccessDenied />
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
