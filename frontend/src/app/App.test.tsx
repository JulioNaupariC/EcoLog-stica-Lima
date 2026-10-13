import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import { login, logout } from '../services/auth'
import type { AuthRole } from '../services/auth'
import { createVehicle, listVehicles } from '../services/vehicles'
import type { VehicleResponse } from '../services/vehicles'
import { listPendingReports } from '../services/reportQueue'
import { clearItinerary } from '../services/offlineStorage'
import { App } from './App'
import { ROLE_LABEL } from '../domain/roles'

vi.mock('../services/auth', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/auth')>()
  return { ...actual, login: vi.fn(), logout: vi.fn() }
})

const loginMock = vi.mocked(login)
const logoutMock = vi.mocked(logout)
const usuario_id = '123e4567-e89b-12d3-a456-426614174000'

vi.mock('../services/reportQueue', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/reportQueue')>()
  return { ...actual, listPendingReports: vi.fn() }
})

const pendingReportsMock = vi.mocked(listPendingReports)

vi.mock('../services/offlineStorage', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/offlineStorage')>()
  return { ...actual, clearItinerary: vi.fn() }
})

const clearItineraryMock = vi.mocked(clearItinerary)

vi.mock('../services/vehicles', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/vehicles')>()
  return { ...actual, listVehicles: vi.fn(), createVehicle: vi.fn() }
})

const listVehiclesMock = vi.mocked(listVehicles)
const createVehicleMock = vi.mocked(createVehicle)
const vehicle: VehicleResponse = {
  vehiculo_id: '223e4567-e89b-12d3-a456-426614174000',
  placa: 'ABC-123', tipo: 'CAMIONETA', capacidad_kg: '1000.00', capacidad_m3: '8.00',
  rendimiento_km_l: '10.000', factor_co2_kg_km: '0.30000', anio_fabricacion: 2024, estado: 'ACTIVO',
}

function RouteControls() {
  const navigate = useNavigate()
  const location = useLocation()
  return (
    <aside aria-label="Controles de prueba">
      <span data-testid="path">{location.pathname}</span>
      <button type="button" onClick={() => { void navigate('/pedidos/nuevo') }}>Abrir ruta de pedido</button>
      <button type="button" onClick={() => { void navigate('/login') }}>Abrir ruta de login</button>
      <button type="button" onClick={() => { void navigate('/vehiculos') }}>Abrir ruta de vehículos</button>
      <button type="button" onClick={() => { void navigate('/conductor/itinerario') }}>Abrir ruta de itinerario</button>
      <button type="button" onClick={() => { void navigate(-1) }}>Atrás</button>
    </aside>
  )
}

function renderAt(path: string, initialEntries?: string[]) {
  return render(
    <MemoryRouter initialEntries={initialEntries ?? [path]} initialIndex={initialEntries ? initialEntries.length - 1 : 0}>
      <RouteControls />
      <App />
    </MemoryRouter>,
  )
}


/** The account menu (top bar) shows the readable role and holds «Cerrar sesión». */
function accountButton(roleLabel: string) {
  return screen.getByRole('button', { name: new RegExp(`^Cuenta: .*, ${roleLabel}$`, 'u') })
}

async function signIn(role: AuthRole) {
  const user = userEvent.setup()
  loginMock.mockResolvedValue({ usuario_id, rol: role })
  await user.click(screen.getByLabelText('Correo electrónico'))
  await user.paste('user@example.test')
  await user.click(screen.getByLabelText('Contraseña'))
  await user.paste('private-password')
  await user.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
  expect(await screen.findByRole('heading', { name: 'Inicio' })).toBeInTheDocument()
  return user
}

describe('App', () => {
  beforeEach(() => {
    loginMock.mockReset()
    logoutMock.mockReset().mockResolvedValue()
    pendingReportsMock.mockReset().mockResolvedValue([])
    clearItineraryMock.mockReset().mockResolvedValue()
    listVehiclesMock.mockReset().mockResolvedValue([vehicle])
    createVehicleMock.mockReset().mockResolvedValue(vehicle)
  })

  it('sin identidad redirige / al login, sin navegación ni enlaces de gestión', () => {
    renderAt('/')
    expect(screen.getByTestId('path')).toHaveTextContent('/login')
    expect(screen.getByRole('main')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Navegación principal' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Registrar pedido' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Vehículos' })).not.toBeInTheDocument()
  })

  it('sin identidad redirige una ruta desconocida al login', () => {
    renderAt('/ruta-inexistente')
    expect(screen.getByTestId('path')).toHaveTextContent('/login')
    expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
  })

  it('con sesión muestra la página 404 y permite volver al inicio', async () => {
    renderAt('/login', ['/ruta-inexistente', '/login'])
    const user = await signIn('OPERADOR')
    await user.click(screen.getByRole('button', { name: 'Atrás' }))
    expect(screen.getByRole('heading', { name: 'Página no encontrada' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Volver al inicio' })).toHaveAttribute('href', '/')
    await user.click(screen.getByRole('link', { name: 'Volver al inicio' }))
    expect(screen.getByRole('heading', { name: 'Inicio' })).toBeInTheDocument()
  })

  it('con sesión muestra la navegación principal y el rol legible', async () => {
    renderAt('/login')
    await signIn('ADMINISTRADOR')
    expect(screen.getByRole('navigation', { name: 'Navegación principal' })).toBeInTheDocument()
    expect(accountButton('Administrador')).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText('ADMINISTRADOR')).not.toBeInTheDocument()
  })

  it('redirige /pedidos/nuevo a /login sin identidad', () => {
    renderAt('/pedidos/nuevo')
    expect(screen.getByTestId('path')).toHaveTextContent('/login')
    expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Registrar pedido' })).not.toBeInTheDocument()
  })

  it('solicita iniciar sesión al abrir el itinerario sin identidad', () => {
    renderAt('/conductor/itinerario')
    expect(screen.getByTestId('path')).toHaveTextContent('/login')
    expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Mi itinerario' })).not.toBeInTheDocument()
  })

  it('permite al conductor abrir su itinerario desde la navegación y por ruta directa', async () => {
    renderAt('/login')
    const user = await signIn('CONDUCTOR')
    expect(screen.getByRole('link', { name: 'Mi itinerario' })).toHaveAttribute('href', '/conductor/itinerario')
    await user.click(screen.getByRole('link', { name: 'Mi itinerario' }))
    expect(screen.getByRole('heading', { name: 'Mi itinerario' })).toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'EcoLogística Lima' }))
    await user.click(screen.getByRole('button', { name: 'Abrir ruta de itinerario' }))
    // No API in this test: the real itinerary fails to load and the page offers a retry.
    // Without VITE_DEMO_ITINERARY=true it never falls back to fictitious stops.
    expect(await screen.findByRole('heading', { name: 'No se pudo cargar tu itinerario' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument()
    expect(screen.queryByRole('note')).not.toBeInTheDocument()
  })

  it.each<AuthRole>(['ADMINISTRADOR', 'OPERADOR', 'ANALISTA', 'AUDITOR'])(
    'oculta itinerario y deniega su ruta directa a %s',
    async (role) => {
      renderAt('/login')
      const user = await signIn(role)
      expect(screen.queryByRole('link', { name: 'Mi itinerario' })).not.toBeInTheDocument()
      await user.click(screen.getByRole('button', { name: 'Abrir ruta de itinerario' }))
      expect(screen.getByRole('heading', { name: 'Acceso denegado' })).toBeInTheDocument()
      expect(screen.queryByRole('note')).not.toBeInTheDocument()
    },
  )

  it('al entrar correctamente vuelve a / y reemplaza la entrada de /login', async () => {
    const user = userEvent.setup()
    loginMock.mockResolvedValue({ usuario_id, rol: 'OPERADOR' })
    renderAt('/login', ['/ruta-inexistente', '/login'])
    await user.click(screen.getByLabelText('Correo electrónico'))
    await user.paste('user@example.test')
    await user.click(screen.getByLabelText('Contraseña'))
    await user.paste('private-password')
    await user.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
    expect(await screen.findByRole('heading', { name: 'Inicio' })).toBeInTheDocument()
    expect(screen.getByTestId('path')).toHaveTextContent('/')
    expect(accountButton('Operador')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Atrás' }))
    expect(screen.getByTestId('path')).toHaveTextContent('/ruta-inexistente')
    expect(screen.getByRole('heading', { name: 'Página no encontrada' })).toBeInTheDocument()
  })

  it.each<AuthRole>(['ADMINISTRADOR', 'OPERADOR'])(
    'permite a %s ver y abrir el formulario de pedidos',
    async (role) => {
      renderAt('/login')
      const user = await signIn(role)
      expect(accountButton(ROLE_LABEL[role])).toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Registrar pedido' })).toHaveAttribute('href', '/pedidos/nuevo')
      await user.click(screen.getByRole('link', { name: 'Registrar pedido' }))
      expect(screen.getByRole('heading', { name: 'Registrar pedido' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Registrar pedido' })).toBeInTheDocument()
    },
  )

  it.each<AuthRole>(['CONDUCTOR', 'ANALISTA', 'AUDITOR'])(
    'oculta pedidos y deniega el acceso directo a %s',
    async (role) => {
      renderAt('/login')
      const user = await signIn(role)
      expect(accountButton(ROLE_LABEL[role])).toBeInTheDocument()
      expect(screen.queryByRole('link', { name: 'Registrar pedido' })).not.toBeInTheDocument()
      await user.click(screen.getByRole('button', { name: 'Abrir ruta de pedido' }))
      expect(screen.getByRole('heading', { name: 'Acceso denegado' })).toBeInTheDocument()
      expect(screen.getByRole('alert')).toHaveTextContent('No tienes permisos para acceder a esta función.')
      expect(screen.queryByRole('button', { name: 'Registrar pedido' })).not.toBeInTheDocument()
    },
  )

  it('redirige /login a / cuando ya existe identidad en memoria', async () => {
    renderAt('/login')
    const user = await signIn('OPERADOR')
    await user.click(screen.getByRole('button', { name: 'Abrir ruta de login' }))
    expect(screen.getByTestId('path')).toHaveTextContent('/')
    expect(screen.queryByRole('heading', { name: 'Iniciar sesión' })).not.toBeInTheDocument()
  })

  it.each(['/pedidos/nuevo', '/vehiculos'])('no recupera identidad al volver a montar App en %s', async (path) => {
    const first = renderAt('/login')
    await signIn('OPERADOR')
    expect(screen.getByRole('link', { name: 'Registrar pedido' })).toBeInTheDocument()
    first.unmount()
    // The home summary of the first mount reads the vehicle list; only the second mount matters.
    listVehiclesMock.mockClear()
    renderAt(path)
    expect(screen.getByTestId('path')).toHaveTextContent('/login')
    expect(screen.queryByRole('link', { name: 'Registrar pedido' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
    expect(listVehiclesMock).not.toHaveBeenCalled()
  })

  it('redirige /vehiculos a login sin identidad y no consulta vehículos', () => {
    renderAt('/vehiculos')
    expect(screen.getByTestId('path')).toHaveTextContent('/login')
    expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
    expect(listVehiclesMock).not.toHaveBeenCalled()
    expect(createVehicleMock).not.toHaveBeenCalled()
  })

  it.each<AuthRole>(['ADMINISTRADOR', 'OPERADOR'])('permite a %s listar y crear conservando /vehiculos', async (role) => {
    renderAt('/login')
    const user = await signIn(role)
    expect(screen.getByRole('link', { name: 'Vehículos' })).toHaveAttribute('href', '/vehiculos')
    // The home summary already read the list once; count only the vehicles page.
    listVehiclesMock.mockClear()
    await user.click(screen.getByRole('link', { name: 'Vehículos' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(listVehiclesMock).toHaveBeenCalledTimes(1)
    for (const [label, value] of Object.entries({
      Placa: ' abc-123 ', Tipo: 'CAMIONETA', 'Capacidad (kg)': '1000.00', 'Capacidad (m³)': '8.00',
      'Rendimiento (km/L)': '10.000', 'Factor CO₂ (kg/km)': '0.30000', 'Año de fabricación': '2024',
    })) {
      fireEvent.change(screen.getByLabelText(label), { target: { value } })
    }
    await user.click(screen.getByRole('button', { name: 'Registrar vehículo' }))
    expect(await screen.findByText('Vehículo registrado: ABC-123.')).toBeInTheDocument()
    expect(createVehicleMock).toHaveBeenCalledTimes(1)
    expect(listVehiclesMock).toHaveBeenCalledTimes(2)
    expect(screen.getByTestId('path').textContent).toBe('/vehiculos')
  })

  it('Auditor ve enlace y listado, sin montar el formulario', async () => {
    renderAt('/login')
    const user = await signIn('AUDITOR')
    await user.click(screen.getByRole('link', { name: 'Vehículos' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(screen.queryByRole('form')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Registrar vehículo' })).not.toBeInTheDocument()
    expect(createVehicleMock).not.toHaveBeenCalled()
  })

  it.each<AuthRole>(['CONDUCTOR', 'ANALISTA'])('oculta vehículos y deniega acceso directo a %s sin solicitudes', async (role) => {
    renderAt('/login')
    const user = await signIn(role)
    expect(screen.queryByRole('link', { name: 'Vehículos' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Abrir ruta de vehículos' }))
    expect(screen.getByRole('heading', { name: 'Acceso denegado' })).toBeInTheDocument()
    expect(screen.queryByRole('form')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actualizar listado' })).not.toBeInTheDocument()
    expect(listVehiclesMock).not.toHaveBeenCalled()
    expect(createVehicleMock).not.toHaveBeenCalled()
  })

  it('confirma antes de cerrar sesión con reportes offline pendientes y los conserva', async () => {
    const user = userEvent.setup()
    pendingReportsMock.mockResolvedValue([
      {
        ownerId: usuario_id,
        stopId: '223e4567-e89b-42d3-a456-426614174000',
        operationId: '323e4567-e89b-42d3-a456-426614174000',
        status: 'ENTREGADO',
        createdAt: 1,
        attemptCount: 0,
      },
    ])
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderAt('/login')
    await signIn('CONDUCTOR')

    await user.click(accountButton('Conductor'))
    await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }))

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('1 reporte pendiente'))
    expect(logoutMock).not.toHaveBeenCalled()
    expect(accountButton('Conductor')).toBeInTheDocument()
    confirm.mockRestore()
  })

  it('cierra sesión tras advertir que la cola pendiente se conservará localmente', async () => {
    const user = userEvent.setup()
    pendingReportsMock.mockResolvedValue([
      {
        ownerId: usuario_id,
        stopId: '223e4567-e89b-42d3-a456-426614174000',
        operationId: '323e4567-e89b-42d3-a456-426614174000',
        status: 'ENTREGADO',
        createdAt: 1,
        attemptCount: 0,
      },
    ])
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderAt('/login')
    await signIn('CONDUCTOR')

    await user.click(accountButton('Conductor'))
    await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }))

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('Se conservarán en este dispositivo'))
    expect(logoutMock).toHaveBeenCalledOnce()
    await waitFor(() => expect(screen.getByTestId('path')).toHaveTextContent('/login'))
    expect(screen.queryByRole('button', { name: /^Cuenta: .*, Conductor$/u })).not.toBeInTheDocument()
    expect(clearItineraryMock).toHaveBeenCalledWith(usuario_id)
    confirm.mockRestore()
  })
})
